"""
Agent Registry for Coordinator

This module provides a registry for coordinator-accessible agents.
Only research_agent and report_writer are exposed to the coordinator.
Additional agents (data_analyst, reviewer) are internal to research_agent.
"""

from typing import Type

from .schema import AgentCapability, RESEARCH_AGENT_CAPABILITY, WRITER_AGENT_CAPABILITY


class AgentRegistry:
    """
    Registry for coordinator-accessible agents.
    
    This registry contains only the agents that the coordinator
    can directly invoke. Internal agents are not exposed here.
    """
    
    AGENTS: dict[str, AgentCapability] = {
        "research": RESEARCH_AGENT_CAPABILITY,
        "writer": WRITER_AGENT_CAPABILITY,
    }
    
    @classmethod
    def get(cls, name: str) -> AgentCapability:
        """
        Get an agent capability by name.
        
        Args:
            name: Agent name
            
        Returns:
            AgentCapability for the agent
            
        Raises:
            KeyError: If agent not found
        """
        if name not in cls.AGENTS:
            raise KeyError(f"Unknown agent: {name}. Available: {list(cls.AGENTS.keys())}")
        return cls.AGENTS[name]
    
    @classmethod
    def list_capabilities(cls) -> list[AgentCapability]:
        """Get list of all available agent capabilities."""
        return list(cls.AGENTS.values())
    
    @classmethod
    def list_names(cls) -> list[str]:
        """Get list of all available agent names."""
        return list(cls.AGENTS.keys())
    
    @classmethod
    def has_agent(cls, name: str) -> bool:
        """Check if an agent is registered."""
        return name in cls.AGENTS
