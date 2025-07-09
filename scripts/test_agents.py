#!/usr/bin/env python3
"""
Test script for Agents API endpoints.

This script tests the following endpoints:
- POST /api/v1/agents
- GET /api/v1/agents
- GET /api/v1/agents/{agent_id}
- PUT /api/v1/agents/{agent_id}
- DELETE /api/v1/agents/{agent_id}
"""
import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import httpx
import uuid

# Add the parent directory to the path so we can import config
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configuration
BASE_URL = "http://localhost:8000/api/v1"

class AgentTestClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
        self.agents_url = f"{base_url}/agents"
    
    async def create_agent(self, agent_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new agent."""
        try:
            print(f"Sending request to: {self.agents_url}")
            print(f"Request data: {agent_data}")
            
            response = await self.client.post(
                self.agents_url,
                json=agent_data,
                timeout=10.0
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            print(f"Response text: {response.text}")
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"❌ Create agent failed: {str(e)}")
            if hasattr(e, "response"):
                print(f"Response status: {e.response.status_code}")
                print(f"Response headers: {dict(e.response.headers)}")
                print(f"Response text: {e.response.text}")
            return None
    
    async def list_agents(self) -> Optional[Dict[str, Any]]:
        """List all agents."""
        try:
            response = await self.client.get(self.agents_url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ List agents failed: {str(e)}")
            return None
    
    async def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific agent by ID."""
        try:
            response = await self.client.get(f"{self.agents_url}/{agent_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Get agent failed: {str(e)}")
            if hasattr(e, "response"):
                print(f"Response: {e.response.text}")
            return None
    
    async def update_agent(self, agent_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing agent."""
        try:
            response = await self.client.put(
                f"{self.agents_url}/{agent_id}",
                json=update_data
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Update agent failed: {str(e)}")
            if hasattr(e, "response"):
                print(f"Response: {e.response.text}")
            return None
    
    async def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent."""
        try:
            response = await self.client.delete(f"{self.agents_url}/{agent_id}")
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"❌ Delete agent failed: {str(e)}")
            if hasattr(e, "response"):
                print(f"Response: {e.response.text}")
            return False

async def main():
    print("🚀 Starting Agents API tests...")
    
    # Initialize test client
    client = AgentTestClient(BASE_URL)
    
    # Test data
    test_agent = {
        "name": "Test Agent",
        "agent_type": "sub",
        "model": "gpt-4",
        "temperature": 0.7,
        "system_prompt": "You are a helpful assistant."
    }
    
    # 1. Test creating an agent
    print("\n1. Testing agent creation...")
    created_agent = await client.create_agent(test_agent)
    if not created_agent:
        print("❌ Agent creation test failed. Exiting...")
        return
    
    agent_id = created_agent.get("id")
    print(f"✅ Agent created successfully! ID: {agent_id}")
    
    # 2. Test getting the agent
    print("\n2. Testing agent retrieval...")
    retrieved_agent = await client.get_agent(agent_id)
    if retrieved_agent and retrieved_agent.get("id") == agent_id:
        print(f"✅ Successfully retrieved agent: {retrieved_agent.get('name')}")
    else:
        print("❌ Failed to retrieve agent")
    
    # 3. Test listing all agents
    print("\n3. Testing agent listing...")
    agents = await client.list_agents()
    if agents and len(agents) > 0:
        print(f"✅ Successfully listed {len(agents)} agent(s)")
    else:
        print("❌ Failed to list agents")
    
    # 4. Test updating the agent
    print("\n4. Testing agent update...")
    update_data = {
        "name": "Updated Test Agent",
        "temperature": 0.8
    }
    updated_agent = await client.update_agent(agent_id, update_data)
    if updated_agent and updated_agent.get("name") == "Updated Test Agent":
        print(f"✅ Successfully updated agent. New name: {updated_agent.get('name')}")
    else:
        print("❌ Failed to update agent")
    
    # 5. Test deleting the agent
    print("\n5. Testing agent deletion...")
    if await client.delete_agent(agent_id):
        print("✅ Successfully deleted agent")
    else:
        print("❌ Failed to delete agent")
    
    # Verify deletion
    print("\n6. Verifying agent deletion...")
    deleted_agent = await client.get_agent(agent_id)
    if not deleted_agent or "detail" in deleted_agent:
        print("✅ Agent deletion verified")
    else:
        print("❌ Agent still exists after deletion")
    
    print("\n✨ All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
