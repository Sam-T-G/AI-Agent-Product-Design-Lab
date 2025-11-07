"""
Capability discovery system for multi-level agent hierarchies.
"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
import asyncio

from db.schemas import AgentModel
from core.delegation import AgentCapability
from core.gemini_client import generate_text
from core.logging import get_logger
import json

logger = get_logger("capability_discovery")


class CapabilityDiscovery:
    """Discovers and maps agent capabilities recursively."""
    
    def __init__(self, db: Session):
        self.db = db
        self.cache: Dict[str, AgentCapability] = {}
    
    async def discover_capabilities(
        self,
        agent: AgentModel,
        api_key: str,
        depth: int = 0,
        session_id: Optional[str] = None
    ) -> AgentCapability:
        """
        Recursively discover capabilities of agent and all descendants.
        
        Returns complete capability map of the subtree.
        """
        # Check cache
        cache_key = f"{agent.id}_{depth}"
        if cache_key in self.cache:
            logger.info("capability_cache_hit", agent_id=agent.id, depth=depth)
            return self.cache[cache_key]
        
        logger.info("capability_discovery_start", agent_id=agent.id, agent_name=agent.name, depth=depth)
        
        # Analyze agent's own capabilities from system_prompt
        own_capabilities = await self._analyze_agent_capabilities(agent, api_key)
        
        # Get children
        children = self._load_children(agent.id, session_id)
        
        # Recursively discover children's capabilities
        child_capabilities = []
        if children:
            logger.info("capability_discovery_children", agent_id=agent.id, child_count=len(children))
            
            # Discover children in parallel
            tasks = [
                self.discover_capabilities(child, api_key, depth + 1, session_id)
                for child in children
            ]
            child_capabilities = await asyncio.gather(*tasks)
        
        # Build capability object
        capability = AgentCapability(
            agent_id=agent.id,
            agent_name=agent.name,
            can_handle=own_capabilities,
            confidence=0.7,  # Default confidence
            depth=depth,
            children=list(child_capabilities)
        )
        
        # Cache it
        self.cache[cache_key] = capability
        
        logger.info(
            "capability_discovery_complete",
            agent_id=agent.id,
            capabilities=own_capabilities,
            child_count=len(child_capabilities),
            max_depth=capability.get_max_depth()
        )
        
        return capability
    
    async def _analyze_agent_capabilities(
        self,
        agent: AgentModel,
        api_key: str
    ) -> List[str]:
        """
        Analyze agent's system_prompt to extract capabilities.
        
        Returns list of keywords/topics the agent can handle.
        """
        prompt = f"""Analyze this agent's capabilities and extract keywords for what they can handle.

Agent Name: {agent.name}
Agent Role: {agent.role}
System Prompt:
{agent.system_prompt}

Instructions:
1. Extract 3-7 specific keywords/topics this agent can handle
2. Be specific (e.g., "flight booking", "hotel recommendations", not just "travel")
3. Focus on actionable capabilities
4. Return ONLY a JSON array of keywords

Example: ["flight booking", "airline recommendations", "seat selection"]

Your response (JSON array only):"""
        
        try:
            response = await generate_text(
                system_prompt="You extract capability keywords from agent descriptions. Respond ONLY with a JSON array.",
                user_input=prompt,
                model="gemini-2.5-flash",
                temperature=0.1,
                api_key=api_key
            )
            
            # Parse response
            response = response.strip()
            if response.startswith("```json"):
                response = response.split("```json")[1].split("```")[0].strip()
            elif response.startswith("```"):
                response = response.split("```")[1].split("```")[0].strip()
            
            capabilities = json.loads(response)
            
            if not isinstance(capabilities, list):
                logger.warning("capability_analysis_invalid_format", agent_id=agent.id, response=response)
                # Fallback to role-based
                return [agent.role.lower()]
            
            logger.info("capability_analysis_success", agent_id=agent.id, capabilities=capabilities)
            return capabilities
            
        except Exception as e:
            logger.error("capability_analysis_error", agent_id=agent.id, error=str(e))
            # Fallback to role-based
            return [agent.role.lower()]
    
    def _load_children(self, parent_id: str, session_id: Optional[str]) -> List[AgentModel]:
        """Load child agents."""
        query = self.db.query(AgentModel).filter(AgentModel.parent_id == parent_id)
        if session_id:
            query = query.filter(AgentModel.session_id == session_id)
        return query.all()
    
    def clear_cache(self):
        """Clear capability cache (useful when agents change)."""
        self.cache.clear()
        logger.info("capability_cache_cleared")
    
    def print_capability_tree(self, capability: AgentCapability, indent: int = 0):
        """Print capability tree for debugging."""
        prefix = "  " * indent
        caps_str = ", ".join(capability.can_handle)
        print(f"{prefix}├─ {capability.agent_name} (depth={capability.depth}): [{caps_str}]")
        for child in capability.children:
            self.print_capability_tree(child, indent + 1)

