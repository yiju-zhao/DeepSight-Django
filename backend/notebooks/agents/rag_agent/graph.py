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
from .tools import retrieve_knowledge
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
        ...     model_name="gpt-4o-mini",
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

    # Bind tool with injected dependencies
    # This allows the tool to access retrieval_service and dataset_ids
    # without passing them as parameters each time
    bound_tool = retrieve_knowledge.bind(
        retrieval_service=config.retrieval_service, dataset_ids=config.dataset_ids
    )

    # Bind tools to model for function calling
    model_with_tools = model.bind_tools([bound_tool])

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
            # No tool calls - agent has decided to finish
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
    builder.add_node("tools", ToolNode([bound_tool]))

    # Add edges
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("tools", should_continue)

    # Compile graph
    graph = builder.compile()

    logger.info("RAG agent graph compiled successfully")

    return graph
