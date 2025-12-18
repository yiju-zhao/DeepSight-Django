import logging
from typing import Literal, cast

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
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


class DeepSightRAGAgent:
    """
    RAG Agent implementation using a class-based approach following the open-research-ANA scaffold.
    
    This allows the graph to be compiled once but remain dynamic via RunnableConfig.
    """

    def __init__(self, config: RAGAgentConfig):
        self.config = config
        self._initialize_models()
        self._build_workflow()

    def _initialize_models(self):
        """Initialize chat models."""
        self.response_model = init_chat_model(
            model=f"openai:{self.config.model_name}",
            api_key=self.config.api_key,
            temperature=self.config.temperature,
        )

        self.grader_model = init_chat_model(
            model=f"openai:{self.config.model_name}",
            api_key=self.config.api_key,
            temperature=self.config.eval_temperature,
        )

        self.synthesis_model = init_chat_model(
            model=f"openai:{self.config.model_name}",
            api_key=self.config.api_key,
            temperature=self.config.synthesis_temperature,
        )

    def _build_workflow(self):
        """Build the workflow graph with nodes and edges."""
        workflow = StateGraph(RAGAgentState)

        # Add nodes
        workflow.add_node("generate_query_or_respond", self.generate_query_or_respond)
        workflow.add_node("retrieve", self.tool_node)
        workflow.add_node("rewrite_question", self.rewrite_question)
        workflow.add_node("generate_answer", self.generate_answer)
        workflow.add_node("prepare_followup_query", self.prepare_followup_query)

        # Add edges
        workflow.add_edge(START, "generate_query_or_respond")

        # Route based on tool calls
        workflow.add_conditional_edges(
            "generate_query_or_respond",
            self.route_after_query,
            {
                "tools": "retrieve",
                "__end__": END,
            },
        )

        # Grade documents after retrieval
        workflow.add_conditional_edges(
            "retrieve",
            self.grade_documents,
            {
                "generate_answer": "generate_answer",
                "rewrite_question": "rewrite_question",
                "generate_query_or_respond": "generate_query_or_respond",
                "prepare_followup_query": "prepare_followup_query",
            },
        )

        # After rewrite, go back to generate query
        workflow.add_edge("rewrite_question", "generate_query_or_respond")
        # After preparing follow-up, go back to generate query
        workflow.add_edge("prepare_followup_query", "generate_query_or_respond")

        # After answer, end
        workflow.add_edge("generate_answer", END)

        # Add checkpointer for conversation state management
        memory = MemorySaver()
        self.graph = workflow.compile(checkpointer=memory)
        logger.info("RAG agent graph compiled successfully with MemorySaver checkpointer")

    async def generate_query_or_respond(self, state: RAGAgentState, config: RunnableConfig) -> dict:
        """Call the model to generate a response or determine search queries."""
        logger.info("[generate_query_or_respond] Processing messages")

        # In a real dynamic scenario, we might want to refresh tools here or use a tool registry
        # For now, we reuse the tools from initialization if they were pre-created
        # But wait, we need to handle the case where dataset_ids might change
        
        # For DeepSight, we currently create tools per notebook.
        # However, to compile the graph once, we either need a ToolRegistry or 
        # to ensure the ToolNode can handle dynamic tools.
        
        # Actually, let's keep the tools dynamic by creating them if they don't exist in config or state
        # Better: we can pass them in config['configurable']
        
        tools = config.get("configurable", {}).get("retrieval_tools", [])
        if not tools:
            # Fallback if tools aren't passed (shouldn't happen in our new server.py)
            tools = await create_mcp_retrieval_tools(
                dataset_ids=self.config.dataset_ids,
                mcp_server_url=self.config.mcp_server_url
            )

        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        model_with_tools = self.response_model.bind_tools(tools)
        response = await model_with_tools.ainvoke(messages, config)

        return {"messages": [response]}

    async def tool_node(self, state: RAGAgentState, config: RunnableConfig):
        """Custom tool node that delegates to LangGraph's ToolNode but with dynamic tools."""
        tools = config.get("configurable", {}).get("retrieval_tools", [])
        node = ToolNode(tools)
        return await node.ainvoke(state, config)

    async def grade_documents(self, state: RAGAgentState, config: RunnableConfig) -> Literal["generate_answer", "rewrite_question", "generate_query_or_respond", "prepare_followup_query"]:
        """Grade the documents for relevance and completeness."""
        logger.info("[grade_documents] Grading retrieved documents")

        question = state.get("question", "")
        messages = state["messages"]

        latest_tool_context = ""
        for msg in reversed(messages):
            if isinstance(msg, ToolMessage):
                latest_tool_context = format_tool_content(msg.content).strip()
                break

        if not latest_tool_context or latest_tool_context == "No relevant documents found.":
            return "rewrite_question"

        prompt = format_grade_documents_prompt(question=question, context=latest_tool_context)

        try:
            grader_with_output = self.grader_model.with_structured_output(GradeDocuments)
            result = await grader_with_output.ainvoke([{"role": "user", "content": prompt}], config)
            relevance = result.relevance.lower()
            completeness = result.completeness.lower()

            # Logic for max attempts and routing
            tool_call_count = sum(1 for msg in messages if isinstance(msg, ToolMessage))
            if tool_call_count >= MAX_RETRIEVAL_ATTEMPTS:
                return "generate_answer"

            if relevance != "yes":
                return "rewrite_question"

            retrieved_chunks = state.get("retrieved_chunks", []) or []
            if latest_tool_context not in [c.get("content") for c in retrieved_chunks]:
                retrieved_chunks = retrieved_chunks + [{"content": latest_tool_context}]
            
            # We must return the update
            state["retrieved_chunks"] = retrieved_chunks

            if completeness == "needs_more":
                return "prepare_followup_query"

            return "generate_answer"

        except Exception as e:
            logger.warning(f"[grade_documents] Grading failed: {e}, defaulting to answer")
            return "generate_answer"

    async def rewrite_question(self, state: RAGAgentState, config: RunnableConfig) -> dict:
        """Rewrite the question for better retrieval."""
        logger.info("[rewrite_question] Rewriting question")
        question = state.get("question", "")
        
        prompt = format_rewrite_question_prompt(question)
        response = await self.response_model.ainvoke([{"role": "user", "content": prompt}], config)
        
        return {"messages": [HumanMessage(content=response.content)]}

    async def generate_answer(self, state: RAGAgentState, config: RunnableConfig) -> dict:
        """Generate the final synthesis."""
        logger.info("[generate_answer] Generating final answer")
        question = state.get("question", "")
        
        retrieved_chunks = state.get("retrieved_chunks", []) or []
        context_parts = [c.get("content", "") for c in retrieved_chunks if c.get("content")]
        context = "\n\n".join(context_parts) if context_parts else "No context available."

        prompt = format_synthesis_prompt(question=question, context=context)
        response = await self.synthesis_model.ainvoke([{"role": "user", "content": prompt}], config)

        return {"messages": [response]}

    def route_after_query(self, state: RAGAgentState) -> Literal["tools", "__end__"]:
        """Determine next node based on tool calls."""
        return tools_condition(state)

    async def prepare_followup_query(self, state: RAGAgentState, config: RunnableConfig) -> dict:
        """Prepare a follow-up hint for the next retrieval round."""
        logger.info("[prepare_followup_query] Adding follow-up hint")
        latest_context = ""
        retrieved_chunks = state.get("retrieved_chunks", []) or []
        if retrieved_chunks:
            latest_context = retrieved_chunks[-1].get("content", "") or ""

        tail_snippet = latest_context[-500:] if latest_context else ""
        hint = (
            "Continue searching for additional relevant chunks. "
            "Focus on content that follows this recent snippet: "
            f"{tail_snippet}"
        )

# Define the graph export for direct usage
# We initialize it with a base configuration as nodes handle dynamic overrides
# via config['configurable'] at runtime.
graph = DeepSightRAGAgent(RAGAgentConfig(
    model_name="gpt-4o-mini",
    dataset_ids=[],
    mcp_server_url="http://localhost:9382/mcp/"
)).graph


