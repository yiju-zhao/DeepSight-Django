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


# ===== GRADE_COMPLETENESS_PROMPT =====
# Used to evaluate if the entire collection of documents is sufficient
GRADE_COMPLETENESS_PROMPT = """You are an expert evaluator assessing whether a collection of retrieved documents forms a complete and coherent narrative.

**Original Question:** {question}

**Existing Documents:**
{existing_context}

**Newly Retrieved Documents:**
{new_context}

**Your Task:**
1. **FIRST**: If there are newly retrieved documents, evaluate if they CONTRIBUTE to completing the story:
   - Do they add NEW information that advances the narrative?
   - Do they fill gaps in the existing documents?
   - Do they provide continuation of truncated content?
   - OR: Are they redundant/irrelevant to completing the story?

2. **SECOND**: Assuming we KEEP the contributing new documents, evaluate if the COMBINED collection forms a COMPLETE STORY:
   - Does it have logical coherence (beginning, middle, end or sufficient depth)?
   - Are there glaring gaps where the text references something not explained?

3. **CRITICAL: Check for TRUNCATION indicators**:
   - Does any chunk end mid-sentence or mid-thought?
   - Are there phrases like "continued...", "...", or cut-off statements?

**Output Requirements:**
- `new_docs_contribute`: (bool) Do new docs add value? (Always True if no new docs)
- `is_complete`: (bool) Is the overall story complete?
- If incomplete, determine TYPE:
  - **MISSING_TOPIC**: Need different concept/topic
  - **TRUNCATED_CONTINUATION**: Content is cut off
- In `search_advice`, start with `[MISSING_TOPIC]` or `[TRUNCATED]` prefix.
- For TRUNCATED: Extract unique phrase from END of truncated chunk.

Provide structured evaluation."""


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
# Used when some info was found but specific gaps remain (MISSING_TOPIC case).
# Focus: Find connected/follow-up information based on specific advice.
REWRITE_INCOMPLETE_PROMPT = """You are a research specialist. You have found some relevant information, but the narrative is incomplete because a related TOPIC is missing.

**Original Question:** {question}

**Search Advice:** {search_advice}

**Current Findings:**
{current_context}

**Your Task:**
1. Analyze the search advice and the current findings.
2. Generate ONE targeted search query (2-5 words, keyword-focused) that specifically addresses the missing TOPIC identified in the advice.
3. Ensure the new query is distinct from what would likely have returned the current findings.

Return ONLY the query and nothing else."""


# ===== REWRITE_CONTINUATION_PROMPT =====
# Used when content is TRUNCATED and we need to find the next chunk.
# Focus: Use phrases from the END of the current chunk to find adjacent content.
REWRITE_CONTINUATION_PROMPT = """You are a content continuation specialist. The retrieved content appears to be TRUNCATED mid-speech or mid-thought. You need to find the NEXT CHUNK that continues this content.

**Original Question:** {question}

**Truncated Content (last portion):**
{last_portion}

**Your Task:**
1. Identify unique phrases or key terms from the END of the truncated content.
2. Generate ONE search query (2-5 words) that would match the BEGINNING of the next chunk.
3. AVOID using proper nouns (like person names) that might be in the original question but NOT in the continuation.
4. Focus on: topic-specific verbs, technical terms, or unique phrases that would appear in both chunks.

Return ONLY the query and nothing else."""


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


def format_grade_completeness_prompt(question: str, existing_context: str, new_context: str) -> str:
    """
    Format completeness grading prompt with separate existing and new contexts.

    Args:
        question: Original user question
        existing_context: Previously accumulated document contents
        new_context: Newly retrieved document contents

    Returns:
        Formatted completeness prompt
    """
    return GRADE_COMPLETENESS_PROMPT.format(
        question=question,
        existing_context=existing_context,
        new_context=new_context
    )


def format_rewrite_irrelevant_prompt(question: str) -> str:
    """Format prompt for broadening a failed search."""
    return REWRITE_IRRELEVANT_PROMPT.format(question=question)


def format_rewrite_incomplete_prompt(question: str, current_context: str, search_advice: str) -> str:
    """
    Format prompt for targeting missing topic information.
    
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


def format_rewrite_continuation_prompt(question: str, last_portion: str) -> str:
    """
    Format prompt for finding chunk continuations.
    
    Args:
        question: Original user question
        last_portion: The last ~500 chars of the truncated chunk
    """
    return REWRITE_CONTINUATION_PROMPT.format(
        question=question,
        last_portion=last_portion
    )
