"""
LangGraph workflow for ReAct RAG agent.

Implements ReAct (Reasoning + Acting) pattern with iterative retrieval:
- reasoning_node: Agent thinks and generates queries
- retrieval_node: Execute retrieval based on queries
- evaluation_node: LLM evaluates and extracts relevant info
- synthesize_node: Generate final answer from all reasoning steps

Flow: reasoning → retrieval → evaluation → (continue OR synthesize)
"""

import logging
from typing import Literal

from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, END

from .states import RAGReActState
from .prompts import (
    REASON_PROMPT,
    RELEVANT_EXTRACTION_PROMPT,
    format_synthesis_prompt,
    BEGIN_SEARCH_QUERY,
    END_SEARCH_QUERY,
    BEGIN_SEARCH_RESULT,
    END_SEARCH_RESULT,
    MAX_ITERATIONS,
)
from .config import RAGAgentConfig
from .utils import (
    extract_between,
    truncate_reasoning_history,
    format_chunks,
    remove_query_tags,
)

logger = logging.getLogger(__name__)


def create_rag_agent(config: RAGAgentConfig):
    """
    Build and compile the ReAct RAG agent graph.

    The graph structure:
    ```
    START → reasoning → [has_queries?] → retrieval → evaluation
                                              ↓
                      [no_queries] → synthesize → END
                                              ↑
                      [continue?] ←───────────┘
                            ↓ [finish]
                       synthesize → END
    ```

    Args:
        config: RAGAgentConfig with model and retrieval settings

    Returns:
        Compiled LangGraph that can be invoked or streamed

    Example:
        >>> from backend.notebooks.agents.rag_agent import create_rag_agent, RAGAgentConfig
        >>> config = RAGAgentConfig(
        ...     model_name="gpt-4o-mini",
        ...     retrieval_service=retrieval_service,
        ...     dataset_ids=["kb1"]
        ... )
        >>> agent = create_rag_agent(config)
        >>> result = await agent.ainvoke({
        ...     "question": "What is deep learning?",
        ...     "message_history": [],
        ...     ...
        ... })
    """
    logger.info(f"Creating ReAct RAG agent with model: {config.model_name}")

    # Initialize chat model for reasoning and synthesis
    chat_model = init_chat_model(
        model=f"openai:{config.model_name}",
        api_key=config.api_key,
        temperature=config.temperature,
    )

    # Evaluation model (lower temperature for precision)
    eval_model = init_chat_model(
        model=f"openai:{config.model_name}",
        api_key=config.api_key,
        temperature=config.eval_temperature,
    )

    # Synthesis model (balanced temperature)
    synthesis_model = init_chat_model(
        model=f"openai:{config.model_name}",
        api_key=config.api_key,
        temperature=config.synthesis_temperature,
    )

    # ===== Node Definitions =====

    async def reasoning_node(state: RAGReActState) -> RAGReActState:
        """
        Agent self-reasoning node: thinks and generates queries.

        Uses REASON_PROMPT to guide the agent through step-by-step reasoning.
        Agent outputs queries wrapped in special markers.
        """
        logger.info(f"[reasoning_node] Iteration {state['iteration']}")

        msg_history = state["message_history"].copy()

        # If not first iteration, prompt to continue reasoning
        if state["iteration"] > 0:
            if not msg_history or msg_history[-1]["role"] != "user":
                msg_history.append({
                    "role": "user",
                    "content": "Continue reasoning with the new information.\n"
                })
            else:
                msg_history[-1]["content"] += "\n\nContinue reasoning with the new information.\n"

        # Call LLM with REASON_PROMPT
        messages = [{"role": "system", "content": REASON_PROMPT}] + msg_history

        reasoning_output = ""
        async for chunk in chat_model.astream(messages):
            if hasattr(chunk, "content"):
                reasoning_output += chunk.content

        logger.debug(f"[reasoning_node] Output: {reasoning_output[:200]}...")

        # Extract queries from reasoning
        queries = extract_between(reasoning_output, BEGIN_SEARCH_QUERY, END_SEARCH_QUERY)
        logger.info(f"[reasoning_node] Extracted {len(queries)} queries: {queries}")

        # Update state
        return {
            **state,
            "current_reasoning": reasoning_output,
            "current_queries": queries,
            "reasoning_steps": state["reasoning_steps"] + [reasoning_output],
            "iteration": state["iteration"] + 1,
        }

    async def retrieval_node(state: RAGReActState) -> RAGReActState:
        """
        Execute retrieval for all current queries.

        Performs deduplication and uses config thresholds.
        """
        logger.info(f"[retrieval_node] Processing {len(state['current_queries'])} queries")

        queries = state["current_queries"]
        executed_queries = state["executed_queries"]
        all_retrieved = []

        for query in queries:
            # Skip if already executed
            if query in executed_queries:
                logger.info(f"[retrieval_node] Query already executed: {query}")
                msg = f"\n{BEGIN_SEARCH_RESULT}\nYou have searched this query. Please refer to previous results.\n{END_SEARCH_RESULT}\n"
                state["message_history"].append({"role": "user", "content": msg})
                state["reasoning_steps"].append(msg)
                continue

            logger.info(f"[retrieval_node] Executing query: {query}")

            # Execute retrieval
            try:
                # Call retrieval service (returns RetrievalResult object)
                result = config.retrieval_service.retrieve_chunks(
                    question=query,
                    dataset_ids=config.dataset_ids,
                    similarity_threshold=config.similarity_threshold,
                    top_k=config.top_k,
                )

                # Extract chunks from result
                chunks = result.chunks if hasattr(result, 'chunks') else []
                logger.info(f"[retrieval_node] Retrieved {len(chunks)} chunks for query: {query}")

                # Convert chunks to dict format for state
                for chunk in chunks:
                    chunk_dict = {
                        "chunk_id": getattr(chunk, 'id', ''),
                        "doc_name": getattr(chunk, 'document_name', 'Unknown'),
                        "content": getattr(chunk, 'content', ''),
                        "similarity": getattr(chunk, 'similarity', 0.0),
                    }
                    all_retrieved.append(chunk_dict)

                executed_queries.append(query)

            except Exception as e:
                logger.error(f"[retrieval_node] Retrieval error: {e}")
                # Add error message to context
                error_msg = f"\n{BEGIN_SEARCH_RESULT}\nRetrieval failed: {str(e)}\n{END_SEARCH_RESULT}\n"
                state["message_history"].append({"role": "user", "content": error_msg})
                state["reasoning_steps"].append(error_msg)

        # Update state
        return {
            **state,
            "current_retrieved": all_retrieved,
            "retrieved_chunks": state["retrieved_chunks"] + all_retrieved,
            "executed_queries": executed_queries,
        }

    async def evaluation_node(state: RAGReActState) -> RAGReActState:
        """
        Evaluate retrieval results and extract relevant information.

        Uses RELEVANT_EXTRACTION_PROMPT to filter and summarize.
        """
        logger.info(f"[evaluation_node] Evaluating {len(state['current_retrieved'])} chunks")

        current_query = state["current_queries"][0] if state["current_queries"] else "unknown"
        retrieved = state["current_retrieved"]

        # Format chunks for LLM
        document_text = format_chunks(retrieved, max_content_length=500)

        # Truncate reasoning history
        truncated_reasoning = truncate_reasoning_history(
            state["reasoning_steps"],
            keep_first_n=config.keep_first_n_steps,
            keep_last_n=config.keep_last_n_steps,
        )

        # Build evaluation prompt
        eval_prompt = RELEVANT_EXTRACTION_PROMPT.format(
            prev_reasoning=truncated_reasoning,
            search_query=current_query,
            document=document_text,
        )

        # Call LLM for evaluation
        messages = [{"role": "user", "content": eval_prompt}]

        evaluation_output = ""
        async for chunk in eval_model.astream(messages):
            if hasattr(chunk, "content"):
                evaluation_output += chunk.content

        logger.debug(f"[evaluation_node] Evaluation: {evaluation_output[:200]}...")

        # Wrap in result tags
        result_text = f"\n{BEGIN_SEARCH_RESULT}{evaluation_output}{END_SEARCH_RESULT}\n"

        # Add to message history
        state["message_history"].append({"role": "user", "content": result_text})
        state["reasoning_steps"].append(result_text)

        return state

    async def synthesize_node(state: RAGReActState) -> RAGReActState:
        """
        Synthesize final answer from all reasoning steps.
        """
        logger.info("[synthesize_node] Generating final answer")

        # Join all reasoning steps (remove query/result tags for cleaner output)
        all_reasoning = "\n\n".join(
            remove_query_tags(step) for step in state["reasoning_steps"]
        )

        # Build synthesis prompt
        synthesis_prompt = format_synthesis_prompt(
            question=state["question"],
            reasoning_process=all_reasoning,
        )

        # Call LLM for synthesis
        messages = [{"role": "user", "content": synthesis_prompt}]

        final_answer = ""
        async for chunk in synthesis_model.astream(messages):
            if hasattr(chunk, "content"):
                final_answer += chunk.content

        logger.info(f"[synthesize_node] Generated answer ({len(final_answer)} chars)")

        return {
            **state,
            "final_answer": final_answer,
        }

    # ===== Conditional Edge Functions =====

    def should_retrieve(state: RAGReActState) -> Literal["retrieve", "synthesize"]:
        """
        Decide whether to retrieve or synthesize.

        Logic:
        - If iteration 1 and no queries: force retrieval with original question
        - If has queries: retrieve
        - Otherwise: synthesize
        """
        queries = state.get("current_queries", [])
        iteration = state.get("iteration", 0)

        # First iteration without queries: force retrieval
        if iteration == 1 and not queries:
            logger.info("[should_retrieve] First iteration, forcing retrieval with original question")
            state["current_queries"] = [state["question"]]
            return "retrieve"

        # Has queries: retrieve
        if queries:
            logger.info(f"[should_retrieve] Has {len(queries)} queries, routing to retrieval")
            return "retrieve"

        # No queries: synthesize
        logger.info("[should_retrieve] No queries, routing to synthesis")
        return "synthesize"

    def should_continue_reasoning(state: RAGReActState) -> Literal["continue", "finish"]:
        """
        Decide whether to continue reasoning or finish.

        Logic:
        - If max iterations reached: finish
        - If evaluation says "sufficient information": finish
        - Otherwise: continue
        """
        iteration = state.get("iteration", 0)

        # Max iterations reached
        if iteration >= config.max_iterations:
            logger.info(f"[should_continue_reasoning] Max iterations ({config.max_iterations}) reached, finishing")
            return "finish"

        # Check last reasoning step for completion signals
        if state["reasoning_steps"]:
            last_step = state["reasoning_steps"][-1].lower()

            if any(phrase in last_step for phrase in [
                "sufficient information",
                "ready to answer",
                "can now answer",
                "have all the information",
            ]):
                logger.info("[should_continue_reasoning] Agent indicates completion, finishing")
                return "finish"

        logger.info("[should_continue_reasoning] Continuing reasoning")
        return "continue"

    # ===== Build Graph =====

    graph = StateGraph(RAGReActState)

    # Add nodes
    graph.add_node("reasoning", reasoning_node)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("evaluation", evaluation_node)
    graph.add_node("synthesize", synthesize_node)

    # Set entry point
    graph.set_entry_point("reasoning")

    # Add edges
    graph.add_conditional_edges(
        "reasoning",
        should_retrieve,
        {
            "retrieve": "retrieval",
            "synthesize": "synthesize",
        }
    )

    graph.add_edge("retrieval", "evaluation")

    graph.add_conditional_edges(
        "evaluation",
        should_continue_reasoning,
        {
            "continue": "reasoning",
            "finish": "synthesize",
        }
    )

    graph.add_edge("synthesize", END)

    # Compile and return
    compiled_graph = graph.compile()
    logger.info("ReAct RAG agent graph compiled successfully")

    return compiled_graph
