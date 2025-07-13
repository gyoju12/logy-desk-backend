import os
import tempfile
from datetime import datetime, timezone

import pytest
from fastapi import status

# Test data
TEST_AGENT = {
    "name": "Test Agent",
    "agent_type": "sub",
    "model": "gpt-4",
    "temperature": 1.5,  # Updated to be within 0-2 range
    "system_prompt": "Test system prompt",
}

TEST_DOCUMENT = {
    "title": "Test Document",
    "filename": "test.txt",
    "content_type": "text/plain",
    "size": 1024,  # Added required field
}


def test_create_agent(client):
    """Test creating a new agent"""
    response = client.post("/agents", json=TEST_AGENT)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == TEST_AGENT["name"]
    assert data["agent_type"] == TEST_AGENT["agent_type"]
    assert data["model"] == TEST_AGENT["model"]
    assert "id" in data
    return data["id"]


def test_get_agent(client, test_agent):
    """Test getting an agent by ID"""
    response = client.get(f"/agents/{test_agent.id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == test_agent.id
    assert data["name"] == test_agent.name


def test_list_agents(client, test_agent):
    """Test listing all agents"""
    response = client.get("/agents")
    assert response.status_code == status.HTTP_200_OK
    agents = response.json()
    assert isinstance(agents, list)
    assert len(agents) > 0
    assert any(agent["id"] == str(test_agent.id) for agent in agents)


def test_upload_document(client):
    """Test uploading a document"""
    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        tmp.write(b"Test document content")
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            response = client.post(
                "/documents/upload",
                files={"file": ("test.txt", f, "text/plain")},
                data={"title": "Test Document"},
            )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "id" in data
        assert data["title"] == "Test Document"
        assert data["filename"] == "test.txt"
        return data["id"]
    finally:
        # Clean up the temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_list_documents(client):
    """Test listing all documents"""
    response = client.get("/documents")
    assert response.status_code == status.HTTP_200_OK
    documents = response.json()
    assert isinstance(documents, list)


def test_create_chat_session(client):
    """Test creating a new chat session"""
    response = client.post("/chat_sessions", json={"title": "Test Chat"})
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "id" in data
    assert "updated_at" in data  # Ensure updated_at is in the response
    assert data["title"] == "Test Chat"
    return data["id"]


def test_send_chat_message(client, test_chat_session):
    """Test sending a chat message"""
    response = client.post(
        f"/chat/{test_chat_session}/messages",
        json={"role": "user", "content": "Hello, world!"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "id" in data
    assert data["content"] == "Hello, world!"
    assert data["role"] == "user"
    return data["id"]


def test_get_chat_messages(client, test_chat_session):
    """Test getting chat messages for a session"""
    # First send a message
    message_id = test_send_chat_message(client, test_chat_session)

    # Then retrieve messages
    response = client.get(f"/chat/{test_chat_session}/messages")
    assert response.status_code == status.HTTP_200_OK
    messages = response.json()
    assert isinstance(messages, list)
    assert len(messages) > 0
    assert any(msg["id"] == message_id for msg in messages)
