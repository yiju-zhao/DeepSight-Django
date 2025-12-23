import asyncio
import os
import json
import django
from django.conf import settings

# Configure Django settings (minimal for standalone script)
if not settings.configured:
    settings.configure(
        INSTALLED_APPS=[
            'backend.agents.rag_agent',
        ],
        DATABASES={}, # No DB needed for this mock test
    )
    django.setup()

from backend.agents.rag_agent.graph import DeepSightRAGAgent
from backend.agents.rag_agent.states import RAGAgentState
from langchain_core.messages import HumanMessage

async def test_rag_workflow():
    print("Initializing RAG Agent...")
    rag_agent = DeepSightRAGAgent()
    
    # Mock input state
    initial_state = {
        "question": "What are the key features of DeepSight?",
        "original_question": "What are the key features of DeepSight?",
        "documents": [],
        "iteration_count": 0
    }
    
    print(f"Starting Workflow with question: {initial_state['question']}")
    
    # Run the graph
    app = rag_agent.app
    final_state = await app.ainvoke(initial_state)
    
    print("\n--- WORKFLOW COMPLETE ---")
    
    # Validating Output
    print(f"Final Step: {final_state.get('current_step')}")
    print(f"Generated Answer Logic Test: {'PASS' if final_state.get('generation') else 'FAIL'}")
    
    # Verify Semantic Groups (The optimization target)
    groups = final_state.get('semantic_groups')
    if groups:
        print(f"Semantic Groups Found: {len(groups)}")
        print(json.dumps(groups, indent=2))
    else:
        print("No Semantic Groups found (might be expected if mock retrieval failed)")

    # Verify State Pruning
    if not final_state.get('documents') and not final_state.get('reordered_context'):
         print("State Pruning Test: PASS (Heavy fields cleared)")
    else:
         print(f"State Pruning Test: FAIL - Docs: {len(final_state.get('documents', []))}")

if __name__ == "__main__":
    asyncio.run(test_rag_workflow())
