
import logging

from typing import Type, Any, Optional

from pydantic import BaseModel, Field
try:
    # pydantic v2
    from pydantic import ConfigDict
except Exception:
    ConfigDict = dict  # fallback for type checkers; not used at runtime
from crewai.tools.base_tool import BaseTool
from crewai_tools import TavilySearchTool

logger = logging.getLogger(__name__)

# Constants
MAX_QUERY_LENGTH = 200

class SafeSearchToolInput(BaseModel):
    """Input schema for SafeSearchTool.
    
    Accepts flexible inputs. Prefer `query`, but also tolerates `description`,
    `content`, or a generic payload that will be normalized into a string.
    """
    query: Optional[Any] = Field(None, description="The search query string.")
    description: Optional[Any] = Field(None, description="Alternative field sometimes used by LLMs for the query.")
    content: Optional[Any] = Field(None, description="Alternative field name that may contain the query text.")

class SafeSearchTool(BaseTool):
    """Safe wrapper for TavilySearchTool that handles parameter validation.
    
    This tool provides a robust wrapper around the Tavily Search API with
    comprehensive error handling and input validation.
    """
    name: str = "Safe Tavily Search"
    description: str = (
        "Perform comprehensive web searches using the Tavily Search API. "
        "Supports configurable search depth (basic/advanced), topic filtering "
        "(general/news/finance), time ranges, domain control, and direct answers. "
        "Use this to find recent information, research papers, news, or technical "
        "details not in your training data."
    )
    args_schema: Type[BaseModel] = SafeSearchToolInput
    # Pydantic v2 config to allow arbitrary types (for _tavily_tool)
    model_config = ConfigDict(arbitrary_types_allowed=True) if isinstance(ConfigDict, type) else None

    # Configurable fields (validated by Pydantic); do not override __init__
    search_depth: str = "advanced"
    max_results: int = 5
    include_answer: bool = True
    timeout: int = 60
    # Ensure attribute exists even if model_post_init isn't called (e.g., Pydantic v1)
    _tavily_tool: Any = None

    def model_post_init(self, __context: Any) -> None:  # pydantic v2 hook
        """Post-init setup for underlying Tavily tool."""
        try:
            self._tavily_tool = TavilySearchTool(
                search_depth=self.search_depth,
                max_results=self.max_results,
                include_answer=self.include_answer,
                timeout=self.timeout,
            )
        except Exception as e:
            logger.warning(f"Could not initialize TavilySearchTool: {e}")
            self._tavily_tool = None

    def _run(self, query: Any = None, description: Any = None, content: Any = None, **kwargs: Any) -> str:
        """Execute the search with proper parameter handling.

        Args:
            query: The search query string or payload
            description: Alternate field that may contain the query string
            content: Alternate field that may contain the query string

        Returns:
            The search results or an appropriate error message
        """
        try:
            # Handle case where Tavily tool is not available
            if self._tavily_tool is None:
                logger.warning("Tavily search tool not available, falling back to default message")
                return "Search tool is not available. Please proceed with your existing knowledge."

            # Select among possible fields, then normalize
            selected = query if query is not None else (description if description is not None else content)
            if selected is None and kwargs:
                # Try common keys in kwargs
                for k in ("query", "description", "content", "text", "prompt", "input"):
                    if k in kwargs and kwargs[k] is not None:
                        selected = kwargs[k]
                        break

            # Normalize query to string and flatten dict-shaped inputs used by LLMs
            normalized_query = self._normalize_query(selected)
            if not normalized_query:
                logger.warning("Empty search query provided")
                return "Error: Empty search query provided. Please specify what you'd like to search for."

            # Validate query length to prevent abuse
            if len(normalized_query) > MAX_QUERY_LENGTH:
                logger.warning(f"Query too long ({len(normalized_query)} chars), truncating")
                normalized_query = normalized_query[:MAX_QUERY_LENGTH].rsplit(' ', 1)[0] + "..."

            # Execute search with comprehensive error handling
            try:
                logger.debug(f"Executing search with query: {normalized_query[:50]}...")
                result = self._tavily_tool.run(normalized_query)

                if not result:
                    logger.info("No search results returned")
                    return "No search results found for this query. Please try a different search term or proceed with existing knowledge."

                # Validate result format
                if not isinstance(result, str):
                    logger.warning(f"Unexpected result type: {type(result)}")
                    result = str(result)

                # Ensure result is not empty after processing
                if not result.strip():
                    return "Search completed but no useful results found. Please proceed with existing knowledge."

                logger.debug("Search completed successfully")
                return result

            except ConnectionError as e:
                logger.error(f"Network connection error during search: {e}")
                return "Search temporarily unavailable due to network issues. Please use your existing knowledge to continue the discussion."
            except TimeoutError as e:
                logger.error(f"Search timeout: {e}")
                return "Search request timed out. Please try again later or proceed with existing knowledge."
            except Exception as e:
                logger.exception(f"Search execution failed with error: {e}")
                return "Search temporarily unavailable. Please use your existing knowledge to continue the discussion."

        except Exception as e:
            logger.exception(f"Unexpected error in search tool: {e}")
            return f"Search tool encountered an unexpected error. Please continue with your existing knowledge."
    
    def _normalize_query(self, query) -> str:
        """Normalize and validate query input.
        
        Args:
            query: The input query (may be string or other type)
            
        Returns:
            Normalized query string
        """
        # Ensure query is a string
        if not isinstance(query, str):
            # Support dict-like payloads sometimes produced by tool-calling LLMs
            if hasattr(query, 'get'):
                possible_fields = [
                    'query',
                    'q',
                    'text',
                    'content',
                    'prompt',
                    'description',
                    'input',
                ]
                for field in possible_fields:
                    value = query.get(field)
                    if isinstance(value, str) and value.strip():
                        query = value
                        break
                else:
                    # Fall back to stringifying the payload if nothing suitable found
                    query = str(query)
            else:
                query = str(query)
        
        # Clean and validate the query string
        query = query.strip()
        if not query:
            return ""
        
        return query
