"""
In-memory cache for agent tree structure and capabilities.
Optimizes performance by avoiding repeated database queries and LLM capability analysis.
"""
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import asyncio

from db.schemas import AgentModel
from core.delegation import AgentCapability
from core.capability_discovery import CapabilityDiscovery
from core.logging import get_logger

logger = get_logger("agent_tree_cache")


@dataclass
class AgentTreeSnapshot:
    """
    Complete snapshot of agent tree structure and capabilities.
    Cached in memory for fast access.
    """
    session_id: str
    root_agent_id: str
    capability_map: AgentCapability
    agent_count: int
    max_depth: int
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    
    def update_access_time(self):
        """Update last accessed timestamp."""
        self.last_accessed = datetime.utcnow()
    
    def get_all_agent_ids(self) -> List[str]:
        """Get flat list of all agent IDs in tree."""
        ids = []
        
        def collect_ids(cap: AgentCapability):
            ids.append(cap.agent_id)
            for child in cap.children:
                collect_ids(child)
        
        collect_ids(self.capability_map)
        return ids
    
    def find_agent_capability(self, agent_id: str) -> Optional[AgentCapability]:
        """Find capability info for specific agent."""
        return self.capability_map.find_agent(agent_id)


class AgentTreeCache:
    """
    Global cache for agent tree structures and capabilities.
    
    Optimizations:
    - Caches full tree structure per session
    - Caches LLM-analyzed capabilities
    - Lazy loading (build on first access)
    - Auto-invalidation on agent changes
    - Memory-efficient (only active sessions)
    """
    
    def __init__(self):
        self._cache: Dict[str, AgentTreeSnapshot] = {}
        self._lock = asyncio.Lock()
        self._invalidation_timestamps: Dict[str, datetime] = {}
    
    async def get_or_build(
        self,
        session_id: str,
        root_agent_id: str,
        db,
        api_key: str,
        force_rebuild: bool = False
    ) -> AgentTreeSnapshot:
        """
        Get cached tree snapshot or build if not exists.
        
        Args:
            session_id: Session ID
            root_agent_id: Root agent of tree
            db: Database session
            api_key: Gemini API key for capability analysis
            force_rebuild: Force rebuild even if cached
            
        Returns:
            Complete tree snapshot with capabilities
        """
        cache_key = f"{session_id}_{root_agent_id}"
        
        async with self._lock:
            # Check if invalidated
            if cache_key in self._invalidation_timestamps:
                if cache_key in self._cache:
                    snapshot = self._cache[cache_key]
                    if snapshot.created_at < self._invalidation_timestamps[cache_key]:
                        logger.info("cache_invalidated", cache_key=cache_key)
                        del self._cache[cache_key]
            
            # Return cached if exists and not force rebuild
            if cache_key in self._cache and not force_rebuild:
                snapshot = self._cache[cache_key]
                snapshot.update_access_time()
                logger.info("cache_hit", 
                    cache_key=cache_key,
                    agent_count=snapshot.agent_count,
                    max_depth=snapshot.max_depth
                )
                return snapshot
            
            # Build new snapshot
            logger.info("cache_miss_building", cache_key=cache_key)
            snapshot = await self._build_snapshot(
                session_id, root_agent_id, db, api_key
            )
            
            # Cache it
            self._cache[cache_key] = snapshot
            
            logger.info("cache_built",
                cache_key=cache_key,
                agent_count=snapshot.agent_count,
                max_depth=snapshot.max_depth,
                all_agents=snapshot.get_all_agent_ids()
            )
            
            return snapshot
    
    async def _build_snapshot(
        self,
        session_id: str,
        root_agent_id: str,
        db,
        api_key: str
    ) -> AgentTreeSnapshot:
        """Build complete tree snapshot with capability discovery."""
        # Load root agent
        root_agent = db.query(AgentModel).filter(
            AgentModel.id == root_agent_id,
            AgentModel.session_id == session_id
        ).first()
        
        if not root_agent:
            raise ValueError(f"Root agent {root_agent_id} not found")
        
        # Discover capabilities recursively
        discovery = CapabilityDiscovery(db)
        capability_map = await discovery.discover_capabilities(
            root_agent, api_key, depth=0, session_id=session_id
        )
        
        # Count agents and depth
        agent_count = self._count_agents(capability_map)
        max_depth = self._calculate_max_depth(capability_map)
        
        # Create snapshot
        snapshot = AgentTreeSnapshot(
            session_id=session_id,
            root_agent_id=root_agent_id,
            capability_map=capability_map,
            agent_count=agent_count,
            max_depth=max_depth
        )
        
        return snapshot
    
    def _count_agents(self, cap: AgentCapability) -> int:
        """Count total agents in tree."""
        count = 1
        for child in cap.children:
            count += self._count_agents(child)
        return count
    
    def _calculate_max_depth(self, cap: AgentCapability, current_depth: int = 0) -> int:
        """Calculate maximum depth of capability tree."""
        if not cap.children:
            return current_depth
        return max(self._calculate_max_depth(child, current_depth + 1) for child in cap.children)
    
    def invalidate(self, session_id: str, root_agent_id: Optional[str] = None):
        """
        Mark cache as invalid (will rebuild on next access).
        
        Args:
            session_id: Session to invalidate
            root_agent_id: Specific root, or None to invalidate all in session
        """
        if root_agent_id:
            cache_key = f"{session_id}_{root_agent_id}"
            self._invalidation_timestamps[cache_key] = datetime.utcnow()
            logger.info("cache_invalidated_specific", cache_key=cache_key)
        else:
            # Invalidate all for session
            for cache_key in list(self._cache.keys()):
                if cache_key.startswith(f"{session_id}_"):
                    self._invalidation_timestamps[cache_key] = datetime.utcnow()
                    logger.info("cache_invalidated_session", session_id=session_id)
    
    def clear_session(self, session_id: str):
        """Remove all cache entries for a session."""
        keys_to_remove = [
            k for k in self._cache.keys() 
            if k.startswith(f"{session_id}_")
        ]
        for key in keys_to_remove:
            del self._cache[key]
            if key in self._invalidation_timestamps:
                del self._invalidation_timestamps[key]
        
        logger.info("cache_cleared_session", session_id=session_id, removed_count=len(keys_to_remove))
    
    def clear_all(self):
        """Clear entire cache."""
        count = len(self._cache)
        self._cache.clear()
        self._invalidation_timestamps.clear()
        logger.info("cache_cleared_all", removed_count=count)
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        return {
            "cached_trees": len(self._cache),
            "invalidation_pending": len(self._invalidation_timestamps),
            "sessions": len(set(k.split("_")[0] for k in self._cache.keys())),
            "total_agents": sum(s.agent_count for s in self._cache.values()),
        }


# Global cache instance
global_agent_tree_cache = AgentTreeCache()


def get_agent_tree_cache() -> AgentTreeCache:
    """Get global agent tree cache instance."""
    return global_agent_tree_cache

