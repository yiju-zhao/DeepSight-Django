"""
RagFlow Client - Wrapper around ragflow-sdk with error handling and configuration.
"""

import logging
import time
from typing import Dict, List, Optional, Any
from django.conf import settings
from ragflow_sdk import RAGFlow
from ragflow_sdk.modules.dataset import DataSet

logger = logging.getLogger(__name__)


class RagFlowClientError(Exception):
    """Base exception for RagFlow client errors."""
    pass


class RagFlowDatasetError(RagFlowClientError):
    """Exception for dataset-related errors."""
    pass


class RagFlowDocumentError(RagFlowClientError):
    """Exception for document-related errors."""
    pass


class RagFlowChatError(RagFlowClientError):
    """Exception for chat-related errors."""
    pass


class RagFlowSessionError(RagFlowClientError):
    """Exception for session-related errors."""
    pass


class RagFlowClient:
    """
    RagFlow client wrapper with error handling, retry logic, and logging.
    
    Provides a clean interface for interacting with RagFlow API while handling
    common errors and providing comprehensive logging.
    """
    
    def __init__(self, api_key: str = None, base_url: str = None):
        """
        Initialize RagFlow client.
        
        Args:
            api_key: RagFlow API key (defaults to settings.RAGFLOW_API_KEY)
            base_url: RagFlow base URL (defaults to settings.RAGFLOW_BASE_URL)
        """
        self.api_key = api_key or getattr(settings, 'RAGFLOW_API_KEY', None)
        self.base_url = base_url or getattr(settings, 'RAGFLOW_BASE_URL', 'http://localhost:9380')
        
        if not self.api_key:
            raise RagFlowClientError("RagFlow API key is required")
        
        self.client = RAGFlow(api_key=self.api_key, base_url=self.base_url)
        logger.info(f"RagFlow client initialized with base_url: {self.base_url}")
    
    def _retry_on_failure(self, func, *args, max_retries: int = 3, delay: float = 1.0, **kwargs):
        """
        Retry a function on failure with exponential backoff.
        
        Args:
            func: Function to retry
            *args: Function arguments
            max_retries: Maximum number of retries
            delay: Initial delay between retries
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            RagFlowClientError: If all retries fail
        """
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                result = func(*args, **kwargs)
                if attempt > 0:
                    logger.info(f"Function succeeded after {attempt} retries")
                return result
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    wait_time = delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries + 1} attempts failed. Last error: {e}")
        
        raise RagFlowClientError(f"Operation failed after {max_retries + 1} attempts: {last_error}")
    
    # Dataset Management
    def create_dataset(self, name: str, description: str = "", **kwargs) -> Dict:
        """
        Create a new RagFlow dataset.
        
        Args:
            name: Dataset name
            description: Dataset description
            **kwargs: Additional dataset configuration
            
        Returns:
            Dict containing dataset information
            
        Raises:
            RagFlowDatasetError: If dataset creation fails
        """
        try:
            logger.info(f"Creating RagFlow dataset: {name}")
            
            # Create parser config object with mixed data types as required by API
            parser_config_dict = {
                "chunk_token_num": 512,
                "delimiter": "#",
                "html4excel": False,  # boolean expected
                "layout_recognize": "true",  # string expected
                "raptor": {"use_raptor": True}  # boolean expected
            }
            # Create a ParserConfig object with proper rag and res_dict parameters
            parser_config = DataSet.ParserConfig(self.client, parser_config_dict)

            # Set default configuration
            dataset_config = {
                'name': name,
                'description': description,
                'chunk_method': getattr(settings, 'RAGFLOW_DEFAULT_CHUNK_METHOD', 'naive'),
                'embedding_model': getattr(settings, 'RAGFLOW_DEFAULT_EMBEDDING_MODEL', 'text-embedding-3-large@OpenAI'),
                'parser_config': parser_config
            }
            
            def _create():
                return self.client.create_dataset(**dataset_config)
            
            dataset = self._retry_on_failure(_create)
            logger.info(f"Dataset created successfully: {dataset.id}")
            
            return {
                'id': dataset.id,
                'name': dataset.name,
                'description': getattr(dataset, 'description', description),
                'status': 'created'
            }
            
        except Exception as e:
            logger.error(f"Failed to create dataset '{name}': {e}")
            raise RagFlowDatasetError(f"Failed to create dataset: {e}")
    
    def delete_dataset(self, dataset_id: str) -> bool:
        """
        Delete a RagFlow dataset.
        
        Args:
            dataset_id: Dataset ID to delete
            
        Returns:
            True if successful
            
        Raises:
            RagFlowDatasetError: If deletion fails
        """
        try:
            logger.info(f"Deleting RagFlow dataset: {dataset_id}")
            
            def _delete():
                self.client.delete_datasets(ids=[dataset_id])
                return True
            
            result = self._retry_on_failure(_delete)
            logger.info(f"Dataset deleted successfully: {dataset_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to delete dataset '{dataset_id}': {e}")
            raise RagFlowDatasetError(f"Failed to delete dataset: {e}")
    
    def get_dataset(self, dataset_id: str) -> Optional[Dict]:
        """
        Get dataset information.

        Args:
            dataset_id: Dataset ID

        Returns:
            Dataset information or None if not found
        """
        try:
            datasets = self.client.list_datasets(id=dataset_id)
            if datasets:
                dataset = datasets[0]
                return {
                    'id': dataset.id,
                    'name': dataset.name,
                    'description': getattr(dataset, 'description', ''),
                    'status': getattr(dataset, 'status', 'unknown')
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get dataset '{dataset_id}': {e}")
            return None

    def update_dataset(self, dataset_id: str, update_config: Dict = None) -> bool:
        """
        Update a RagFlow dataset configuration.
        This triggers re-processing of documents with new settings (embedding model, chunk method, etc.)

        Args:
            dataset_id: Dataset ID to update
            update_config: Dictionary of configuration updates. If None, triggers re-processing with current settings.

        Returns:
            True if update was successful

        Raises:
            RagFlowDatasetError: If update fails
        """
        try:
            logger.info(f"Updating RagFlow dataset: {dataset_id}")

            # Get the dataset first
            datasets = self.client.list_datasets(id=dataset_id)
            if not datasets:
                raise RagFlowDatasetError(f"Dataset {dataset_id} not found")

            dataset = datasets[0]

            # If no update config provided, use minimal update to trigger re-processing
            if update_config is None:
                # Get current embedding model or use default
                current_embedding = getattr(dataset, 'embedding_model', None)
                if current_embedding is None:
                    current_embedding = getattr(settings, 'RAGFLOW_DEFAULT_EMBEDDING_MODEL', 'text-embedding-3-large@OpenAI')

                update_config = {
                    "embedding_model": current_embedding
                }

            def _update():
                dataset.update(update_config)
                return True

            result = self._retry_on_failure(_update)
            logger.info(f"Dataset updated successfully: {dataset_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to update dataset '{dataset_id}': {e}")
            raise RagFlowDatasetError(f"Failed to update dataset: {e}")
    
    # Document Management
    def upload_document(self, dataset_id: str, content: str, display_name: str) -> Dict:
        """
        Upload a document to a RagFlow dataset.

        Args:
            dataset_id: Target dataset ID
            content: Document content (markdown text)
            display_name: Display name for the document

        Returns:
            Dict containing document information

        Raises:
            RagFlowDocumentError: If upload fails
        """
        try:
            logger.info(f"Uploading document '{display_name}' to dataset {dataset_id}")

            # Get the dataset
            datasets = self.client.list_datasets(id=dataset_id)
            if not datasets:
                raise RagFlowDocumentError(f"Dataset {dataset_id} not found")

            dataset = datasets[0]

            # Prepare document for upload
            document_data = [{
                'display_name': display_name,
                'blob': content.encode('utf-8')
            }]

            def _upload():
                uploaded_docs = dataset.upload_documents(document_data)
                return uploaded_docs[0] if uploaded_docs else None

            document = self._retry_on_failure(_upload)

            if not document:
                raise RagFlowDocumentError("Document upload returned no result")

            logger.info(f"Document uploaded successfully: {document.id}")

            return {
                'id': document.id,
                'name': display_name,
                'status': 'uploaded'
            }

        except Exception as e:
            logger.error(f"Failed to upload document '{display_name}' to dataset '{dataset_id}': {e}")
            raise RagFlowDocumentError(f"Failed to upload document: {e}")

    def upload_document_file(self, dataset_id: str, file_content: bytes, filename: str) -> Dict:
        """
        Upload a file to a RagFlow dataset using file content from storage.

        Args:
            dataset_id: Target dataset ID
            file_content: File content as bytes
            filename: Name of the file (with extension)

        Returns:
            Dict containing document information

        Raises:
            RagFlowDocumentError: If upload fails
        """
        try:
            logger.info(f"Uploading file '{filename}' to dataset {dataset_id}")

            # Get the dataset
            datasets = self.client.list_datasets(id=dataset_id)
            if not datasets:
                raise RagFlowDocumentError(f"Dataset {dataset_id} not found")

            dataset = datasets[0]

            # Prepare document for upload - use file content directly
            document_data = [{
                'display_name': filename,
                'blob': file_content
            }]

            def _upload():
                uploaded_docs = dataset.upload_documents(document_data)
                return uploaded_docs[0] if uploaded_docs else None

            document = self._retry_on_failure(_upload)

            if not document:
                raise RagFlowDocumentError("Document upload returned no result")

            logger.info(f"File uploaded successfully: {document.id}")

            return {
                'id': document.id,
                'name': filename,
                'status': 'uploaded'
            }

        except Exception as e:
            logger.error(f"Failed to upload file '{filename}' to dataset '{dataset_id}': {e}")
            raise RagFlowDocumentError(f"Failed to upload file: {e}")
    
    def delete_document(self, dataset_id: str, document_id: str) -> bool:
        """
        Delete a document from a RagFlow dataset.
        
        Args:
            dataset_id: Dataset ID
            document_id: Document ID to delete
            
        Returns:
            True if successful
            
        Raises:
            RagFlowDocumentError: If deletion fails
        """
        try:
            logger.info(f"Deleting document {document_id} from dataset {dataset_id}")
            
            # Get the dataset
            datasets = self.client.list_datasets(id=dataset_id)
            if not datasets:
                raise RagFlowDocumentError(f"Dataset {dataset_id} not found")
            
            dataset = datasets[0]
            
            def _delete():
                dataset.delete_documents(ids=[document_id])
                return True
            
            result = self._retry_on_failure(_delete)
            logger.info(f"Document deleted successfully: {document_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to delete document '{document_id}': {e}")
            raise RagFlowDocumentError(f"Failed to delete document: {e}")
    
    def parse_documents(self, dataset_id: str, document_ids: List[str]) -> bool:
        """
        Trigger parsing for documents in a dataset.
        
        Args:
            dataset_id: Dataset ID
            document_ids: List of document IDs to parse
            
        Returns:
            True if parsing was triggered successfully
            
        Raises:
            RagFlowDocumentError: If parsing trigger fails
        """
        try:
            logger.info(f"Triggering parsing for {len(document_ids)} documents in dataset {dataset_id}")
            
            # Get the dataset
            datasets = self.client.list_datasets(id=dataset_id)
            if not datasets:
                raise RagFlowDocumentError(f"Dataset {dataset_id} not found")
            
            dataset = datasets[0]
            
            def _parse():
                dataset.async_parse_documents(document_ids)
                return True
            
            result = self._retry_on_failure(_parse)
            logger.info(f"Document parsing triggered successfully for {len(document_ids)} documents")
            return result
            
        except Exception as e:
            logger.error(f"Failed to trigger document parsing: {e}")
            raise RagFlowDocumentError(f"Failed to trigger document parsing: {e}")
    
    def get_document_status(self, dataset_id: str, document_id: str) -> Optional[Dict]:
        """
        Get document parsing status.
        
        Args:
            dataset_id: Dataset ID
            document_id: Document ID
            
        Returns:
            Document status information or None if not found
        """
        try:
            # Get the dataset
            datasets = self.client.list_datasets(id=dataset_id)
            if not datasets:
                return None
            
            dataset = datasets[0]
            documents = dataset.list_documents(id=document_id)
            
            if documents:
                doc = documents[0]
                return {
                    'id': doc.id,
                    'name': getattr(doc, 'name', ''),
                    'status': getattr(doc, 'run', 'UNSTART')  # Use 'run' field for processing status
                }
            
            return None
        except Exception as e:
            logger.error(f"Failed to get document status: {e}")
            return None
    
    # Chat Management
    def create_chat_assistant(self, dataset_ids: List[str], name: str) -> Dict:
        """
        Create a chat assistant for datasets.
        
        Args:
            dataset_ids: List of dataset IDs to include
            name: Assistant name
            
        Returns:
            Dict containing chat assistant information
            
        Raises:
            RagFlowChatError: If chat creation fails
        """
        try:
            logger.info(f"Creating chat assistant '{name}' for {len(dataset_ids)} datasets")
            
            def _create_chat():
                return self.client.create_chat(name, dataset_ids=dataset_ids)
            
            chat = self._retry_on_failure(_create_chat)
            logger.info(f"Chat assistant created successfully: {chat.id}")
            
            return {
                'id': chat.id,
                'name': name,
                'dataset_ids': dataset_ids
            }
            
        except Exception as e:
            logger.error(f"Failed to create chat assistant '{name}': {e}")
            raise RagFlowChatError(f"Failed to create chat assistant: {e}")
    
    def delete_chat_assistant(self, chat_id: str) -> bool:
        """
        Delete a chat assistant.
        
        Args:
            chat_id: Chat assistant ID
            
        Returns:
            True if successful
            
        Raises:
            RagFlowChatError: If deletion fails
        """
        try:
            logger.info(f"Deleting chat assistant: {chat_id}")
            
            def _delete():
                self.client.delete_chats(ids=[chat_id])
                return True
            
            result = self._retry_on_failure(_delete)
            logger.info(f"Chat assistant deleted successfully: {chat_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to delete chat assistant '{chat_id}': {e}")
            raise RagFlowChatError(f"Failed to delete chat assistant: {e}")
    
    # Chat Completion
    def create_chat_completion(self, chat_id: str, messages: List[Dict], stream: bool = True) -> Any:
        """
        Create chat completion using RagFlow's OpenAI-compatible API.
        
        Args:
            chat_id: RagFlow chat assistant ID
            messages: List of messages in OpenAI format
            stream: Whether to stream the response
            
        Returns:
            Chat completion response (streaming or non-streaming)
            
        Raises:
            RagFlowChatError: If chat completion fails
        """
        try:
            from openai import OpenAI
            
            logger.info(f"Creating chat completion for chat {chat_id} with {len(messages)} messages")
            
            # Create OpenAI client pointing to RagFlow
            openai_client = OpenAI(
                api_key=self.api_key,
                base_url=f"{self.base_url}/api/v1/chats_openai/{chat_id}"
            )
            
            def _create_completion():
                return openai_client.chat.completions.create(
                    model="ragflow",  # Model name doesn't matter for RagFlow
                    messages=messages,
                    stream=stream,
                    extra_body={"reference": True}  # Include references in response
                )
            
            completion = self._retry_on_failure(_create_completion)
            logger.info(f"Chat completion created successfully for chat {chat_id}")
            
            return completion
            
        except Exception as e:
            logger.error(f"Failed to create chat completion for chat '{chat_id}': {e}")
            raise RagFlowChatError(f"Failed to create chat completion: {e}")
    
    # Agent Management
    def list_agents(self, page: int = 1, page_size: int = 30, orderby: str = "create_time", 
                   desc: bool = True, id: str = None, title: str = None) -> List[Dict]:
        """
        List RagFlow agents.
        
        Args:
            page: Page number (defaults to 1)
            page_size: Number of agents per page (defaults to 30)
            orderby: Sort by attribute ("create_time" or "update_time")
            desc: Sort in descending order
            id: Filter by agent ID
            title: Filter by agent title
            
        Returns:
            List of agent dictionaries
            
        Raises:
            RagFlowClientError: If listing fails
        """
        try:
            logger.info(f"Listing RagFlow agents (page={page}, size={page_size})")
            
            def _list():
                return self.client.list_agents(
                    page=page,
                    page_size=page_size,
                    orderby=orderby,
                    desc=desc,
                    id=id,
                    title=title
                )

            try:
                agents = _list()
            except Exception as e:
                # If "doesn't exist" is in the error, it means no agents exist - return empty list
                if "doesn't exist" in str(e).lower() or "agent doesn't exist" in str(e).lower():
                    logger.info("No agents exist yet - returning empty list")
                    return []
                # For other errors, still use retry logic
                agents = self._retry_on_failure(_list)
            
            # Convert to dict format for consistency
            agent_list = []
            for agent in agents:
                agent_list.append({
                    'id': getattr(agent, 'id', ''),
                    'title': getattr(agent, 'title', ''),
                    'description': getattr(agent, 'description', ''),
                    'create_time': getattr(agent, 'create_time', None),
                    'update_time': getattr(agent, 'update_time', None)
                })
            
            logger.info(f"Retrieved {len(agent_list)} agents")
            return agent_list
            
        except Exception as e:
            logger.error(f"Failed to list agents: {e}")
            raise RagFlowClientError(f"Failed to list agents: {e}")
    
    def create_agent(self, title: str, dsl: Dict, description: str = None) -> Dict:
        """
        Create a RagFlow agent.
        
        Args:
            title: Agent title
            dsl: Canvas DSL configuration
            description: Agent description
            
        Returns:
            Dict with creation result
            
        Raises:
            RagFlowClientError: If creation fails
        """
        try:
            logger.info(f"Creating RagFlow agent: {title}")
            
            def _create():
                return self.client.create_agent(
                    title=title,
                    dsl=dsl,
                    description=description
                )
            
            result = self._retry_on_failure(_create)
            logger.info(f"Agent created successfully: {title}")
            
            return {
                'success': True,
                'title': title,
                'description': description
            }
            
        except Exception as e:
            logger.error(f"Failed to create agent '{title}': {e}")
            raise RagFlowClientError(f"Failed to create agent: {e}")
    
    def delete_agent(self, agent_id: str) -> bool:
        """
        Delete a RagFlow agent.
        
        Args:
            agent_id: Agent ID to delete
            
        Returns:
            True if successful
            
        Raises:
            RagFlowClientError: If deletion fails
        """
        try:
            logger.info(f"Deleting RagFlow agent: {agent_id}")
            
            def _delete():
                self.client.delete_agent(agent_id)
                return True
            
            result = self._retry_on_failure(_delete)
            logger.info(f"Agent deleted successfully: {agent_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to delete agent '{agent_id}': {e}")
            raise RagFlowClientError(f"Failed to delete agent: {e}")
    
    # Session Management
    def create_session(self, agent_id: str, **kwargs) -> Dict:
        """
        Create a session with a RagFlow agent.
        
        Args:
            agent_id: Agent ID to create session with
            **kwargs: Additional session parameters
            
        Returns:
            Dict containing session information
            
        Raises:
            RagFlowSessionError: If session creation fails
        """
        try:
            logger.info(f"Creating session with agent: {agent_id}")
            
            # Get the agent first
            agents = self.client.list_agents(id=agent_id)
            if not agents:
                raise RagFlowSessionError(f"Agent {agent_id} not found")
            
            agent = agents[0]
            
            def _create_session():
                return agent.create_session(**kwargs)
            
            session = self._retry_on_failure(_create_session)
            logger.info(f"Session created successfully: {session.id}")
            
            return {
                'id': session.id,
                'agent_id': agent_id,
                'messages': getattr(session, 'messages', [])
            }
            
        except Exception as e:
            logger.error(f"Failed to create session with agent '{agent_id}': {e}")
            raise RagFlowSessionError(f"Failed to create session: {e}")
    
    def list_agent_sessions(self, agent_id: str, page: int = 1, page_size: int = 30,
                           orderby: str = "update_time", desc: bool = True, 
                           session_id: str = None) -> List[Dict]:
        """
        List sessions for a specific agent.
        
        Args:
            agent_id: Agent ID
            page: Page number (defaults to 1)
            page_size: Number of sessions per page (defaults to 30)
            orderby: Sort by attribute ("create_time" or "update_time")
            desc: Sort in descending order
            session_id: Filter by specific session ID
            
        Returns:
            List of session dictionaries
            
        Raises:
            RagFlowSessionError: If listing fails
        """
        try:
            logger.info(f"Listing sessions for agent {agent_id} (page={page}, size={page_size})")
            
            # Get the agent first
            agents = self.client.list_agents(id=agent_id)
            if not agents:
                raise RagFlowSessionError(f"Agent {agent_id} not found")
            
            agent = agents[0]
            
            def _list_sessions():
                return agent.list_sessions(
                    page=page,
                    page_size=page_size,
                    orderby=orderby,
                    desc=desc,
                    id=session_id
                )
            
            sessions = self._retry_on_failure(_list_sessions)
            
            # Convert to dict format for consistency
            session_list = []
            for session in sessions:
                session_list.append({
                    'id': getattr(session, 'id', ''),
                    'agent_id': agent_id,
                    'messages': getattr(session, 'messages', []),
                    'create_time': getattr(session, 'create_time', None),
                    'update_time': getattr(session, 'update_time', None)
                })
            
            logger.info(f"Retrieved {len(session_list)} sessions for agent {agent_id}")
            return session_list
            
        except Exception as e:
            logger.error(f"Failed to list sessions for agent '{agent_id}': {e}")
            raise RagFlowSessionError(f"Failed to list sessions: {e}")
    
    def delete_agent_sessions(self, agent_id: str, session_ids: List[str] = None) -> bool:
        """
        Delete sessions for a specific agent.
        
        Args:
            agent_id: Agent ID
            session_ids: List of session IDs to delete (if None, deletes all sessions)
            
        Returns:
            True if successful
            
        Raises:
            RagFlowSessionError: If deletion fails
        """
        try:
            session_count = len(session_ids) if session_ids else "all"
            logger.info(f"Deleting {session_count} sessions for agent: {agent_id}")
            
            # Get the agent first
            agents = self.client.list_agents(id=agent_id)
            if not agents:
                raise RagFlowSessionError(f"Agent {agent_id} not found")
            
            agent = agents[0]
            
            def _delete_sessions():
                agent.delete_sessions(ids=session_ids)
                return True
            
            result = self._retry_on_failure(_delete_sessions)
            logger.info(f"Sessions deleted successfully for agent {agent_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to delete sessions for agent '{agent_id}': {e}")
            raise RagFlowSessionError(f"Failed to delete sessions: {e}")
    
    def ask_agent_completion_raw(self, agent_id: str, question: str, session_id: str = None) -> Any:
        """
        Ask a question to an agent using the completions API with raw HTTP streaming.

        Args:
            agent_id: Agent ID
            question: Question to ask
            session_id: Optional session ID (if None, a new session is created)

        Returns:
            Raw streaming response

        Raises:
            RagFlowSessionError: If question fails
        """
        try:
            import requests

            logger.info(f"Asking question to agent {agent_id} (raw streaming) with session {session_id}")

            # Construct the correct endpoint URL per RagFlow API docs
            url = f"{self.base_url}/api/v1/agents/{agent_id}/completions"

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "question": question,
                "stream": True
            }

            # Include session_id if provided
            if session_id:
                payload["session_id"] = session_id

            logger.debug(f"Sending request to: {url} with payload: {payload}")

            # Make streaming request
            response = requests.post(url, json=payload, headers=headers, stream=True, timeout=120)
            response.raise_for_status()

            logger.info(f"Raw streaming request successful for agent {agent_id}")

            # Return the raw response iterator
            return response.iter_lines(decode_unicode=True)

        except Exception as e:
            logger.error(f"Failed to ask agent '{agent_id}' (raw): {e}")
            raise RagFlowSessionError(f"Failed to ask agent (raw): {e}")

    def ask_session(self, agent_id: str, session_id: str, question: str,
                   stream: bool = False) -> Any:
        """
        Ask a question in an agent session.
        
        Args:
            agent_id: Agent ID
            session_id: Session ID
            question: Question to ask
            stream: Whether to stream the response
            
        Returns:
            Message response or iterator for streaming
            
        Raises:
            RagFlowSessionError: If question fails
        """
        try:
            logger.info(f"Asking question in session {session_id} for agent {agent_id}")
            logger.debug(f"Question text: {question[:200]}")  # Log first 200 chars

            # Get the agent first
            agents = self.client.list_agents(id=agent_id)
            if not agents:
                raise RagFlowSessionError(f"Agent {agent_id} not found")

            agent = agents[0]
            logger.debug(f"Found agent: {agent}")

            # Get the session
            sessions = agent.list_sessions(id=session_id)
            if not sessions:
                raise RagFlowSessionError(f"Session {session_id} not found")

            session = sessions[0]
            logger.debug(f"Found session: {session_id}")

            def _ask():
                logger.debug(f"Calling session.ask() with question: {question[:100]}, stream: {stream}")
                try:
                    return session.ask(question=question, stream=stream)
                except KeyError as ke:
                    logger.error(f"KeyError in session.ask(): {ke}. This may indicate response format mismatch.")
                    # Try to catch and re-raise with more context
                    raise RagFlowSessionError(f"Session response format error: {ke}. The agent may not be configured correctly.")

            response = self._retry_on_failure(_ask)
            logger.info(f"Question asked successfully in session {session_id}, response type: {type(response)}")

            return response
            
        except Exception as e:
            logger.error(f"Failed to ask question in session '{session_id}': {e}")
            raise RagFlowSessionError(f"Failed to ask question: {e}")
    
    def get_session(self, agent_id: str, session_id: str) -> Optional[Dict]:
        """
        Get information about a specific session.
        
        Args:
            agent_id: Agent ID
            session_id: Session ID
            
        Returns:
            Session information or None if not found
        """
        try:
            logger.info(f"Getting session {session_id} for agent {agent_id}")
            
            # Get the agent first
            agents = self.client.list_agents(id=agent_id)
            if not agents:
                return None
            
            agent = agents[0]
            
            # Get the session
            sessions = agent.list_sessions(id=session_id)
            if not sessions:
                return None
            
            session = sessions[0]
            
            return {
                'id': getattr(session, 'id', ''),
                'agent_id': agent_id,
                'messages': getattr(session, 'messages', []),
                'create_time': getattr(session, 'create_time', None),
                'update_time': getattr(session, 'update_time', None)
            }
            
        except Exception as e:
            logger.error(f"Failed to get session '{session_id}': {e}")
            return None

    # Health Check
    def health_check(self) -> bool:
        """
        Check if RagFlow service is healthy.
        
        Returns:
            True if service is healthy
        """
        try:
            # Try to list datasets as a health check
            self.client.list_datasets()
            return True
        except Exception as e:
            logger.error(f"RagFlow health check failed: {e}")
            return False


# Singleton instance for global use
_ragflow_client = None


def get_ragflow_client() -> RagFlowClient:
    """
    Get or create singleton RagFlow client instance.
    
    Returns:
        RagFlowClient instance
    """
    global _ragflow_client
    if _ragflow_client is None:
        _ragflow_client = RagFlowClient()
    return _ragflow_client