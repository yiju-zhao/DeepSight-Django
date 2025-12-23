"""
Research Supervisor for Deep Researcher Agent

This module implements a supervisor pattern where:
1. A supervisor agent coordinates research activities and delegates tasks
2. Multiple researcher agents work on specific sub-topics independently
3. Results are aggregated and returned as structured ResearchResult

Note: This module does NOT include report writing - that's in report_writer.
"""

import asyncio
import logging
from typing_extensions import Literal

from langchain.chat_models import init_chat_model
from langchain_core.messages import (
    HumanMessage,
    BaseMessage,
    SystemMessage,
    ToolMessage,
    filter_messages,
)
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from pydantic import BaseModel, Field

from .states import SupervisorState
from .worker import get_researcher_agent
from .tools import think_tool
from .prompts import lead_researcher_prompt
from .config import get_today_str, get_model_config, ResearchConfig


logger = logging.getLogger(__name__)


# ============================================================================
# SUPERVISOR TOOLS (Pydantic models for tool definitions)
# ============================================================================


@tool
class ConductResearch(BaseModel):
    """Tool for delegating a research task to a specialized sub-agent."""

    research_topic: str = Field(
        description="The topic to research. Should be a single topic, described in high detail (at least a paragraph).",
    )


@tool
class ResearchComplete(BaseModel):
    """Tool for indicating that the research process is complete."""

    pass


# ============================================================================
# LAZY MODEL INITIALIZATION
# ============================================================================

_supervisor_model = None
_supervisor_model_with_tools = None


def _get_supervisor_model():
    """Lazy initialization of supervisor model."""
    global _supervisor_model
    if _supervisor_model is None:
        config = get_model_config()
        _supervisor_model = init_chat_model(
            model=f"openai:{config['model']}",
            api_key=config["api_key"],
            temperature=config.get("temperature", 0.7),
        )
    return _supervisor_model


def _get_supervisor_model_with_tools():
    """Lazy initialization of supervisor model with tools."""
    global _supervisor_model_with_tools
    if _supervisor_model_with_tools is None:
        supervisor_tools = [ConductResearch, ResearchComplete, think_tool]
        _supervisor_model_with_tools = _get_supervisor_model().bind_tools(
            supervisor_tools
        )
    return _supervisor_model_with_tools


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def get_notes_from_tool_calls(messages: list[BaseMessage]) -> list[str]:
    """
    Extract research notes from ToolMessage objects in supervisor message history.

    This function retrieves the compressed research findings that sub-agents
    return as ToolMessage content.

    Args:
        messages: List of messages from supervisor's conversation history

    Returns:
        List of research note strings extracted from ToolMessage objects
    """
    return [
        tool_msg.content
        for tool_msg in filter_messages(messages, include_types="tool")
        if tool_msg.content  # Filter out empty messages
    ]


# ============================================================================
# SUPERVISOR NODES
# ============================================================================


async def supervisor(state: SupervisorState) -> Command[Literal["supervisor_tools"]]:
    """
    Coordinate research activities.

    Analyzes the research brief and current progress to decide:
    - What research topics need investigation
    - Whether to conduct parallel research
    - When research is complete

    Args:
        state: Current supervisor state with messages and research progress

    Returns:
        Command to proceed to supervisor_tools node with updated state
    """
    config = ResearchConfig.from_settings()
    supervisor_messages = state.get("supervisor_messages", [])
    model = _get_supervisor_model_with_tools()

    # Prepare system message with configuration
    system_message = lead_researcher_prompt.format(
        date=get_today_str(),
        max_concurrent_research_units=config.MAX_CONCURRENT_RESEARCHERS,
        max_researcher_iterations=config.MAX_RESEARCHER_ITERATIONS,
    )
    messages = [SystemMessage(content=system_message)] + supervisor_messages

    # Make decision about next research steps
    response = await model.ainvoke(messages)

    return Command(
        goto="supervisor_tools",
        update={
            "supervisor_messages": [response],
            "research_iterations": state.get("research_iterations", 0) + 1,
        },
    )


async def supervisor_tools(
    state: SupervisorState,
) -> Command[Literal["supervisor", "__end__"]]:
    """
    Execute supervisor decisions - either conduct research or end the process.

    Handles:
    - Executing think_tool calls for strategic reflection
    - Launching parallel research agents for different topics
    - Aggregating research results
    - Determining when research is complete

    Args:
        state: Current supervisor state with messages and iteration count

    Returns:
        Command to continue supervision or end process
    """
    config = ResearchConfig.from_settings()
    supervisor_messages = state.get("supervisor_messages", [])
    research_iterations = state.get("research_iterations", 0)
    most_recent_message = supervisor_messages[-1]

    # Initialize variables
    tool_messages = []
    all_raw_notes = []
    next_step = "supervisor"
    should_end = False

    # Check exit criteria
    exceeded_iterations = research_iterations >= config.MAX_RESEARCHER_ITERATIONS
    no_tool_calls = (
        not hasattr(most_recent_message, "tool_calls")
        or not most_recent_message.tool_calls
    )

    research_complete = False
    if hasattr(most_recent_message, "tool_calls") and most_recent_message.tool_calls:
        research_complete = any(
            tool_call["name"] == "ResearchComplete"
            for tool_call in most_recent_message.tool_calls
        )

    if exceeded_iterations or no_tool_calls or research_complete:
        should_end = True
        next_step = END
    else:
        try:
            # Separate tool calls by type
            think_tool_calls = [
                tc
                for tc in most_recent_message.tool_calls
                if tc["name"] == "think_tool"
            ]
            conduct_research_calls = [
                tc
                for tc in most_recent_message.tool_calls
                if tc["name"] == "ConductResearch"
            ]

            # Handle think_tool calls (synchronous)
            for tool_call in think_tool_calls:
                observation = think_tool.invoke(tool_call["args"])
                tool_messages.append(
                    ToolMessage(
                        content=observation,
                        name=tool_call["name"],
                        tool_call_id=tool_call["id"],
                    )
                )

            # Handle ConductResearch calls (parallel async)
            if conduct_research_calls:
                researcher = get_researcher_agent()

                # Launch parallel research agents
                coros = [
                    researcher.ainvoke(
                        {
                            "researcher_messages": [
                                HumanMessage(content=tc["args"]["research_topic"])
                            ],
                            "research_topic": tc["args"]["research_topic"],
                        }
                    )
                    for tc in conduct_research_calls
                ]

                # Wait for all research to complete
                tool_results = await asyncio.gather(*coros, return_exceptions=True)

                # Process results
                for result, tool_call in zip(tool_results, conduct_research_calls):
                    if isinstance(result, Exception):
                        logger.error(f"Research failed: {result}")
                        content = f"Error during research: {str(result)}"
                        raw_notes = []
                    else:
                        content = result.get(
                            "compressed_research", "Error synthesizing research"
                        )
                        raw_notes = result.get("raw_notes", [])

                    tool_messages.append(
                        ToolMessage(
                            content=content,
                            name=tool_call["name"],
                            tool_call_id=tool_call["id"],
                        )
                    )
                    all_raw_notes.extend(raw_notes)

        except Exception as e:
            logger.error(f"Supervisor tools error: {e}")
            should_end = True
            next_step = END

    # Return with appropriate state updates
    if should_end:
        return Command(
            goto=next_step,
            update={
                "notes": get_notes_from_tool_calls(supervisor_messages),
                "research_brief": state.get("research_brief", ""),
            },
        )
    else:
        return Command(
            goto=next_step,
            update={"supervisor_messages": tool_messages, "raw_notes": all_raw_notes},
        )


# ============================================================================
# GRAPH CONSTRUCTION
# ============================================================================


def build_supervisor_graph() -> StateGraph:
    """Build and return the supervisor graph."""
    supervisor_builder = StateGraph(SupervisorState)
    supervisor_builder.add_node("supervisor", supervisor)
    supervisor_builder.add_node("supervisor_tools", supervisor_tools)
    supervisor_builder.add_edge(START, "supervisor")
    return supervisor_builder


# Compiled supervisor agent (lazy initialization)
_supervisor_agent = None


def get_supervisor_agent():
    """Get compiled supervisor agent (lazy initialization)."""
    global _supervisor_agent
    if _supervisor_agent is None:
        _supervisor_agent = build_supervisor_graph().compile()
    return _supervisor_agent
