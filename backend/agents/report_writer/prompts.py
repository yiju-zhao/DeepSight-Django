"""
Prompts for Report Writer Agent

This module contains all prompts used by the report writer workflow.
These prompts are extracted from Deep_Research/src/prompts.py
and focus only on report generation functionality.
"""


# ============================================================================
# REPORT GENERATION PROMPTS
# ============================================================================

report_generation_prompt = """Based on all the research conducted, create a comprehensive, well-structured answer to the overall research brief:
<Research Brief>
{research_brief}
</Research Brief>

CRITICAL: Make sure the answer is written in the same language as the human messages!
For example, if the user's messages are in English, then MAKE SURE you write your response in English. If the user's messages are in Chinese, then MAKE SURE you write your entire response in Chinese.
This is critical. The user will only understand the answer if it is written in the same language as their input message.

Today's date is {date}.

Here are the findings from the research:
<Findings>
{findings}
</Findings>

Please create a detailed answer to the overall research brief that:
1. Is well-organized with proper headings (# for title, ## for sections, ### for subsections)
2. Includes specific facts and insights from the research
3. References relevant sources using [Title](URL) format
4. Provides a balanced, thorough analysis. Be as comprehensive as possible, and include all information that is relevant to the overall research question. People are using you for deep research and will expect detailed, comprehensive answers.
5. Includes a "Sources" section at the end with all referenced links

You can structure your report in a number of different ways. Here are some examples:

To answer a question that asks you to compare two things, you might structure your report like this:
1/ intro
2/ overview of topic A
3/ overview of topic B
4/ comparison between A and B
5/ conclusion

To answer a question that asks you to return a list of things, you might only need a single section which is the entire list.
1/ list of things or table of things
Or, you could choose to make each item in the list a separate section in the report. When asked for lists, you don't need an introduction or conclusion.
1/ item 1
2/ item 2
3/ item 3

To answer a question that asks you to summarize a topic, give a report, or give an overview, you might structure your report like this:
1/ overview of topic
2/ concept 1
3/ concept 2
4/ concept 3
5/ conclusion

If you think you can answer the question with a single section, you can do that too!
1/ answer

REMEMBER: Section is a VERY fluid and loose concept. You can structure your report however you think is best, including in ways that are not listed above!
Make sure that your sections are cohesive, and make sense for the reader.

For each section of the report, do the following:
- Use simple, clear language
- Keep important details from the research findings
- Use ## for section title (Markdown format) for each section of the report
- Do NOT ever refer to yourself as the writer of the report. This should be a professional report without any self-referential language. 
- Do not say what you are doing in the report. Just write the report without any commentary from yourself.
- Each section should be as long as necessary to deeply answer the question with the information you have gathered. It is expected that sections will be fairly long and verbose. You are writing a deep research report, and users will expect a thorough answer.
- Use bullet points to list out information when appropriate, but by default, write in paragraph form.

REMEMBER:
The brief and research may be in English, but you need to translate this information to the right language when writing the final answer.
Make sure the final answer report is in the SAME language as the human messages in the message history.

Format the report in clear markdown with proper structure and include source references where appropriate.

<Citation Rules>
- Assign each unique URL a single citation number in your text
- End with ### Sources that lists each source with corresponding numbers
- IMPORTANT: Number sources sequentially without gaps (1,2,3,4...) in the final list regardless of which sources you choose
- Each source should be a separate line item in a list, so that in markdown it is rendered as a list.
- Example format:
  [1] Source Title: URL
  [2] Source Title: URL
- Citations are extremely important. Make sure to include these, and pay a lot of attention to getting these right. Users will often use these citations to look into more information.
</Citation Rules>
"""


# ============================================================================
# STYLE-SPECIFIC PROMPTS
# ============================================================================

STYLE_INSTRUCTIONS = {
    "academic": """
Write in an academic style:
- Use formal language and precise terminology
- Include proper citations throughout
- Maintain objective tone
- Structure with clear thesis and supporting arguments
- Include methodology notes where relevant
""",
    "casual": """
Write in a casual, accessible style:
- Use conversational language
- Explain technical terms simply
- Include engaging examples
- Keep paragraphs short and readable
- Use bullet points for clarity
""",
    "technical": """
Write in a technical documentation style:
- Use precise technical terminology
- Include code examples or specifications where relevant
- Structure with clear hierarchy
- Focus on accuracy and detail
- Use tables for comparisons
""",
    "business": """
Write in a business report style:
- Lead with key findings and recommendations
- Use executive summary format
- Include actionable insights
- Focus on implications and next steps
- Use professional but accessible language
"""
}


def get_style_instructions(style: str) -> str:
    """Get style-specific writing instructions."""
    return STYLE_INSTRUCTIONS.get(style, STYLE_INSTRUCTIONS["academic"])


# ============================================================================
# REFINEMENT PROMPTS
# ============================================================================

polish_report_prompt = """Review and polish the following draft report to improve clarity, coherence, and professionalism.

<Draft Report>
{draft_report}
</Draft Report>

<Research Brief>
{research_brief}
</Research Brief>

Please improve the report by:
1. Fixing any grammatical or spelling errors
2. Improving sentence flow and transitions
3. Ensuring consistent formatting
4. Strengthening weak arguments with available evidence
5. Removing redundant or repetitive content
6. Ensuring all citations are properly formatted

Maintain the same overall structure and content, but make it more polished and professional.
Return the complete improved report.
"""


outline_generation_prompt = """Based on the research findings, generate an outline for a comprehensive report.

<Research Brief>
{research_brief}
</Research Brief>

<Findings Summary>
{findings_summary}
</Findings_Summary>

Create a detailed outline with:
1. Main sections (use ## headings)
2. Key points to cover in each section
3. Where to incorporate specific findings
4. Suggested sources for each section

Return the outline in markdown format.
"""
