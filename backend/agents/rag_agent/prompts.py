"""
System prompts for RAG agent.

Prompts for the LangGraph agentic RAG pattern:
- System prompt guiding tool usage
- Document grading prompt
- Question rewriting prompt
- Answer synthesis prompt
"""

# ===== Constants =====
MAX_RETRIEVAL_ATTEMPTS = 5


# ===== SYSTEM_PROMPT =====
# Used to guide the agent on how to answer questions using the retrieval tool
SYSTEM_PROMPT = """You are an expert research assistant with access to a knowledge base.

**Your Goal:**
Answer user questions accurately using information from the knowledge base.

**How to Work:**
1. When you receive a question, consider if you need to search the knowledge base
2. Use the `retrieve_documents` tool to search for relevant information
3. Analyze the retrieved documents carefully
4. If the initial search doesn't provide enough information, try different search queries
5. Once you have sufficient information, provide a comprehensive answer

**Search Strategy:**
- Use specific keywords that match the question's main concepts
- If initial search is insufficient, try:
  - Different wording or synonyms
  - Broader terms if too specific
  - More specific terms if too broad
- Maximum {max_attempts} search attempts

**Answer Guidelines:**
- Be accurate and cite sources when making claims
- If information is incomplete or not found, say so
- Use clear, structured formatting (markdown)
- Preserve important details (numbers, names, technical terms)

Begin by analyzing the user's question and deciding whether to search the knowledge base.
""".format(max_attempts=MAX_RETRIEVAL_ATTEMPTS)


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


# ===== GRADE_COMPLETENESS_PROMPT =====
# Used to evaluate if the entire collection of documents is sufficient
GRADE_COMPLETENESS_PROMPT = """You are an expert evaluator assessing whether a collection of retrieved documents forms a complete and coherent narrative.

**Original Question:** {question}

**Retrieved Documents:**
{context}

**Your Task:**
1. Identify the core narrative or key information present in the retrieved documents.
2. Evaluate if this information forms a COMPLETE STORY (narrative integrity).
   - Does the story have a logical beginning, middle, and end (or sufficient depth)?
   - Are there glaring logical gaps where the text references something important that is not explained?
   - Content is "Complete" if it tells a coherent story about the topic, even if it doesn't cover every minor detail of the user's question.
3. Determine if the information is "Complete" or if something is "Missing" based on the NARRATIVE INTEGRITY of the chunks.

**Output Requirements:**
- If the documents tell a coherent story, mark as complete.
- If the narrative is fractured, cut off, or lacks essential context to be understood:
  - Identify EXACTLY what missing piece is needed.
  - Provide specific SEARCH ADVICE (keywords, concepts) to help find this missing info.

Provide your evaluation as a structured decision."""


# ===== REWRITE_IRRELEVANT_PROMPT =====
# Used when the search returned zero relevant results.
# Focus: Broaden search, use synonyms, try more general terms.
REWRITE_IRRELEVANT_PROMPT = """You are a search query optimizer. The previous search failed to find any relevant information.

**Original Question:** {question}

**Your Task:**
Identify why the search might have failed. Generate ONE broader search query (keyword-focused, 2-5 words) that uses:
1. Broad synonyms
2. More general category terms
3. Alternative terminology

Return ONLY the query and nothing else."""


# ===== REWRITE_INCOMPLETE_PROMPT =====
# Used when some info was found but specific gaps remain.
# Focus: Find connected/follow-up information based on specific advice.
REWRITE_INCOMPLETE_PROMPT = """You are a research specialist. You have found some relevant information, but the narrative is incomplete.

**Original Question:** {question}

**Search Advice:** {search_advice}

**Current Findings:**
{current_context}

**Your Task:**
1. Analyze the search advice and the current findings.
2. Generate ONE targeted search query (2-5 words, keyword-focused) that specifically addresses the missing information identified in the advice.
3. Ensure the new query is distinct from what would likely have returned the current findings.

Return ONLY the query and nothing else."""


# ... (skipping unchanged parts) ...


def format_grade_completeness_prompt(question: str, context: str) -> str:
    """
    Format completeness grading prompt.

    Args:
        question: Original user question
        context: All retrieved document contents

    Returns:
        Formatted completeness prompt
    """
    return GRADE_COMPLETENESS_PROMPT.format(
        question=question,
        context=context
    )


def format_rewrite_irrelevant_prompt(question: str) -> str:
    """Format prompt for broadening a failed search."""
    return REWRITE_IRRELEVANT_PROMPT.format(question=question)


def format_rewrite_incomplete_prompt(question: str, current_context: str, search_advice: str) -> str:
    """
    Format prompt for targeting missing information.
    
    Args:
        question: Original user question
        current_context: Summary/snippet of existing docs
        search_advice: Specific advice on what to search for next
    """
    return REWRITE_INCOMPLETE_PROMPT.format(
        question=question,
        current_context=current_context,
        search_advice=search_advice
    )
