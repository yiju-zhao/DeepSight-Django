"""
Requirements parser service for parsing user's custom requirements.

This module uses LLM to parse free-text custom requirements into structured
format that can be injected into the STORM pipeline.
"""

import json
import logging
from typing import Optional

import dspy
from django.conf import settings

logger = logging.getLogger(__name__)


class ParseRequirements(dspy.Signature):
    """Parse user's custom requirements for report generation into structured format."""

    requirements_text = dspy.InputField(
        desc="User's free-text custom requirements for the report"
    )

    style = dspy.OutputField(
        desc="Style requirements as JSON with keys: tone (academic/casual/professional), formality (formal/informal), complexity (simple/moderate/complex)"
    )
    structure = dspy.OutputField(
        desc="Structure requirements as JSON with keys: required_sections (list), section_emphasis (dict)"
    )
    content = dspy.OutputField(
        desc="Content requirements as JSON with keys: focus_areas (list), constraints (dict), avoid_topics (list)"
    )
    audience = dspy.OutputField(desc="Target audience description (string)")


class RequirementsParser:
    """
    Parser for user custom requirements using DSPy.

    Converts free-text requirements into structured format for injection
    into the STORM report generation pipeline.
    """

    def __init__(self, model_provider: str = "openai"):
        """
        Initialize the parser with a language model.

        Args:
            model_provider: Model provider ('openai', 'google', etc.)
        """
        self.model_provider = model_provider
        self._setup_language_model()
        self.parser = dspy.ChainOfThought(ParseRequirements)

    def _setup_language_model(self):
        """Setup DSPy language model based on provider."""
        try:
            if self.model_provider == "openai":
                lm = dspy.OpenAI(
                    model=getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"),
                    api_key=settings.OPENAI_API_KEY,
                    temperature=0.2,
                    max_tokens=2000,
                )
            elif self.model_provider == "google":
                lm = dspy.Google(
                    model=getattr(settings, "GOOGLE_MODEL", "gemini-1.5-flash"),
                    api_key=settings.GOOGLE_API_KEY,
                    temperature=0.2,
                    max_output_tokens=2000,
                )
            else:
                # Default to OpenAI
                lm = dspy.OpenAI(
                    model="gpt-4o-mini",
                    api_key=settings.OPENAI_API_KEY,
                    temperature=0.2,
                    max_tokens=2000,
                )

            dspy.settings.configure(lm=lm)
            logger.info(
                f"RequirementsParser initialized with {self.model_provider} model"
            )

        except Exception as e:
            logger.error(f"Failed to setup language model: {e}")
            raise

    def parse(self, requirements_text: str) -> Optional[dict]:
        """
        Parse user's free-text requirements into structured format.

        Args:
            requirements_text: User's custom requirements as free text

        Returns:
            Structured requirements dict with keys:
            - style: {tone, formality, complexity}
            - structure: {required_sections, section_emphasis}
            - content: {focus_areas, constraints, avoid_topics}
            - audience: str
            - raw_instructions: str (original text)

            Returns None if parsing fails or text is empty.
        """
        if not requirements_text or not requirements_text.strip():
            logger.info("No custom requirements provided")
            return None

        try:
            logger.info(f"Parsing custom requirements: {requirements_text[:100]}...")

            # Use DSPy to parse the requirements
            result = self.parser(requirements_text=requirements_text.strip())

            # Parse JSON outputs
            parsed = {
                "style": self._safe_json_parse(result.style, {}),
                "structure": self._safe_json_parse(result.structure, {}),
                "content": self._safe_json_parse(result.content, {}),
                "audience": result.audience if hasattr(result, "audience") else "",
                "raw_instructions": requirements_text.strip(),
            }

            # Validate and clean the parsed structure
            parsed = self._validate_and_clean(parsed)

            logger.info(
                f"Successfully parsed requirements: {json.dumps(parsed, indent=2)}"
            )
            return parsed

        except Exception as e:
            logger.error(f"Failed to parse requirements: {e}", exc_info=True)
            # Return a fallback structure with just the raw text
            return {
                "style": {},
                "structure": {},
                "content": {"focus_areas": [requirements_text.strip()]},
                "audience": "",
                "raw_instructions": requirements_text.strip(),
            }

    def _safe_json_parse(self, json_str: str, default: dict) -> dict:
        """Safely parse JSON string, returning default if parsing fails."""
        if not json_str:
            return default

        try:
            # Handle both string and dict inputs
            if isinstance(json_str, dict):
                return json_str

            # Try to parse as JSON
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse JSON: {e}. Input: {json_str[:200]}")
            return default

    def _validate_and_clean(self, parsed: dict) -> dict:
        """
        Validate and clean the parsed requirements.

        Ensures all required keys exist and values are properly formatted.
        """
        # Ensure style has expected keys
        if "style" not in parsed or not isinstance(parsed["style"], dict):
            parsed["style"] = {}

        # Ensure structure has expected keys
        if "structure" not in parsed or not isinstance(parsed["structure"], dict):
            parsed["structure"] = {}

        if "required_sections" not in parsed["structure"]:
            parsed["structure"]["required_sections"] = []
        elif not isinstance(parsed["structure"]["required_sections"], list):
            parsed["structure"]["required_sections"] = []

        if "section_emphasis" not in parsed["structure"]:
            parsed["structure"]["section_emphasis"] = {}
        elif not isinstance(parsed["structure"]["section_emphasis"], dict):
            parsed["structure"]["section_emphasis"] = {}

        # Ensure content has expected keys
        if "content" not in parsed or not isinstance(parsed["content"], dict):
            parsed["content"] = {}

        if "focus_areas" not in parsed["content"]:
            parsed["content"]["focus_areas"] = []
        elif not isinstance(parsed["content"]["focus_areas"], list):
            parsed["content"]["focus_areas"] = []

        if "constraints" not in parsed["content"]:
            parsed["content"]["constraints"] = {}
        elif not isinstance(parsed["content"]["constraints"], dict):
            parsed["content"]["constraints"] = {}

        if "avoid_topics" not in parsed["content"]:
            parsed["content"]["avoid_topics"] = []
        elif not isinstance(parsed["content"]["avoid_topics"], list):
            parsed["content"]["avoid_topics"] = []

        # Ensure audience is string
        if "audience" not in parsed or not isinstance(parsed["audience"], str):
            parsed["audience"] = ""

        # Ensure raw_instructions exists
        if "raw_instructions" not in parsed:
            parsed["raw_instructions"] = ""

        return parsed


def parse_custom_requirements(
    requirements_text: str, model_provider: str = "openai"
) -> Optional[dict]:
    """
    Convenience function to parse custom requirements.

    Args:
        requirements_text: User's custom requirements as free text
        model_provider: Model provider to use ('openai', 'google', etc.)

    Returns:
        Structured requirements dict or None if parsing fails
    """
    parser = RequirementsParser(model_provider=model_provider)
    return parser.parse(requirements_text)
