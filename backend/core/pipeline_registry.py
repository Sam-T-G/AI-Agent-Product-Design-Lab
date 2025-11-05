"""In-memory registry for agent pipeline awareness and capabilities."""
from __future__ import annotations

from typing import Dict, List, Optional, Set
import re

from sqlalchemy.orm import Session

from db.schemas import AgentModel
from core.logging import get_logger


logger = get_logger("pipeline_registry")


class PipelineRegistry:
    """Caches agent topology and lightweight capability metadata.

    - Builds a parent->children graph
    - Extracts simple capability keywords per agent from role, system prompt, tools and features
    - Provides relevance checks to help parents decide which children to invoke
    """

    _instance: Optional["PipelineRegistry"] = None

    def __init__(self) -> None:
        self.id_to_agent: Dict[str, AgentModel] = {}
        self.parent_to_children: Dict[str, List[str]] = {}
        self.capability_terms_by_agent: Dict[str, Set[str]] = {}

    @classmethod
    def instance(cls) -> "PipelineRegistry":
        if cls._instance is None:
            cls._instance = PipelineRegistry()
        return cls._instance

    def refresh(self, db: Session) -> None:
        """Rebuild registry from database."""
        agents: List[AgentModel] = db.query(AgentModel).all()
        self.id_to_agent = {a.id: a for a in agents}
        self.parent_to_children = {}
        for agent in agents:
            if agent.parent_id:
                self.parent_to_children.setdefault(agent.parent_id, []).append(agent.id)
        # Ensure keys for all agents exist
        for agent in agents:
            self.parent_to_children.setdefault(agent.id, [])

        # Build capability term sets
        self.capability_terms_by_agent = {}
        for agent in agents:
            terms: Set[str] = set()
            # Role and system prompt keywords
            terms.update(self._tokenize(agent.role))
            terms.update(self._tokenize(agent.system_prompt))
            # Tools
            for tool in (agent.tools or []):
                name = tool.get("name") if isinstance(tool, dict) else None
                if name:
                    terms.update(self._tokenize(name))
            # Photo features
            for feat in (agent.photo_injection_features or []):
                terms.update(self._tokenize(str(feat)))

            # Keep only alpha-ish tokens with length >= 3
            filtered = {t for t in terms if len(t) >= 3 and re.match(r"^[a-zA-Z0-9_-]+$", t)}
            self.capability_terms_by_agent[agent.id] = filtered

        logger.info(
            "pipeline_registry_refreshed",
            total_agents=len(self.id_to_agent),
            total_edges=sum(len(v) for v in self.parent_to_children.values()),
        )

    def get_children(self, parent_id: str) -> List[str]:
        return list(self.parent_to_children.get(parent_id, []))

    def get_graph_from_root(self, root_id: str) -> Dict[str, AgentModel]:
        graph: Dict[str, AgentModel] = {}
        if root_id not in self.id_to_agent:
            return graph
        def dfs(aid: str) -> None:
            if aid in graph:
                return
            agent = self.id_to_agent.get(aid)
            if not agent:
                return
            graph[aid] = agent
            for cid in self.parent_to_children.get(aid, []):
                dfs(cid)
        dfs(root_id)
        return graph

    def select_relevant_children(self, parent_id: str, context_text: str, fallback_all_if_empty: bool = True) -> List[str]:
        """Heuristically select relevant children based on keyword intersection.

        If no child passes the threshold and fallback is True, return all children to avoid dead-ends.
        """
        children = self.get_children(parent_id)
        if not children:
            return []
        context_terms = self._tokenize(context_text)
        scores: List[tuple[str, int]] = []
        for cid in children:
            agent_terms = self.capability_terms_by_agent.get(cid, set())
            score = len(agent_terms.intersection(context_terms))
            scores.append((cid, score))
        # Keep children with score >= 1
        relevant = [cid for cid, s in scores if s >= 1]
        if not relevant and fallback_all_if_empty:
            return children
        return relevant

    @staticmethod
    def _tokenize(text: Optional[str]) -> Set[str]:
        if not text:
            return set()
        # Lowercase and split on non-word
        tokens = re.split(r"[^a-zA-Z0-9_-]+", text.lower())
        return {t for t in tokens if t}


