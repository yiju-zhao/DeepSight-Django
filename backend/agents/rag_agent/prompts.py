"""
System prompts for RAG agent.

Prompts for the LangGraph agentic RAG pattern:
- Document grading prompt
- Question rewriting prompt
- Answer synthesis prompt
"""

# ===== GRADE_DOCUMENTS_PROMPT =====
# Used to evaluate if retrieved documents are relevant to the question
# Based on Self-RAG: uses LENIENT grading to filter erroneous retrievals
GRADE_DOCUMENTS_PROMPT = """You are a grader assessing relevance of a retrieved document to a user question.

**IMPORTANT: This is NOT a stringent test.**
The goal is to FILTER OUT erroneous retrievals, not to demand exact matches.

Here is the retrieved document:
{context}

Here is the user question:
{question}

**Grading Rules (BE LENIENT):**
If the document contains ANY of the following, mark as relevant:
- Keywords related to the question (even partial matches)
- Semantic meaning related to the question  
- Background information that helps understand the topic
- IGNORE: typos, spelling variants (optimize/optimise), abbreviations (LLM/Large Language Model)
- IGNORE: different word forms (retrieve/retrieval/retrieved)

**Key Principle:** When in doubt, mark as RELEVANT. It's better to include marginally relevant docs than miss useful ones.

Give a binary score 'yes' or 'no' to indicate whether the document is relevant to the question."""


# ===== PLANNING_PROMPT =====
# Used to generate multiple diverse search queries
PLANNING_PROMPT = """You are a search query strategist. Your goal is to break down a user question into 3-5 diverse search queries to maximize retrieval coverage.

**Question:** {question}

{retry_context}

**Your Task:**
Identify different angles of the question (e.g., factual basics, conceptual relationships, specific technical details, real-world examples).
Generate 3-5 targeted search queries (keyword-focused, 3-7 words each).

Return a JSON list of strings."""


# ===== REORDER_PROMPT =====
# Used to semantically sort and group retrieved chunks using ID mapping
REORDER_PROMPT = """You are a master editor. Organize the following document chunks into a logical and coherent flow to answer the user question.

**User Question:** {question}

**Retrieved Chunks:**
{context}

**Your Task:**
1. Analyze the chunks and identify semantic relationships.
2. Create logical groups (sub-themes).
3. For each group:
    - Provide a brief, professional description of what this group covers.
    - List the IDs of the chunks that belong in this group, in their optimal reading order.
4. Chunks that are purely redundant or irrelevant should be omitted.

Return a structured list of groups."""


# ===== HALLUCINATION_GRADER_PROMPT =====
# Used to check if generation is grounded in retrieved documents
HALLUCINATION_GRADER_PROMPT = """You are a grader assessing whether an LLM generation is grounded in / supported by a set of retrieved facts.

Set of facts:
{documents}

LLM generation:
{generation}

Give a binary score 'yes' or 'no'. 'Yes' means the answer IS grounded in / supported by the set of facts."""


# ===== ANSWER_GRADER_PROMPT =====
# Used to check if the answer addresses the question
ANSWER_GRADER_PROMPT = """You are a grader assessing whether an answer addresses / resolves a question.

User question:
{question}

LLM generation:
{generation}

Give a binary score 'yes' or 'no'. 'Yes' means the answer resolves the question."""


# ===== SYNTHESIS_PROMPT =====
# Used to generate the final answer from retrieved context
SYNTHESIS_PROMPT = """You are an assistant for question-answering tasks.

Use the following pieces of retrieved context to answer the question. If you don't know the answer, just say that you don't know. Use three sentences maximum and keep the answer concise.

**Question:** {question}

**Context:** {context}

**Guidelines:**
- Be concise but comprehensive
- Cite specific documents when making claims (use [Document Name] format)
- Preserve important details (numbers, names, technical terms)
- Acknowledge if information is incomplete
- Use markdown formatting for readability

Now provide the final answer."""


def format_synthesis_prompt(question: str, context: str) -> str:
    """
    Format synthesis prompt with question and retrieved context.

    Args:
        question: Original user question
        context: Retrieved document content

    Returns:
        Formatted synthesis prompt
    """
    return SYNTHESIS_PROMPT.format(
        question=question,
        context=context
    )


def format_grade_documents_prompt(question: str, context: str) -> str:
    """
    Format document grading prompt.

    Args:
        question: User question
        context: Retrieved document content

    Returns:
        Formatted grading prompt
    """
    return GRADE_DOCUMENTS_PROMPT.format(
        question=question,
        context=context
    )


def format_planning_prompt(question: str, previous_queries: list[str] = None) -> str:
    """Format planning prompt with question and optional retry context."""
    retry_context = ""
    if previous_queries:
        retry_context = f"**Previous attempts failed:** {', '.join(previous_queries)}\nPlease refine the search strategy to find relevant information from DIFFERENT angles."
    
    return PLANNING_PROMPT.format(
        question=question,
        retry_context=retry_context
    )


def format_reorder_prompt(question: str, context: str) -> str:
    """Format reordering prompt."""
    return REORDER_PROMPT.format(
        question=question,
        context=context
    )
