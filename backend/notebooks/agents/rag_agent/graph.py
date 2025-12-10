"""
LangGraph workflow for RAG agent.

Defines the agent graph with nodes for reasoning, tool execution,
and conditional routing for multi-round retrieval.
"""

import logging
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from langgraph.prebuilt import ToolNode

from .states import RAGAgentState
from .prompts import format_system_prompt
from .config import RAGAgentConfig

logger = logging.getLogger(__name__)


def create_rag_agent(config: RAGAgentConfig):
    """
    Build and compile the RAG agent graph.

    The graph structure:
    ```
    START → agent_reasoning → [tool_calls?] → tools → agent_reasoning
                            ↓ [no_calls]
                            END
    ```

    Args:
        config: RAGAgentConfig with model and retrieval settings

    Returns:
        Compiled LangGraph that can be invoked or streamed

    Example:
        >>> from backend.notebooks.agents.rag_agent import create_rag_agent, RAGAgentConfig
        >>> config = RAGAgentConfig(
        ...     model_name="gpt-4.1-mini",
        ...     api_key="sk-...",
        ...     retrieval_service=retrieval_service,
        ...     dataset_ids=["kb1"]
        ... )
        >>> agent = create_rag_agent(config)
        >>> result = await agent.ainvoke({"messages": [HumanMessage("What is Python?")], ...})
    """
    logger.info(f"Creating RAG agent with model: {config.model_name}")

    # Initialize model
    model = init_chat_model(
        model=f"openai:{config.model_name}",
        api_key=config.api_key,
        temperature=config.temperature,
    )

    # Create tools with injected dependencies using closures
    # This properly binds config dependencies without breaking LangChain's tool system
    from functools import partial
    from langchain_core.tools import tool as langchain_tool
    from notebooks.agents.rag_agent.tools import (
        RetrieveKnowledgeInput,
        RewriteQueryInput,
        DecomposeQueryInput,
    )

    @langchain_tool(args_schema=RetrieveKnowledgeInput)
    def retrieve_knowledge_bound(query: str, top_k: int = 6) -> str:
        """
        Retrieve relevant information from the knowledge base.

        🔴 CRITICAL: This is your PRIMARY tool. Use it FIRST for any substantive question.
        The knowledge base contains the authoritative, up-to-date information the user wants.
        Do NOT rely on your training data - ALWAYS retrieve first.

        Args:
            query: Specific search query
            top_k: Number of passages to retrieve

        Returns:
            Formatted string with relevant passages and sources
        """
        from notebooks.agents.rag_agent.tools import _retrieve_knowledge_impl

        return _retrieve_knowledge_impl(
            query=query,
            top_k=top_k,
            retrieval_service=config.retrieval_service,
            dataset_ids=config.dataset_ids,
        )

    @langchain_tool(args_schema=RewriteQueryInput)
    def rewrite_query_bound(original_query: str, context: str = "") -> str:
        """
        Transform a user query into an optimized search query for the knowledge base.

        Use this when you have a vague, verbose, or poorly worded question that needs
        optimization before retrieval. Uses gpt-4.1-mini for fast, cost-effective query optimization.

        Args:
            original_query: The user's original question or query
            context: Optional conversation context to inform rewriting

        Returns:
            Optimized search query string with key terms extracted
        """
        from notebooks.agents.rag_agent.tools import _rewrite_query_impl

        return _rewrite_query_impl(
            original_query=original_query,
            context=context,
            api_key=config.api_key,
        )

    @langchain_tool(args_schema=DecomposeQueryInput)
    def decompose_query_bound(complex_query: str) -> list[str]:
        """
        Break down a complex question into simpler, focused sub-queries.

        Use this when a question has multiple parts or aspects that should be researched
        separately for comprehensive coverage. Uses gpt-4.1-mini for fast, cost-effective query decomposition.

        Args:
            complex_query: A multi-part or complex question

        Returns:
            List of simpler, focused sub-queries
        """
        from notebooks.agents.rag_agent.tools import _decompose_query_impl

        return _decompose_query_impl(
            complex_query=complex_query,
            api_key=config.api_key,
        )

    # Bind tools to model for function calling
    # retrieve_knowledge_bound: uses config (retrieval_service, dataset_ids)
    # rewrite_query_bound: uses hardcoded gpt-4.1-mini + config.api_key (fast and cheap for query optimization)
    # decompose_query_bound: uses hardcoded gpt-4.1-mini + config.api_key (fast and cheap for query optimization)
    model_with_tools = model.bind_tools([
        retrieve_knowledge_bound,
        rewrite_query_bound,
        decompose_query_bound,
    ])

    # Define agent reasoning node
    def agent_reasoning(state: RAGAgentState) -> Command[Literal["tools", END]]:
        """
        Agent reasoning node: decides whether to retrieve or finish.

        This node:
        1. Checks iteration limit
        2. Builds system message with context
        3. Invokes LLM with tool access
        4. Routes to tools node if tool calls present, otherwise finishes

        Args:
            state: Current agent state

        Returns:
            Command to either execute tools or end workflow
        """
        iteration_count = state.get("iteration_count", 0)
        messages = state["messages"]

        logger.debug(
            f"Agent reasoning: iteration {iteration_count}/{config.max_iterations}"
        )

        # Check iteration limit
        if iteration_count >= config.max_iterations:
            logger.info(
                f"Reached max iterations ({config.max_iterations}), forcing finish"
            )
            # Force finish - no more tool calls
            # The agent should use accumulated knowledge to answer
            return Command(goto=END, update={"should_finish": True})

        # Build system message with iteration context
        system_msg = SystemMessage(
            content=format_system_prompt(iteration_count, config.max_iterations)
        )

        # Invoke model with system message + conversation history
        try:
            response = model_with_tools.invoke([system_msg] + list(messages))
        except Exception as e:
            logger.exception(f"Error invoking model: {e}")
            # On error, force finish with error message
            from langchain_core.messages import AIMessage

            error_response = AIMessage(
                content=f"I encountered an error while processing your request: {str(e)}"
            )
            return Command(
                goto=END, update={"messages": [error_response], "should_finish": True}
            )

        # Check for tool calls
        has_tool_calls = hasattr(response, "tool_calls") and response.tool_calls

        if has_tool_calls:
            logger.info(
                f"Agent requested {len(response.tool_calls)} tool call(s) "
                f"in iteration {iteration_count}"
            )
            # Update state and route to tools node
            return Command(
                goto="tools",
                update={
                    "messages": [response],
                    "iteration_count": iteration_count + 1,
                },
            )
        else:
            # No tool calls - force at least one retrieval on first iteration
            from uuid import uuid4
            from langchain_core.messages import AIMessage, HumanMessage

            last_user_message = next(
                (m for m in reversed(messages) if isinstance(m, HumanMessage)), None
            )
            user_query = last_user_message.content if last_user_message else ""

            # Only force retrieval when we have a user query and configured datasets
            if iteration_count == 0 and user_query and config.dataset_ids:
                logger.info(
                    "Agent returned without tool calls on first iteration. "
                    "Forcing retrieve_knowledge tool invocation."
                )
                forced_tool_call_id = f"forced-retrieval-{uuid4().hex}"
                forced_tool_call = AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "id": forced_tool_call_id,
                            "name": "retrieve_knowledge_bound",
                            "args": {"query": user_query, "top_k": config.top_k},
                        }
                    ],
                )

                # Route to tools node with forced call
                return Command(
                    goto="tools",
                    update={
                        "messages": [forced_tool_call],
                        "iteration_count": iteration_count + 1,
                        "retrieval_history": state.get("retrieval_history", [])
                        + [user_query],
                    },
                )

            # No tool calls and no forced retrieval path available
            logger.info("Agent finished without tool calls")
            return Command(
                goto=END, update={"messages": [response], "should_finish": True}
            )

    # Define conditional routing after tool execution
    def should_continue(state: RAGAgentState) -> Literal["agent", END]:
        """
        Determine whether to continue after tool execution.

        After tools execute, we always return to the agent for synthesis
        unless we've hit the iteration limit.

        Args:
            state: Current agent state

        Returns:
            Next node name ("agent") or END signal
        """
        iteration_count = state.get("iteration_count", 0)

        if state.get("should_finish", False) or iteration_count >= config.max_iterations:
            logger.info("Finishing after tool execution")
            return END

        logger.debug("Continuing to agent after tool execution")
        return "agent"

    # Build the graph
    builder = StateGraph(RAGAgentState)

    # Add nodes
    builder.add_node("agent", agent_reasoning)
    builder.add_node("tools", ToolNode([
        retrieve_knowledge_bound,
        rewrite_query_bound,
        decompose_query_bound,
    ]))

    # Add edges
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("tools", should_continue)

    # Compile graph
    graph = builder.compile()

    logger.info("RAG agent graph compiled successfully")

    return graph
