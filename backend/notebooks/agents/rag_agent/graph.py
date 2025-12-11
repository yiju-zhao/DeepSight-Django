"""
LangGraph workflow for RAG agent using MCP (Model Context Protocol).

Implements agentic RAG pattern following LangGraph best practices with MCP integration:
- Uses MessagesState for standard message handling
- LLM decides when to use retrieval tool via bind_tools()
- ToolNode handles automatic tool execution from MCP server
- tools_condition routes based on tool calls
- Document grading filters irrelevant results
- Question rewriting improves failed searches

Flow:
START → generate_query_or_respond → [tools_condition] → retrieve → grade_documents
                                          ↓                            ↓
                                        END          [relevant?] → generate_answer → END
                                                          ↓
                                                   rewrite_question → generate_query_or_respond
"""

import logging
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import BaseModel, Field

from .config import RAGAgentConfig
from .prompts import (
    SYSTEM_PROMPT,
    format_synthesis_prompt,
    format_grade_documents_prompt,
    format_rewrite_question_prompt,
    MAX_RETRIEVAL_ATTEMPTS,
)
from .states import RAGAgentState
from .tools import create_mcp_retrieval_tools
from .utils import format_tool_content

logger = logging.getLogger(__name__)


class GradeDocuments(BaseModel):
    """Assess both relevance and completeness of retrieved documents."""

    relevance: str = Field(
        description="Relevance score: 'yes' if relevant, or 'no' if not relevant"
    )
    completeness: str = Field(
        description="Coverage score: 'complete' if enough to answer, or 'needs_more' if more retrieval is needed"
    )


async def create_rag_agent(config: RAGAgentConfig):
    """
    Build and compile the RAG agent graph using MCP server following LangGraph best practices.

    The graph structure:
    ```
    START → generate_query_or_respond → [tools_condition]
                 ↓                              ↓
               END (direct response)        retrieve (ToolNode)
                                               ↓
                                        grade_documents
                                         ↓         ↓
                              (relevant)          (not relevant)
                                 ↓                      ↓
                          generate_answer        rewrite_question
                                 ↓                      ↓
                               END         generate_query_or_respond
    ```

    Args:
        config: RAGAgentConfig with model and retrieval settings

    Returns:
        Compiled LangGraph that can be invoked or streamed

    Example:
        >>> from notebooks.agents.rag_agent import create_rag_agent, RAGAgentConfig
        >>> config = RAGAgentConfig(
        ...     model_name="gpt-4o-mini",
        ...     dataset_ids=["kb1"],
        ...     mcp_server_url="http://localhost:9382/mcp/"
        ... )
        >>> agent = await create_rag_agent(config)
        >>> result = await agent.ainvoke({
        ...     "messages": [HumanMessage(content="What is deep learning?")],
        ...     "question": "What is deep learning?",
        ...     "retrieved_chunks": [],
        ... })
    """
    logger.info(f"Creating RAG agent with MCP integration, model: {config.model_name}")
    logger.info(f"MCP server URL: {config.mcp_server_url}")

    # Create MCP retrieval tools
    retrieval_tools = await create_mcp_retrieval_tools(
        dataset_ids=config.dataset_ids,
        mcp_server_url=config.mcp_server_url,
        document_ids=getattr(config, "document_ids", None),
    )

    logger.info(f"Retrieved {len(retrieval_tools)} tools from MCP server")

    # Initialize chat models
    response_model = init_chat_model(
        model=f"openai:{config.model_name}",
        api_key=config.api_key,
        temperature=config.temperature,
    )

    grader_model = init_chat_model(
        model=f"openai:{config.model_name}",
        api_key=config.api_key,
        temperature=config.eval_temperature,
    )

    synthesis_model = init_chat_model(
        model=f"openai:{config.model_name}",
        api_key=config.api_key,
        temperature=config.synthesis_temperature,
    )

    # ===== Node Definitions =====

    def generate_query_or_respond(state: RAGAgentState) -> dict:
        """
        Call the model to generate a response based on the current state.

        Given the question, it will decide to:
        - Use the retrieval tool to search the knowledge base
        - Respond directly if no search is needed
        """
        logger.info("[generate_query_or_respond] Processing messages")

        # Prepare messages with system prompt
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]

        # Call LLM with tool binding
        response = response_model.bind_tools(retrieval_tools).invoke(messages)

        logger.debug(f"[generate_query_or_respond] Response type: {type(response)}")

        if hasattr(response, "tool_calls") and response.tool_calls:
            logger.info(
                f"[generate_query_or_respond] Tool calls: {len(response.tool_calls)}"
            )
        else:
            logger.info("[generate_query_or_respond] Direct response (no tool calls)")

        return {"messages": [response]}

    def grade_documents(
        state: RAGAgentState,
    ) -> Literal["generate_answer", "rewrite_question", "generate_query_or_respond"]:
        """
        Determine whether the retrieved documents are relevant and complete for the question.

        Returns the name of the next node to route to:
        - "generate_answer" if documents are relevant
        - "generate_query_or_respond" if relevant but more retrieval is needed
        - "rewrite_question" if documents are not relevant
        """
        logger.info("[grade_documents] Grading retrieved documents")

        question = state.get("question", "")
        messages = state["messages"]

        # Get the last tool message (contains retrieval results)
        context = ""
        for msg in reversed(messages):
            if hasattr(msg, "type") and msg.type == "tool":
                context = format_tool_content(msg.content).strip()
                break

        if not context or context == "No relevant documents found.":
            logger.info("[grade_documents] No documents to grade, rewriting question")
            return "rewrite_question"

        # Use structured output for grading
        prompt = format_grade_documents_prompt(question=question, context=context)

        try:
            grader_with_output = grader_model.with_structured_output(GradeDocuments)
            result = grader_with_output.invoke([{"role": "user", "content": prompt}])
            relevance = result.relevance.lower()
            completeness = result.completeness.lower()

            logger.info(
                f"[grade_documents] Relevance: {relevance}, Completeness: {completeness}"
            )

            # Avoid infinite loops: if we've already hit max attempts, proceed to answer
            tool_call_count = sum(
                1 for msg in messages if hasattr(msg, "type") and msg.type == "tool"
            )
            if tool_call_count >= MAX_RETRIEVAL_ATTEMPTS:
                logger.info(
                    "[grade_documents] Max retrieval attempts reached, proceeding to answer"
                )
                return "generate_answer"

            if relevance != "yes":
                return "rewrite_question"

            if completeness == "needs_more":
                return "generate_query_or_respond"

            return "generate_answer"

        except Exception as e:
            logger.warning(f"[grade_documents] Grading failed: {e}, defaulting to answer")
            return "generate_answer"

    def rewrite_question(state: RAGAgentState) -> dict:
        """
        Rewrite the original user question to improve retrieval results.

        Called when retrieved documents are not relevant.
        """
        logger.info("[rewrite_question] Rewriting question")

        question = state.get("question", "")

        # Check if we've already rewritten too many times
        rewrite_count = sum(
            1 for msg in state["messages"]
            if isinstance(msg, HumanMessage) and msg.content != question
        )

        if rewrite_count >= MAX_RETRIEVAL_ATTEMPTS:
            logger.info("[rewrite_question] Max rewrites reached, proceeding to answer")
            # Return empty to trigger direct answer
            return {"messages": []}

        prompt = format_rewrite_question_prompt(question)
        response = response_model.invoke([{"role": "user", "content": prompt}])

        logger.info(f"[rewrite_question] Rewritten: {response.content[:100]}...")

        # Add the rewritten question as a new human message
        return {"messages": [HumanMessage(content=response.content)]}

    def generate_answer(state: RAGAgentState) -> dict:
        """
        Generate the final answer using retrieved context.
        """
        logger.info("[generate_answer] Generating final answer")

        question = state.get("question", "")
        messages = state["messages"]

        # Extract context from tool messages
        context_parts = []
        for msg in messages:
            if hasattr(msg, "type") and msg.type == "tool":
                content = format_tool_content(msg.content).strip()
                if content and content != "No relevant documents found.":
                    context_parts.append(content)

        context = "\n\n".join(context_parts) if context_parts else "No context available."

        # Generate answer
        prompt = format_synthesis_prompt(question=question, context=context)
        response = synthesis_model.invoke([{"role": "user", "content": prompt}])

        logger.info(f"[generate_answer] Generated answer ({len(response.content)} chars)")

        return {"messages": [response]}

    # ===== Custom tools_condition wrapper =====

    def route_after_query(state: RAGAgentState) -> Literal["tools", "__end__"]:
        """
        Route based on whether the LLM wants to use tools.

        Uses LangGraph's tools_condition internally but allows customization.
        """
        result = tools_condition(state)
        logger.info(f"[route_after_query] Routing to: {result}")
        return result

    # ===== Build Graph =====

    workflow = StateGraph(RAGAgentState)

    # Add nodes
    workflow.add_node("generate_query_or_respond", generate_query_or_respond)
    workflow.add_node("retrieve", ToolNode(retrieval_tools))
    workflow.add_node("rewrite_question", rewrite_question)
    workflow.add_node("generate_answer", generate_answer)

    # Add edges
    workflow.add_edge(START, "generate_query_or_respond")

    # Route based on tool calls
    workflow.add_conditional_edges(
        "generate_query_or_respond",
        route_after_query,
        {
            "tools": "retrieve",
            "__end__": END,
        },
    )

    # Grade documents after retrieval
    workflow.add_conditional_edges(
        "retrieve",
        grade_documents,
        {
            "generate_answer": "generate_answer",
            "rewrite_question": "rewrite_question",
            "generate_query_or_respond": "generate_query_or_respond",
        },
    )

    # After rewrite, go back to generate query
    workflow.add_edge("rewrite_question", "generate_query_or_respond")

    # After answer, end
    workflow.add_edge("generate_answer", END)

    # Compile and return
    compiled_graph = workflow.compile()
    logger.info("RAG agent graph compiled successfully")

    return compiled_graph
