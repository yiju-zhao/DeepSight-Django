"""
Chat Service - Handle chat functionality business logic following Django patterns.
Includes integrated agentic RAG functionality using RagFlow Knowledge Base Agents.
"""
import json
import logging
from typing import Dict, List, Optional, Generator, Any
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.conf import settings
from rest_framework import status

from ..models import Notebook, ChatSession, SessionChatMessage
from infrastructure.ragflow.client import get_ragflow_client, RagFlowClientError, RagFlowSessionError
from core.services import NotebookBaseService

logger = logging.getLogger(__name__)


class ChatService(NotebookBaseService):
    """
    Handle chat functionality business logic following Django patterns.
    Includes integrated agentic RAG functionality using RagFlow Knowledge Base Agents.
    """
    
    def __init__(self):
        super().__init__()
        self.ragflow_client = get_ragflow_client()
        self._agent_cache_timeout = 300  # 5 minutes
        self._session_cache_timeout = 1800  # 30 minutes
    
    def perform_action(self, **kwargs):
        """
        Implementation of abstract method from BaseService.
        This service uses direct method calls rather than the template pattern.
        """
        # This method is required by BaseService but not used in this service
        # Individual methods handle their own transactions and validation
        pass
    
    def validate_chat_request(self, question: str, file_ids: Optional[List] = None) -> Optional[Dict]:
        """
        Validate chat request parameters.
        
        Args:
            question: The user's question
            file_ids: Optional list of file IDs to use for context
            
        Returns:
            None if valid, error dict if invalid
        """
        if not question:
            return {
                "error": "Question is required.",
                "status_code": status.HTTP_400_BAD_REQUEST
            }
        
        if file_ids is not None and not isinstance(file_ids, list):
            return {
                "error": "file_ids must be a list.",
                "status_code": status.HTTP_400_BAD_REQUEST
            }
        
        
        return None

    def check_notebook_knowledge_base(self, notebook) -> Optional[Dict]:
        """
        Check if notebook has data in its RagFlow dataset.
        
        Args:
            notebook: Notebook instance
            
        Returns:
            None if valid, error dict if no data found
        """
        try:
            # Check if notebook has RagFlow dataset ID
            if not notebook.ragflow_dataset_id:
                return {
                    "error": "This notebook doesn't have a RagFlow dataset. Try creating a new notebook or uploading files to initialize the knowledge base.",
                    "status_code": status.HTTP_400_BAD_REQUEST
                }

            # Check if dataset exists and get info from RagFlow
            dataset_info = self.ragflow_client.get_dataset(notebook.ragflow_dataset_id)
            if not dataset_info:
                return {
                    "error": "Knowledge base dataset not found in RagFlow",
                    "status_code": status.HTTP_400_BAD_REQUEST
                }

            # Check if dataset has documents
            # For now, assume dataset is ready if it exists - can be enhanced later
            return None
            
        except Exception as e:
            logger.exception(f"Error checking notebook knowledge base: {e}")
            return {
                "error": "Failed to check knowledge base status.",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR
            }


    def create_chat_stream(
        self,
        user_id: int,
        question: str,
        history: List[tuple],
        file_ids: Optional[List] = None,
        notebook = None,
        collections: Optional[List] = None,
    ) -> Generator:
        """
        Create agentic RAG chat stream with message recording using RagFlow Knowledge Base Agent.
        
        Args:
            user_id: User ID
            question: User's question
            history: Chat history as list of (sender, message) tuples
            file_ids: Optional file IDs for context (not used with agentic RAG)
            notebook: Notebook instance
            collections: Optional additional collections (not used with agentic RAG)
            
        Returns:
            Generator yielding chat stream chunks
        """
        # Convert history format for agent
        formatted_history = []
        if history:
            for sender, message in history:
                role = "user" if sender == "user" else "assistant"
                formatted_history.append({"role": role, "content": message})
        
        def wrapped_stream():
            """Wrapper to capture assistant tokens and save final response"""
            buffer = []
            
            # Get streaming response from knowledge base agent
            agent_stream = self.ask_agent_streaming(
                notebook=notebook,
                user_id=user_id,
                question=question,
                history=formatted_history
            )
            
            for chunk in agent_stream:
                yield chunk
                
                # Parse token events to build full response
                if chunk.startswith("data: "):
                    try:
                        payload = json.loads(chunk[len("data: "):])
                        if payload.get("type") == "token":
                            buffer.append(payload.get("text", ""))
                    except json.JSONDecodeError:
                        # Skip malformed JSON
                        continue
            
            # Note: Session-based chat handles message recording separately
            full_response = "".join(buffer).strip()

        return wrapped_stream()

    def _get_total_content_length(self, notebook, file_ids: List[str]) -> int:
        """
        Calculate total character length of selected knowledge base items.
        
        Args:
            notebook: Notebook instance
            file_ids: List of knowledge base item IDs
            
        Returns:
            Total character length of content
        """
        from ..models import KnowledgeBaseItem
        
        # Use the custom manager to get items with content
        items = KnowledgeBaseItem.objects.get_items_with_content(file_ids, user_id=notebook.user.pk)
        
        total_length = sum(len(item['content'] or '') for item in items)
        self.logger.info(f"Total content length for {len(items)} files with content out of {len(file_ids)} requested: {total_length} characters")
        return total_length


    def generate_suggested_questions(self, notebook) -> Dict:
        """
        Generate suggested questions using the knowledge base agent.
        
        Args:
            notebook: Notebook instance
            
        Returns:
            Dict with suggestions or error information
        """
        try:
            # Note: Suggestions are now generated based on notebook content only
            # Session-specific history can be added if needed
            history = []
            
            # Create suggestion prompt
            suggestion_prompt = """Based on our conversation and the knowledge base, suggest 3-5 relevant follow-up questions that would be helpful to explore. 
            Make the questions specific and actionable. Format your response as a simple numbered list."""
            
            # Use integrated agentic RAG to generate suggestions
            result = self.ask_agent_direct(
                notebook=notebook,
                user_id=notebook.user.id,
                question=suggestion_prompt,
                history=history
            )
            
            if result.get('success'):
                content = result.get('content', '')
                
                # Parse suggestions from response (simple parsing for numbered list)
                suggestions = []
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and (line[0].isdigit() or line.startswith('-')):
                        # Remove numbering and clean up
                        clean_question = line.split('.', 1)[-1].strip()
                        if clean_question.startswith('-'):
                            clean_question = clean_question[1:].strip()
                        if clean_question:
                            suggestions.append(clean_question)
                
                # Fallback: if no parsed suggestions, use the raw content
                if not suggestions:
                    suggestions = [content]
                
                self.log_notebook_operation(
                    "agent_suggestions_generated",
                    str(notebook.id),
                    notebook.user.id,
                    suggestion_count=len(suggestions)
                )
                
                return {
                    "success": True,
                    "suggestions": suggestions[:5]  # Limit to 5 suggestions
                }
            else:
                return {
                    "error": result.get('error', 'Failed to generate suggestions'),
                    "status_code": result.get('status_code', status.HTTP_500_INTERNAL_SERVER_ERROR)
                }

        except Exception as e:
            self.logger.exception(f"Failed to generate agent suggestions for notebook {notebook.id}: {e}")
            return {
                "error": "Failed to generate suggestions",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)}
            }

    # Agentic RAG Integration Methods
    
    def get_or_create_agent_session(self, notebook: Notebook, user_id: int) -> Dict:
        """
        Get or create an agent session for the notebook's dataset.
        
        Args:
            notebook: Notebook instance
            user_id: User ID for session management
            
        Returns:
            Dict with session info or error
        """
        try:
            # Validate notebook access
            self.validate_notebook_access(notebook, notebook.user)
            
            # Check if notebook has RagFlow dataset ID
            if not notebook.ragflow_dataset_id:
                # Try to create a dataset for this notebook
                try:
                    dataset_result = self.ragflow_client.create_dataset(
                        name=f"notebook_{notebook.id}_{notebook.name}",
                        description=notebook.description or f"Dataset for notebook '{notebook.name}'"
                    )
                    notebook.ragflow_dataset_id = dataset_result['id']
                    notebook.save()
                    logger.info(f"Created RagFlow dataset {dataset_result['id']} for notebook {notebook.id}")
                except Exception as e:
                    logger.error(f"Failed to create RagFlow dataset for notebook {notebook.id}: {e}")
                    return {
                        "error": f"Notebook has no RagFlow dataset and failed to create one: {str(e)}",
                        "status_code": status.HTTP_400_BAD_REQUEST
                    }

            # Check if dataset exists in RagFlow
            dataset_info = self.ragflow_client.get_dataset(notebook.ragflow_dataset_id)
            if not dataset_info:
                return {
                    "error": "RagFlow dataset not found",
                    "status_code": status.HTTP_400_BAD_REQUEST
                }
            
            # Check cache for existing session
            cache_key = f"ragflow_agent_session_{notebook.id}_{user_id}"
            cached_session = cache.get(cache_key)
            
            if cached_session:
                logger.info(f"Using cached agent session for notebook {notebook.id}")
                return {
                    "success": True,
                    "session_info": cached_session,
                    "cached": True
                }
            
            # Get or create knowledge base agent
            agent_result = self._get_or_create_knowledge_base_agent(notebook.ragflow_dataset_id)
            if not agent_result.get('success'):
                return agent_result
            
            agent_id = agent_result['agent_id']
            
            # Create new session with the agent (no parameters needed without begin node)
            session_result = self.ragflow_client.create_session(
                agent_id=agent_id
            )
            
            # Cache the session info
            session_info = {
                "session": session_result,
                "agent_id": agent_id,
                "dataset_id": notebook.ragflow_dataset_id,
                "notebook_id": notebook.id,
                "created_for_user": user_id
            }
            
            cache.set(cache_key, session_info, timeout=self._session_cache_timeout)
            
            self.log_notebook_operation(
                "agent_session_created",
                str(notebook.id),
                user_id,
                session_id=session_result.get('id', 'unknown'),
                agent_id=agent_id
            )
            
            return {
                "success": True,
                "session_info": session_info,
                "cached": False
            }
            
        except (RagFlowClientError, RagFlowSessionError) as e:
            logger.exception(f"RagFlow error creating agent session for notebook {notebook.id}: {e}")
            return {
                "error": f"RagFlow service error: {e}",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"ragflow_error": str(e)}
            }
        except Exception as e:
            logger.exception(f"Failed to create agent session for notebook {notebook.id}: {e}")
            return {
                "error": "Failed to create agent session",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)}
            }
    
    def ask_agent_streaming(self, notebook: Notebook, user_id: int, question: str, 
                           history: List[Dict] = None) -> Generator:
        """
        Ask the knowledge base agent a question with streaming response.
        
        Args:
            notebook: Notebook instance
            user_id: User ID
            question: Question to ask
            history: Optional conversation history
            
        Returns:
            Generator yielding streaming response chunks
        """
        try:
            # Get or create agent session
            session_result = self.get_or_create_agent_session(notebook, user_id)
            
            if not session_result.get('success'):
                # Yield error as SSE format
                error_msg = session_result.get('error', 'Unknown error')
                yield f"data: {{'type': 'error', 'message': '{error_msg}'}}\n\n"
                return
            
            session_info = session_result.get('session_info')
            session = session_info.get('session')
            agent_id = session_info.get('agent_id')
            session_id = session.get('id')
            
            # Add history context if provided
            if history:
                context_prompt = self._build_context_from_history(history)
                enhanced_question = f"{context_prompt}\n\nCurrent question: {question}"
            else:
                enhanced_question = question
            
            # Ask the agent with streaming
            logger.info(f"Asking agent for notebook {notebook.id}: {question[:100]}...")
            response = self.ragflow_client.ask_session(
                agent_id=agent_id,
                session_id=session_id,
                question=enhanced_question,
                stream=True
            )
            
            # Stream the response
            for chunk in response:
                try:
                    if hasattr(chunk, 'content') and chunk.content:
                        # Format as SSE
                        content = chunk.content.replace('\n', '\\n').replace('"', '\\"')
                        yield f"data: {{'type': 'token', 'text': '{content}'}}\n\n"
                    elif isinstance(chunk, str):
                        # Handle string responses
                        content = chunk.replace('\n', '\\n').replace('"', '\\"')
                        yield f"data: {{'type': 'token', 'text': '{content}'}}\n\n"
                        
                except Exception as chunk_error:
                    logger.error(f"Error processing agent response chunk: {chunk_error}")
                    continue
            
            # Send completion signal
            yield f"data: {{'type': 'done', 'message': 'Agent response complete'}}\n\n"
            
            self.log_notebook_operation(
                "agent_question_asked",
                str(notebook.id),
                user_id,
                question_length=len(question)
            )
            
        except (RagFlowClientError, RagFlowSessionError) as e:
            logger.exception(f"RagFlow error during agent query: {e}")
            yield f"data: {{'type': 'error', 'message': 'RagFlow service error: {str(e)}'}}\n\n"
            
        except Exception as e:
            logger.exception(f"Error during agent streaming query: {e}")
            yield f"data: {{'type': 'error', 'message': 'Agent query failed: {str(e)}'}}\n\n"
    
    def ask_agent_direct(self, notebook: Notebook, user_id: int, question: str, 
                        history: List[Dict] = None) -> Dict:
        """
        Ask the knowledge base agent a question with direct response.
        
        Args:
            notebook: Notebook instance
            user_id: User ID
            question: Question to ask
            history: Optional conversation history
            
        Returns:
            Dict with agent response
        """
        try:
            # Get or create agent session
            session_result = self.get_or_create_agent_session(notebook, user_id)
            
            if not session_result.get('success'):
                return session_result
            
            session_info = session_result.get('session_info')
            session = session_info.get('session')
            agent_id = session_info.get('agent_id')
            session_id = session.get('id')
            
            # Add history context if provided
            if history:
                context_prompt = self._build_context_from_history(history)
                enhanced_question = f"{context_prompt}\n\nCurrent question: {question}"
            else:
                enhanced_question = question
            
            # Ask the agent without streaming
            response = self.ragflow_client.ask_session(
                agent_id=agent_id,
                session_id=session_id,
                question=enhanced_question,
                stream=False
            )
            
            # Extract content from response
            if hasattr(response, 'content'):
                content = response.content
            elif isinstance(response, str):
                content = response
            else:
                content = str(response)
            
            self.log_notebook_operation(
                "agent_question_asked_direct",
                str(notebook.id),
                user_id,
                question_length=len(question),
                response_length=len(content)
            )
            
            return {
                "success": True,
                "content": content,
                "agent_response": response
            }
            
        except (RagFlowClientError, RagFlowSessionError) as e:
            logger.exception(f"RagFlow error during direct agent query: {e}")
            return {
                "error": f"RagFlow service error: {e}",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"ragflow_error": str(e)}
            }
        except Exception as e:
            logger.exception(f"Error during direct agent query: {e}")
            return {
                "error": "Agent query failed",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)}
            }
    
    def clear_agent_session(self, notebook: Notebook, user_id: int) -> Dict:
        """
        Clear the agent session for a notebook.
        
        Args:
            notebook: Notebook instance
            user_id: User ID
            
        Returns:
            Dict with operation result
        """
        try:
            cache_key = f"ragflow_agent_session_{notebook.id}_{user_id}"
            cache.delete(cache_key)
            
            self.log_notebook_operation(
                "agent_session_cleared",
                str(notebook.id),
                user_id
            )
            
            return {
                "success": True,
                "message": "Agent session cleared"
            }
            
        except Exception as e:
            logger.exception(f"Error clearing agent session: {e}")
            return {
                "error": "Failed to clear agent session",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)}
            }
    
    def _get_or_create_knowledge_base_agent(self, dataset_id: str) -> Dict:
        """
        Get or create knowledge base agent for the dataset using a simplified DSL.

        Args:
            dataset_id: RagFlow dataset ID

        Returns:
            Dict with agent info or error
        """
        try:
            # Check cache first
            cache_key = f"ragflow_kb_agent_{dataset_id}"
            cached_agent = cache.get(cache_key)

            if cached_agent:
                return {
                    "success": True,
                    "agent_id": cached_agent,
                    "cached": True
                }

            # Create unique agent title
            agent_title = f"Knowledge Base Agent - Dataset {dataset_id[:8]}"
            agent_description = f"Specialized agent for dataset {dataset_id}"

            # Check if agent already exists and delete it to recreate with new DSL
            try:
                existing_agents = self.ragflow_client.list_agents(title=agent_title)
                if existing_agents:
                    agent_id = existing_agents[0]['id']
                    logger.info(f"Found existing agent {agent_id} for dataset {dataset_id}, deleting to recreate with new DSL")

                    # Delete the old agent to recreate with simplified DSL
                    try:
                        self.ragflow_client.delete_agent(agent_id)
                        logger.info(f"Deleted old agent {agent_id}")
                    except Exception as del_error:
                        logger.warning(f"Failed to delete old agent {agent_id}: {del_error}")

                    # Clear cache
                    cache.delete(cache_key)
                else:
                    # No agents found, create new one
                    logger.info(f"No existing agents found with title '{agent_title}', creating new one")
            except RagFlowClientError as e:
                # If error contains "doesn't exist", it means no agents exist yet
                if "doesn't exist" in str(e).lower():
                    logger.info(f"No agents exist yet, creating first agent for dataset {dataset_id}")
                else:
                    # Some other error occurred
                    logger.error(f"Error checking for existing agents: {e}")
                    return {
                        "error": f"Failed to check existing agents: {str(e)}",
                        "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                        "details": {"error": str(e)}
                    }

            # Create simplified DSL without begin node
            dsl = {
                "components": {
                    "Agent:KnowledgeBot": {
                        "downstream": ["Message:Response"],
                        "obj": {
                            "component_name": "Agent",
                            "params": {
                                "llm_id": getattr(settings, 'RAGFLOW_CHAT_MODEL', 'deepseek-chat@DeepSeek'),
                                "temperature": 0.1,
                                "max_tokens": 1024,
                                "max_rounds": 1,
                                "sys_prompt": "You are a helpful knowledge base assistant. Answer questions based strictly on the information available in the knowledge base. If information is not available, clearly state that you cannot find it in the knowledge base.",
                                "prompts": [
                                    {
                                        "role": "user",
                                        "content": "{sys.query}"
                                    }
                                ],
                                "tools": [
                                    {
                                        "component_name": "Retrieval",
                                        "name": "Retrieval",
                                        "params": {
                                            "cross_languages": [],
                                            "description": "Retrieve from the knowledge bases.",
                                            "empty_response": "No relevant information found in the knowledge base.",
                                            "kb_ids": [dataset_id],
                                            "keywords_similarity_weight": 0.7,
                                            "outputs": {
                                                "formalized_content": {
                                                    "type": "string",
                                                    "value": ""
                                                }
                                            },
                                            "rerank_id": "",
                                            "similarity_threshold": 0.2,
                                            "top_k": 1024,
                                            "top_n": 8,
                                            "use_kg": False
                                        }
                                    }
                                ]
                            }
                        },
                        "upstream": []
                    },
                    "Message:Response": {
                        "downstream": [],
                        "obj": {
                            "component_name": "Message",
                            "params": {
                                "content": ["{Agent:KnowledgeBot@content}"]
                            }
                        },
                        "upstream": ["Agent:KnowledgeBot"]
                    }
                },
                "path": ["Agent:KnowledgeBot", "Message:Response"],
                "history": [],
                "messages": [],
                "retrieval": []
            }

            # Create the agent
            create_result = self.ragflow_client.create_agent(
                title=agent_title,
                dsl=dsl,
                description=agent_description
            )

            if not create_result.get('success'):
                logger.error(f"RagFlow agent creation failed: {create_result}")
                return {
                    "error": "Failed to create knowledge base agent",
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "details": create_result
                }

            # Get the created agent ID by listing agents with the same title
            try:
                created_agents = self.ragflow_client.list_agents(title=agent_title)
                if not created_agents:
                    return {
                        "error": "Agent created but not found when listing",
                        "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR
                    }
                agent_id = created_agents[0]['id']
                logger.info(f"Created new agent {agent_id} for dataset {dataset_id}")
            except RagFlowClientError as e:
                logger.error(f"Failed to find created agent: {e}")
                return {
                    "error": "Agent was created but could not be retrieved",
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "details": {"error": str(e)}
                }

            # Cache the agent ID
            cache.set(cache_key, agent_id, timeout=self._agent_cache_timeout)

            return {
                "success": True,
                "agent_id": agent_id,
                "cached": False
            }

        except Exception as e:
            logger.exception(f"Error creating knowledge base agent for dataset {dataset_id}: {e}")
            return {
                "error": "Failed to create knowledge base agent",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)}
            }
    
    def _build_context_from_history(self, history: List[Dict]) -> str:
        """Build context prompt from conversation history."""
        if not history:
            return ""
        
        context_parts = ["Previous conversation context:"]
        for msg in history[-5:]:  # Use last 5 messages for context
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            if content:
                context_parts.append(f"{role.title()}: {content}")
        
        return "\n".join(context_parts)
    
    def get_agent_info(self, notebook: Notebook) -> Dict:
        """Get information about the current knowledge base agent."""
        try:
            if not notebook.ragflow_dataset_id:
                return {
                    "available": False,
                    "error": "No RagFlow dataset found"
                }

            agent_result = self._get_or_create_knowledge_base_agent(notebook.ragflow_dataset_id)
            
            if not agent_result.get('success'):
                return {
                    "available": False,
                    "error": agent_result.get('error', 'Unknown error')
                }
            
            agent_id = agent_result['agent_id']
            agents = self.ragflow_client.list_agents(id=agent_id)
            
            if not agents:
                return {
                    "available": False,
                    "error": "Agent not found"
                }
            
            agent = agents[0]
            return {
                "available": True,
                "name": agent.get('title', 'Unknown'),
                "id": agent.get('id', 'Unknown'),
                "description": agent.get('description', ''),
            }
            
        except Exception as e:
            logger.exception(f"Error getting agent info: {e}")
            return {
                "available": False,
                "error": str(e)
            }

    # Session Management Methods
    
    @transaction.atomic
    def create_chat_session(self, notebook: Notebook, user_id: int, title: str = None) -> Dict:
        """
        Create a new chat session for a notebook.
        
        Args:
            notebook: Notebook instance
            user_id: User ID
            title: Optional session title
            
        Returns:
            Dict with session info or error
        """
        try:
            # Validate notebook access
            self.validate_notebook_access(notebook, notebook.user)
            
            # Get or create agent for this notebook's dataset
            agent_result = self._get_or_create_knowledge_base_agent_for_session(notebook)
            if not agent_result.get('success'):
                return agent_result
            
            agent_id = agent_result['agent_id']
            
            # Create RagFlow session (no parameters needed without begin node)
            ragflow_session = self.ragflow_client.create_session(
                agent_id=agent_id
            )
            
            # Create local session record
            chat_session = ChatSession.objects.create(
                notebook=notebook,
                title=title,
                ragflow_session_id=ragflow_session.get('id'),
                ragflow_agent_id=agent_id,
                session_metadata={
                    'created_by_user': str(user_id),
                    'dataset_id': str(notebook.ragflow_dataset_id) if notebook.ragflow_dataset_id else None
                }
            )
            
            self.log_notebook_operation(
                "chat_session_created",
                str(notebook.id),
                user_id,
                session_id=str(chat_session.session_id),
                ragflow_session_id=ragflow_session.get('id')
            )
            
            return {
                "success": True,
                "session": {
                    "id": str(chat_session.session_id),
                    "title": chat_session.title,
                    "status": chat_session.status,
                    "created_at": chat_session.created_at.isoformat(),
                    "message_count": 0
                },
                "ragflow_session_id": ragflow_session.get('id')
            }
            
        except (RagFlowClientError, RagFlowSessionError) as e:
            logger.exception(f"RagFlow error creating session for notebook {notebook.id}: {e}")
            return {
                "error": f"RagFlow service error: {e}",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"ragflow_error": str(e)}
            }
        except Exception as e:
            logger.exception(f"Failed to create chat session for notebook {notebook.id}: {e}")
            return {
                "error": "Failed to create chat session",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)}
            }
    
    def list_chat_sessions(self, notebook: Notebook, user_id: int, include_closed: bool = False) -> Dict:
        """
        List all chat sessions for a notebook.
        
        Args:
            notebook: Notebook instance
            user_id: User ID
            include_closed: Whether to include closed/archived sessions
            
        Returns:
            Dict with sessions list or error
        """
        try:
            # Validate notebook access
            self.validate_notebook_access(notebook, notebook.user)
            
            # Get sessions
            sessions_query = ChatSession.objects.filter(notebook=notebook)
            
            if not include_closed:
                sessions_query = sessions_query.filter(status='active')
            
            sessions = sessions_query.order_by('-last_activity')
            
            # Format sessions for API
            sessions_data = []
            for session in sessions:
                last_message = session.get_last_message()
                sessions_data.append({
                    "id": str(session.session_id),
                    "title": session.title,
                    "status": session.status,
                    "message_count": session.get_message_count(),
                    "last_activity": session.last_activity.isoformat(),
                    "created_at": session.created_at.isoformat(),
                    "last_message": {
                        "sender": last_message.sender,
                        "message": last_message.message[:100],
                        "timestamp": last_message.timestamp.isoformat()
                    } if last_message else None
                })
            
            return {
                "success": True,
                "sessions": sessions_data,
                "total_count": len(sessions_data)
            }
            
        except Exception as e:
            logger.exception(f"Failed to list sessions for notebook {notebook.id}: {e}")
            return {
                "error": "Failed to list chat sessions",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)}
            }
    
    @transaction.atomic
    def close_chat_session(self, session_id: str, notebook: Notebook, user_id: int, 
                          delete_ragflow_session: bool = True) -> Dict:
        """
        Close a chat session.
        
        Args:
            session_id: Session UUID
            notebook: Notebook instance
            user_id: User ID
            delete_ragflow_session: Whether to delete the RagFlow session
            
        Returns:
            Dict with operation result
        """
        try:
            # Validate notebook access
            self.validate_notebook_access(notebook, notebook.user)
            
            # Get the session
            session = ChatSession.objects.filter(
                session_id=session_id, 
                notebook=notebook
            ).first()
            
            if not session:
                return {
                    "error": "Session not found",
                    "status_code": status.HTTP_404_NOT_FOUND
                }
            
            # Delete RagFlow session if requested
            if delete_ragflow_session and session.ragflow_session_id and session.ragflow_agent_id:
                try:
                    self.ragflow_client.delete_agent_sessions(
                        agent_id=session.ragflow_agent_id,
                        session_ids=[session.ragflow_session_id]
                    )
                except Exception as e:
                    logger.warning(f"Failed to delete RagFlow session {session.ragflow_session_id}: {e}")
            
            # Close the session
            session.close()
            
            self.log_notebook_operation(
                "chat_session_closed",
                str(notebook.id),
                user_id,
                session_id=str(session.session_id)
            )
            
            return {
                "success": True,
                "session_id": str(session.session_id),
                "status": session.status
            }
            
        except Exception as e:
            logger.exception(f"Failed to close session {session_id}: {e}")
            return {
                "error": "Failed to close chat session",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)}
            }
    
    def get_chat_session(self, session_id: str, notebook: Notebook, user_id: int) -> Dict:
        """
        Get details of a specific chat session.
        
        Args:
            session_id: Session UUID
            notebook: Notebook instance
            user_id: User ID
            
        Returns:
            Dict with session details or error
        """
        try:
            # Validate notebook access
            self.validate_notebook_access(notebook, notebook.user)
            
            # Get the session
            session = ChatSession.objects.filter(
                session_id=session_id, 
                notebook=notebook
            ).first()
            
            if not session:
                return {
                    "error": "Session not found",
                    "status_code": status.HTTP_404_NOT_FOUND
                }
            
            # Get recent messages
            recent_messages = session.messages.order_by('-timestamp')[:50]
            messages_data = []
            
            for msg in reversed(recent_messages):  # Reverse to get chronological order
                messages_data.append({
                    "id": msg.id,
                    "sender": msg.sender,
                    "message": msg.message,
                    "timestamp": msg.timestamp.isoformat(),
                    "sources": msg.get_sources(),
                    "confidence": msg.get_confidence()
                })
            
            return {
                "success": True,
                "session": {
                    "id": str(session.session_id),
                    "title": session.title,
                    "status": session.status,
                    "message_count": session.get_message_count(),
                    "created_at": session.created_at.isoformat(),
                    "last_activity": session.last_activity.isoformat(),
                    "messages": messages_data
                }
            }
            
        except Exception as e:
            logger.exception(f"Failed to get session {session_id}: {e}")
            return {
                "error": "Failed to get chat session",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)}
            }
    
    @transaction.atomic
    def update_session_title(self, session_id: str, notebook: Notebook, user_id: int, title: str) -> Dict:
        """
        Update the title of a chat session.
        
        Args:
            session_id: Session UUID
            notebook: Notebook instance
            user_id: User ID
            title: New title
            
        Returns:
            Dict with operation result
        """
        try:
            # Validate notebook access
            self.validate_notebook_access(notebook, notebook.user)
            
            # Get the session
            session = ChatSession.objects.filter(
                session_id=session_id, 
                notebook=notebook
            ).first()
            
            if not session:
                return {
                    "error": "Session not found",
                    "status_code": status.HTTP_404_NOT_FOUND
                }
            
            # Update title
            session.title = title.strip()
            session.save(update_fields=['title', 'updated_at'])
            
            return {
                "success": True,
                "session_id": str(session.session_id),
                "title": session.title
            }
            
        except Exception as e:
            logger.exception(f"Failed to update session title {session_id}: {e}")
            return {
                "error": "Failed to update session title",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)}
            }
    
    def create_session_chat_stream(self, session_id: str, notebook: Notebook, user_id: int, question: str) -> Generator:
        """
        Create chat stream for a specific session.

        Args:
            session_id: Session UUID
            notebook: Notebook instance
            user_id: User ID
            question: User's question

        Returns:
            Generator yielding chat stream chunks
        """
        def session_stream():
            accumulated_content = ""

            try:
                # Send immediate keepalive to establish SSE connection
                keepalive_payload = json.dumps({'type': 'status', 'message': 'Connected'})
                yield f"data: {keepalive_payload}\n\n"

                # Validate notebook access
                self.validate_notebook_access(notebook, notebook.user)

                # Get the session
                session = ChatSession.objects.filter(
                    session_id=session_id,
                    notebook=notebook,
                    status='active'
                ).first()

                if not session:
                    error_payload = json.dumps({'type': 'error', 'message': 'Session not found or inactive'})
                    yield f"data: {error_payload}\n\n"
                    return

                # Record user message
                user_message = SessionChatMessage.objects.create(
                    session=session,
                    notebook=notebook,
                    sender='user',
                    message=question
                )

                self.log_notebook_operation(
                    "session_user_message_recorded",
                    str(notebook.id),
                    user_id,
                    session_id=str(session.session_id),
                    message_id=str(user_message.id)
                )

                # Use RagFlow session directly
                if not session.ragflow_session_id or not session.ragflow_agent_id:
                    error_payload = json.dumps({'type': 'error', 'message': 'Session not properly initialized'})
                    yield f"data: {error_payload}\n\n"
                    return

                logger.info(f"Starting streaming ask for session {session.ragflow_session_id} with agent {session.ragflow_agent_id}")
                logger.info(f"User question: {question[:200]}")

                # Ask the agent with streaming
                try:
                    response = self.ragflow_client.ask_session(
                        agent_id=session.ragflow_agent_id,
                        session_id=session.ragflow_session_id,
                        question=question,
                        stream=True
                    )
                    logger.info(f"Successfully initiated streaming response from RagFlow for question: {question[:50]}...")
                except Exception as ask_error:
                    logger.exception(f"Failed to ask RagFlow session: {ask_error}")
                    error_payload = json.dumps({'type': 'error', 'message': f'Failed to contact agent: {str(ask_error)}'})
                    yield f"data: {error_payload}\n\n"
                    return

                # According to RagFlow SDK docs, streaming returns an iterator of Message objects
                # where each Message has a .content attribute that accumulates the full response
                message_count = 0
                for message in response:
                    message_count += 1
                    try:
                        if hasattr(message, 'content') and message.content:
                            # Get the new content (delta from accumulated content)
                            new_content = message.content[len(accumulated_content):]

                            if new_content:
                                # Format as SSE - use proper JSON encoding
                                payload = json.dumps({'type': 'token', 'text': new_content})
                                yield f"data: {payload}\n\n"
                                logger.debug(f"Yielded {len(new_content)} new characters (message #{message_count})")

                            # Update accumulated content
                            accumulated_content = message.content
                        else:
                            logger.warning(f"Message #{message_count} has no content attribute or empty content")

                    except Exception as chunk_error:
                        logger.error(f"Error processing message chunk #{message_count}: {chunk_error}")
                        continue

                logger.info(f"Streaming completed, processed {message_count} messages, accumulated {len(accumulated_content)} characters")

                # Send completion signal
                completion_payload = json.dumps({'type': 'done', 'message': 'Response complete'})
                yield f"data: {completion_payload}\n\n"

                # Save assistant response
                if accumulated_content:
                    SessionChatMessage.objects.create(
                        session=session,
                        notebook=notebook,
                        sender='assistant',
                        message=accumulated_content
                    )

                    self.log_notebook_operation(
                        "session_assistant_message_recorded",
                        str(notebook.id),
                        user_id,
                        session_id=str(session.session_id),
                        response_length=len(accumulated_content)
                    )

            except Exception as e:
                logger.exception(f"Error in session stream: {e}")
                error_payload = json.dumps({'type': 'error', 'message': f'Response generation failed: {str(e)}'})
                yield f"data: {error_payload}\n\n"

        return session_stream()
    
    def _get_or_create_knowledge_base_agent_for_session(self, notebook: Notebook) -> Dict:
        """
        Get or create knowledge base agent for session management.
        Wrapper around existing method for session-specific logic.
        """
        if not notebook.ragflow_dataset_id:
            return {
                "error": "Notebook has no RagFlow dataset",
                "status_code": status.HTTP_400_BAD_REQUEST
            }

        # Check if dataset exists in RagFlow
        dataset_info = self.ragflow_client.get_dataset(notebook.ragflow_dataset_id)
        if not dataset_info:
            return {
                "error": "RagFlow dataset not found",
                "status_code": status.HTTP_400_BAD_REQUEST
            }

        return self._get_or_create_knowledge_base_agent(notebook.ragflow_dataset_id)
    
    def get_session_count_for_notebook(self, notebook: Notebook) -> int:
        """Get the number of active sessions for a notebook."""
        return ChatSession.objects.filter(notebook=notebook, status='active').count()
    
    def cleanup_inactive_sessions(self, notebook: Notebook, max_age_hours: int = 24) -> Dict:
        """
        Clean up inactive sessions older than specified hours.
        
        Args:
            notebook: Notebook instance
            max_age_hours: Maximum age in hours for inactive sessions
            
        Returns:
            Dict with cleanup results
        """
        try:
            from django.utils import timezone
            from datetime import timedelta
            
            cutoff_time = timezone.now() - timedelta(hours=max_age_hours)
            
            # Find inactive sessions
            inactive_sessions = ChatSession.objects.filter(
                notebook=notebook,
                status='active',
                last_activity__lt=cutoff_time
            )
            
            cleanup_count = 0
            for session in inactive_sessions:
                # Close the session (this also handles RagFlow cleanup)
                session.close()
                cleanup_count += 1
            
            logger.info(f"Cleaned up {cleanup_count} inactive sessions for notebook {notebook.id}")
            
            return {
                "success": True,
                "cleaned_up_count": cleanup_count
            }
            
        except Exception as e:
            logger.exception(f"Failed to cleanup sessions for notebook {notebook.id}: {e}")
            return {
                "error": "Failed to cleanup inactive sessions",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)}
            }