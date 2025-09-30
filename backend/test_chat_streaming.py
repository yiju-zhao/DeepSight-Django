#!/usr/bin/env python
"""
Quick diagnostic script to test chat streaming functionality.
Run with: python test_chat_streaming.py
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings.development')
django.setup()

from notebooks.models import ChatSession, Notebook
from notebooks.services.chat_service import ChatService

def test_session_streaming():
    """Test if session chat streaming works"""

    # Get the first active session
    session = ChatSession.objects.filter(status='active').first()

    if not session:
        print("❌ No active chat sessions found")
        print("   Please create a chat session first")
        return False

    print(f"✓ Found session: {session.session_id}")
    print(f"  - Title: {session.title}")
    print(f"  - RagFlow Session ID: {session.ragflow_session_id}")
    print(f"  - RagFlow Agent ID: {session.ragflow_agent_id}")

    if not session.ragflow_session_id or not session.ragflow_agent_id:
        print("❌ Session is not properly initialized with RagFlow")
        return False

    notebook = session.notebook
    print(f"✓ Notebook: {notebook.name} (ID: {notebook.id})")
    print(f"  - RagFlow Dataset ID: {notebook.ragflow_dataset_id}")

    # Test the streaming
    print("\n📡 Testing streaming with question: 'Hello'")
    print("-" * 60)

    chat_service = ChatService()

    try:
        stream = chat_service.create_session_chat_stream(
            session_id=str(session.session_id),
            notebook=notebook,
            user_id=notebook.user.id,
            question="Hello"
        )

        chunk_count = 0
        for chunk in stream:
            chunk_count += 1
            print(f"Chunk {chunk_count}: {chunk[:100]}...")  # Print first 100 chars

            if chunk_count > 10:  # Limit output for testing
                print("(truncated after 10 chunks)")
                break

        print("-" * 60)
        print(f"✓ Streaming completed successfully ({chunk_count} chunks)")
        return True

    except Exception as e:
        print(f"❌ Streaming failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Chat Streaming Diagnostic Test")
    print("=" * 60)
    print()

    success = test_session_streaming()

    print()
    print("=" * 60)
    if success:
        print("✓ All tests passed!")
    else:
        print("❌ Tests failed - check the errors above")
    print("=" * 60)

    sys.exit(0 if success else 1)
