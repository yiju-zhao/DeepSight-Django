"""
Research Worker for Deep Researcher Agent

This module implements an individual research worker that can perform 
iterative web searches and synthesis to answer specific research questions.
The worker is spawned by the supervisor for each research sub-task.
"""

import logging
from typing_extensions import Literal

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, filter_messages
from langchain.chat_models import init_chat_model

from .states import ResearcherState, ResearcherOutputState
from .tools import RESEARCH_TOOLS, TOOLS_BY_NAME
from .prompts import research_agent_prompt, compress_research_system_prompt, compress_research_human_message
from .config import get_today_str, get_model_config, get_compression_model_config


logger = logging.getLogger(__name__)


# ============================================================================
# LAZY MODEL INITIALIZATION
# ============================================================================

_model = None
_model_with_tools = None
_compress_model = None


def _get_model():
    """Lazy initialization of research model."""
    global _model
    if _model is None:
        config = get_model_config()
        _model = init_chat_model(
            model=f"openai:{config['model']}",
            api_key=config['api_key'],
            temperature=config.get('temperature', 0.7),
        )
    return _model


def _get_model_with_tools():
    """Lazy initialization of model with tools bound."""
    global _model_with_tools
    if _model_with_tools is None:
        _model_with_tools = _get_model().bind_tools(RESEARCH_TOOLS)
    return _model_with_tools


def _get_compress_model():
    """Lazy initialization of compression model."""
    global _compress_model
    if _compress_model is None:
        config = get_compression_model_config()
        _compress_model = init_chat_model(
            model=f"openai:{config['model']}",
            api_key=config['api_key'],
            max_tokens=config.get('max_tokens', 32000),
        )
    return _compress_model


# ============================================================================
# WORKER NODES
# ============================================================================

def llm_call(state: ResearcherState) -> dict:
    """
    Analyze current state and decide on next actions.

    The model analyzes the current conversation state and decides whether to:
    1. Call search tools to gather more information
    2. Provide a final answer based on gathered information

    Returns updated state with the model's response.
    """
    model = _get_model_with_tools()
    system_prompt = research_agent_prompt.format(date=get_today_str())
    
    response = model.invoke(
        [SystemMessage(content=system_prompt)] + state["researcher_messages"]
    )
    
    return {"researcher_messages": [response]}


def tool_node(state: ResearcherState) -> dict:
    """
    Execute all tool calls from the previous LLM response.

    Executes all tool calls from the previous LLM responses.
    Returns updated state with tool execution results.
    """
    tool_calls = state["researcher_messages"][-1].tool_calls

    observations = []
    for tool_call in tool_calls:
        try:
            tool = TOOLS_BY_NAME[tool_call["name"]]
            observation = tool.invoke(tool_call["args"])
            observations.append(observation)
        except KeyError:
            logger.error(f"Unknown tool: {tool_call['name']}")
            observations.append(f"Error: Unknown tool {tool_call['name']}")
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            observations.append(f"Error: {str(e)}")

    # Create tool message outputs
    tool_outputs = [
        ToolMessage(
            content=observation,
            name=tool_call["name"],
            tool_call_id=tool_call["id"]
        ) for observation, tool_call in zip(observations, tool_calls)
    ]

    return {"researcher_messages": tool_outputs}


def compress_research(state: ResearcherState) -> dict:
    """
    Compress research findings into a concise summary.

    Takes all the research messages and tool outputs and creates
    a compressed summary suitable for the supervisor's aggregation.
    """
    model = _get_compress_model()
    
    system_message = compress_research_system_prompt.format(date=get_today_str())
    research_topic = state.get("research_topic", "the given topic")
    human_message = compress_research_human_message.format(research_topic=research_topic)
    
    messages = (
        [SystemMessage(content=system_message)] + 
        state.get("researcher_messages", []) + 
        [HumanMessage(content=human_message)]
    )
    
    response = model.invoke(messages)

    # Extract raw notes from tool and AI messages
    raw_notes = [
        str(m.content) for m in filter_messages(
            state["researcher_messages"],
            include_types=["tool", "ai"]
        )
    ]

    return {
        "compressed_research": str(response.content),
        "raw_notes": ["\n".join(raw_notes)]
    }


# ============================================================================
# ROUTING LOGIC
# ============================================================================

def should_continue(state: ResearcherState) -> Literal["tool_node", "compress_research"]:
    """
    Determine whether to continue research or compress findings.

    Determines whether the agent should continue the research loop or 
    compress findings based on whether the LLM made tool calls.

    Returns:
        "tool_node": Continue to tool execution
        "compress_research": Stop and compress research
    """
    messages = state["researcher_messages"]
    last_message = messages[-1]

    # If the LLM makes a tool call, continue to tool execution
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tool_node"
    # Otherwise, compress the research
    return "compress_research"


# ============================================================================
# GRAPH CONSTRUCTION
# ============================================================================

def build_researcher_graph() -> StateGraph:
    """Build and return the research worker graph."""
    
    agent_builder = StateGraph(ResearcherState, output_schema=ResearcherOutputState)

    # Add nodes
    agent_builder.add_node("llm_call", llm_call)
    agent_builder.add_node("tool_node", tool_node)
    agent_builder.add_node("compress_research", compress_research)

    # Add edges
    agent_builder.add_edge(START, "llm_call")
    agent_builder.add_conditional_edges(
        "llm_call",
        should_continue,
        {
            "tool_node": "tool_node",
            "compress_research": "compress_research",
        },
    )
    agent_builder.add_edge("tool_node", "llm_call")
    agent_builder.add_edge("compress_research", END)

    return agent_builder


# Compiled researcher agent (lazy initialization)
_researcher_agent = None


def get_researcher_agent():
    """Get compiled researcher agent (lazy initialization)."""
    global _researcher_agent
    if _researcher_agent is None:
        _researcher_agent = build_researcher_graph().compile()
    return _researcher_agent
