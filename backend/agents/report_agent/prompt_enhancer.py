"""
Prompt enhancer for injecting custom requirements into STORM pipeline.

This module provides utilities to enhance prompts with parsed custom requirements
at different stages of the report generation pipeline (outline, article, polish).
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class PromptEnhancer:
    """
    Enhances prompts with user's custom requirements.

    Takes parsed requirements and generates enhanced prompts for different
    stages of the STORM pipeline.
    """

    @staticmethod
    def enhance_topic_for_outline(
        base_topic: str, parsed_requirements: Optional[dict[str, Any]] = None
    ) -> str:
        """
        Enhance the topic/input for outline generation with custom requirements.

        Args:
            base_topic: Original research topic or content
            parsed_requirements: Parsed structured requirements

        Returns:
            Enhanced topic string with requirements injected
        """
        if not parsed_requirements:
            return base_topic

        enhancements = []

        # Extract style requirements
        style = parsed_requirements.get("style", {})
        if style:
            style_parts = []
            if style.get("tone"):
                style_parts.append(f"tone: {style['tone']}")
            if style.get("formality"):
                style_parts.append(f"formality: {style['formality']}")
            if style.get("complexity"):
                style_parts.append(f"complexity: {style['complexity']}")

            if style_parts:
                enhancements.append(f"Style: {', '.join(style_parts)}")

        # Extract structure requirements
        structure = parsed_requirements.get("structure", {})
        if structure:
            if structure.get("required_sections"):
                sections = ", ".join(structure["required_sections"])
                enhancements.append(f"Required sections: {sections}")

            if structure.get("section_emphasis"):
                emphasis_items = []
                for section, description in structure["section_emphasis"].items():
                    emphasis_items.append(f"{section} ({description})")
                if emphasis_items:
                    enhancements.append(
                        f"Section emphasis: {'; '.join(emphasis_items)}"
                    )

        # Extract content requirements
        content = parsed_requirements.get("content", {})
        if content:
            if content.get("focus_areas"):
                focus = ", ".join(content["focus_areas"])
                enhancements.append(f"Focus on: {focus}")

            constraints = content.get("constraints", {})
            if constraints:
                constraint_parts = []
                if constraints.get("min_words"):
                    constraint_parts.append(f"minimum {constraints['min_words']} words")
                if constraints.get("max_words"):
                    constraint_parts.append(f"maximum {constraints['max_words']} words")
                if constraints.get("citation_style"):
                    constraint_parts.append(
                        f"citation style: {constraints['citation_style']}"
                    )

                if constraint_parts:
                    enhancements.append(f"Constraints: {', '.join(constraint_parts)}")

            if content.get("avoid_topics"):
                avoid = ", ".join(content["avoid_topics"])
                enhancements.append(f"Avoid: {avoid}")

        # Extract audience
        audience = parsed_requirements.get("audience", "")
        if audience:
            enhancements.append(f"Target audience: {audience}")

        # Fallback to raw instructions if no structured requirements
        if not enhancements and parsed_requirements.get("raw_instructions"):
            enhancements.append(parsed_requirements["raw_instructions"])

        # Build enhanced topic
        if enhancements:
            requirements_text = "\n".join(f"- {e}" for e in enhancements)
            enhanced = f"""Research Topic: {base_topic}

User Requirements:
{requirements_text}

Please generate the outline considering both the research topic and user requirements above."""

            logger.info(
                f"Enhanced topic for outline generation with {len(enhancements)} requirements"
            )
            return enhanced

        return base_topic

    @staticmethod
    def enhance_for_article_generation(
        section_name: str, parsed_requirements: Optional[dict[str, Any]] = None
    ) -> str:
        """
        Generate additional guidance for article generation phase.

        Args:
            section_name: Name of the section being generated
            parsed_requirements: Parsed structured requirements

        Returns:
            Additional guidance text for article generation
        """
        if not parsed_requirements:
            return ""

        guidance = []

        # Style guidance
        style = parsed_requirements.get("style", {})
        if style:
            style_desc = []
            if style.get("tone"):
                style_desc.append(style["tone"])
            if style.get("formality"):
                style_desc.append(style["formality"])

            if style_desc:
                guidance.append(f"Write in {' and '.join(style_desc)} style")

        # Section-specific emphasis
        structure = parsed_requirements.get("structure", {})
        section_emphasis = structure.get("section_emphasis", {})
        if section_name in section_emphasis:
            guidance.append(f"For this section, {section_emphasis[section_name]}")

        # Content focus
        content = parsed_requirements.get("content", {})
        if content.get("focus_areas"):
            focus = ", ".join(content["focus_areas"])
            guidance.append(f"Emphasize: {focus}")

        # Audience consideration
        audience = parsed_requirements.get("audience", "")
        if audience:
            guidance.append(f"Target audience: {audience}")

        if guidance:
            return "\n".join(guidance)

        return ""

    @staticmethod
    def enhance_for_polish(parsed_requirements: Optional[dict[str, Any]] = None) -> str:
        """
        Generate guidance for article polishing phase.

        Args:
            parsed_requirements: Parsed structured requirements

        Returns:
            Guidance text for polish phase
        """
        if not parsed_requirements:
            return ""

        guidance = []

        # Final style check
        style = parsed_requirements.get("style", {})
        if style:
            guidance.append("Ensure consistent style throughout the article")
            if style.get("tone"):
                guidance.append(f"Maintain {style['tone']} tone")

        # Content constraints
        content = parsed_requirements.get("content", {})
        constraints = content.get("constraints", {})
        if constraints:
            if constraints.get("min_words"):
                guidance.append(
                    f"Ensure article has at least {constraints['min_words']} words"
                )
            if constraints.get("citation_style"):
                guidance.append(
                    f"Verify citations follow {constraints['citation_style']} style"
                )

        # Audience alignment
        audience = parsed_requirements.get("audience", "")
        if audience:
            guidance.append(f"Ensure content is appropriate for: {audience}")

        if guidance:
            return "Final polishing requirements:\n" + "\n".join(
                f"- {g}" for g in guidance
            )

        return ""

    @staticmethod
    def get_summary(parsed_requirements: Optional[dict[str, Any]] = None) -> str:
        """
        Get a summary of the custom requirements for logging.

        Args:
            parsed_requirements: Parsed structured requirements

        Returns:
            Human-readable summary of requirements
        """
        if not parsed_requirements:
            return "No custom requirements"

        parts = []

        style = parsed_requirements.get("style", {})
        if style:
            parts.append(f"Style: {style.get('tone', 'unspecified')}")

        structure = parsed_requirements.get("structure", {})
        if structure.get("required_sections"):
            parts.append(f"Sections: {len(structure['required_sections'])} required")

        content = parsed_requirements.get("content", {})
        if content.get("focus_areas"):
            parts.append(f"Focus: {len(content['focus_areas'])} areas")

        audience = parsed_requirements.get("audience", "")
        if audience:
            parts.append(f"Audience: {audience[:30]}...")

        if parts:
            return "; ".join(parts)

        return "Custom requirements provided"

    @staticmethod
    def format_requirements_text(
        parsed_requirements: Optional[dict[str, Any]] = None
    ) -> str:
        """
        Format parsed requirements as text for outline generation prompts.

        Args:
            parsed_requirements: Parsed structured requirements

        Returns:
            Formatted requirements text suitable for outline generation input
        """
        if not parsed_requirements:
            return "N/A"

        sections = []

        # Style requirements
        style = parsed_requirements.get("style", {})
        if style:
            style_parts = []
            if style.get("tone"):
                style_parts.append(f"tone: {style['tone']}")
            if style.get("formality"):
                style_parts.append(f"formality: {style['formality']}")
            if style.get("complexity"):
                style_parts.append(f"complexity: {style['complexity']}")
            if style_parts:
                sections.append(f"Style: {', '.join(style_parts)}")

        # Structure requirements
        structure = parsed_requirements.get("structure", {})
        if structure:
            struct_parts = []
            if structure.get("required_sections"):
                sections_list = structure["required_sections"]
                struct_parts.append(
                    f"Required sections: {', '.join(sections_list)}"
                )
            if structure.get("section_order"):
                struct_parts.append(f"Section order: {structure['section_order']}")
            if struct_parts:
                sections.append(f"Structure: {'; '.join(struct_parts)}")

        # Content requirements
        content = parsed_requirements.get("content", {})
        if content:
            content_parts = []
            if content.get("focus_areas"):
                focus_list = content["focus_areas"]
                content_parts.append(f"Focus on: {', '.join(focus_list)}")
            if content.get("depth"):
                content_parts.append(f"Depth: {content['depth']}")
            if content_parts:
                sections.append(f"Content: {'; '.join(content_parts)}")

        # Audience requirements
        audience = parsed_requirements.get("audience", "")
        if audience:
            sections.append(f"Target audience: {audience}")

        if sections:
            return "\n".join(sections)

        return "N/A"


def enhance_topic_with_requirements(
    topic: str,
    custom_requirements: Optional[str] = None,
    parsed_requirements: Optional[dict[str, Any]] = None,
) -> str:
    """
    Convenience function to enhance topic with requirements.

    Args:
        topic: Original research topic
        custom_requirements: Raw custom requirements text (optional)
        parsed_requirements: Parsed requirements dict (optional)

    Returns:
        Enhanced topic string
    """
    if parsed_requirements:
        return PromptEnhancer.enhance_topic_for_outline(topic, parsed_requirements)
    elif custom_requirements:
        # Simple concatenation if no parsed requirements
        return f"{topic}\n\nUser requirements: {custom_requirements}"
    else:
        return topic
