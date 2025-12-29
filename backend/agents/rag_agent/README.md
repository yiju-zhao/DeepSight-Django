# RAG Agent with MCP Integration

Agentic RAG (Retrieval-Augmented Generation) agent using LangGraph orchestration and RAGFlow MCP server for knowledge retrieval.

## Overview

The RAG agent implements an intelligent retrieval pattern with:
- **Agentic Decision Making**: LLM decides when to retrieve information
- **Document Grading**: Filters irrelevant results
- **Question Rewriting**: Improves failed searches
- **MCP Protocol**: Standardized integration with RAGFlow server

## Architecture

```
START → generate_query_or_respond → [tools_condition]
             ↓                              ↓
           END                          retrieve
                                           ↓
                                    grade_documents
                                     ↓         ↓
                          (relevant)          (not relevant)
                             ↓                      ↓
                      generate_answer        rewrite_question
                             ↓                      ↓
                           END         generate_query_or_respond
```

## Prerequisites

1. **RAGFlow MCP Server**: Running at `http://localhost:9382/mcp/`
2. **Dependencies**: Install required packages
   ```bash
   pip install langchain langchain-mcp-adapters langgraph langchain-openai
   ```
3. **API Key**: OpenAI API key for LLM calls
4. **Dataset IDs**: RAGFlow dataset IDs configured

## Quick Start

```python
from notebooks.agents.rag_agent import create_rag_agent, RAGAgentConfig
from langchain_core.messages import HumanMessage
import os

# Configure the agent
config = RAGAgentConfig(
    model_name="gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
    dataset_ids=["your_dataset_id"],
    mcp_server_url="http://localhost:9382/mcp/",
)

# Create the agent (async)
agent = await create_rag_agent(config)

# Invoke the agent
result = await agent.ainvoke({
    "messages": [HumanMessage(content="What is deep learning?")],
    "question": "What is deep learning?",
    "retrieved_chunks": [],
})

# Get the final answer
final_answer = result["messages"][-1].content
print(final_answer)
```

## Configuration Options

### Basic Configuration

```python
config = RAGAgentConfig(
    # Model settings
    model_name="gpt-4o-mini",           # OpenAI model name
    api_key=os.getenv("OPENAI_API_KEY"), # Optional, uses env by default

    # Dataset configuration
    dataset_ids=["dataset_1", "dataset_2"],  # Required
    document_ids=["doc_1"],                   # Optional: filter specific docs

    # MCP server
    mcp_server_url="http://localhost:9382/mcp/",
)
```

### Advanced Configuration

```python
config = RAGAgentConfig(
    # ... basic settings ...

    # Temperature settings for different phases
    temperature=0.7,              # Reasoning phase (exploration)
    eval_temperature=0.1,         # Evaluation phase (precision)
    synthesis_temperature=0.3,    # Final answer (balance)

    # Retrieval settings
    similarity_threshold=0.4,     # Minimum similarity for results
    top_k=10,                     # Max chunks to retrieve
    max_iterations=5,             # Max ReAct loop iterations
)
```

## Temperature Explained

The agent uses different temperatures for different phases:

- **Temperature (0.7)**: Reasoning and query generation - encourages exploration
- **Eval Temperature (0.1)**: Document grading - requires precision
- **Synthesis Temperature (0.3)**: Final answer generation - balanced creativity

## File Structure

```
backend/notebooks/agents/rag_agent/
├── __init__.py          # Public API exports
├── config.py            # Configuration dataclass
├── states.py            # LangGraph state definitions
├── prompts.py           # System prompts and templates
├── graph.py             # LangGraph workflow
├── tools.py             # MCP retrieval tools
├── utils.py             # Utility functions
├── example_usage.py     # Usage examples
└── README.md            # This file
```

## Running the Example

```bash
cd backend
python -m notebooks.agents.rag_agent.example_usage
```

## Troubleshooting

### MCP Server Connection Issues

**Error**: `Failed to connect to MCP server`

**Solution**:
1. Verify RAGFlow MCP server is running
2. Check server URL is correct
3. Ensure network connectivity

### Tool Not Found

**Error**: `ragflow_retrieval tool not found`

**Solution**:
1. Verify MCP server exposes `ragflow_retrieval` tool
2. Check MCP server logs for errors
3. Test server connection: `curl http://localhost:9382/mcp/`

### Import Errors

**Error**: `ModuleNotFoundError: No module named 'langchain_mcp_adapters'`

**Solution**:
```bash
pip install langchain-mcp-adapters
```

### Async/Await Issues

**Error**: `RuntimeWarning: coroutine 'create_rag_agent' was never awaited`

**Solution**:
```python
# Wrong
agent = create_rag_agent(config)

# Correct
agent = await create_rag_agent(config)
```

## Environment Variables

Add to your Django settings or `.env` file:

```python
# Django settings.py
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
RAGFLOW_MCP_URL = os.getenv("RAGFLOW_MCP_URL", "http://localhost:9382/mcp/")
```

## API Reference

### `create_rag_agent(config: RAGAgentConfig)`

Create and compile the RAG agent graph.

**Parameters**:
- `config`: RAGAgentConfig with model and retrieval settings

**Returns**: Compiled LangGraph (async)

**Example**:
```python
agent = await create_rag_agent(config)
```

### `RAGAgentConfig`

Configuration dataclass for RAG agent.

**Required Fields**:
- `dataset_ids`: List of RAGFlow dataset IDs

**Optional Fields**:
- `model_name`: OpenAI model (default: "gpt-5")
- `mcp_server_url`: MCP server URL (default: "http://localhost:9382/mcp/")
- `temperature`: Reasoning temperature (default: 0.7)
- `eval_temperature`: Evaluation temperature (default: 0.1)
- `synthesis_temperature`: Synthesis temperature (default: 0.3)
- `similarity_threshold`: Minimum similarity (default: 0.4)
- `top_k`: Max chunks (default: 10)
- `max_iterations`: Max iterations (default: 5)

### `create_mcp_retrieval_tools(dataset_ids, mcp_server_url, document_ids)`

Create MCP-based retrieval tools.

**Parameters**:
- `dataset_ids`: List of dataset IDs
- `mcp_server_url`: MCP server URL (default: "http://localhost:9382/mcp/")
- `document_ids`: Optional list of document IDs

**Returns**: List of LangChain tools (async)

### `invoke_mcp_retrieval(tools, question, dataset_ids, document_ids)`

Invoke MCP retrieval tool directly.

**Parameters**:
- `tools`: Tools from `create_mcp_retrieval_tools`
- `question`: Search query
- `dataset_ids`: Optional override for dataset IDs
- `document_ids`: Optional override for document IDs

**Returns**: Formatted retrieval results (async)

## Further Reading

- [LangChain MCP Documentation](https://python.langchain.com/docs/integrations/tools/mcp/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [RAGFlow Documentation](https://ragflow.io/docs/)
