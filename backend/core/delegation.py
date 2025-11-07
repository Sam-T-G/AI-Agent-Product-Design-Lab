"""
Multi-level delegation system for recursive agent communication.
"""
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid
import time


class DelegationStatus(Enum):
    """Status of a delegation request/response."""
    FULFILLED = "fulfilled"
    UNABLE = "unable"
    PARTIAL = "partial"
    TIMEOUT = "timeout"
    ERROR = "error"
    NEEDS_USER_INPUT = "needs_user_input"


@dataclass
class DelegationRequest:
    """
    A request that can travel through agent hierarchy.
    
    Tracks path to prevent cycles and enforce depth limits.
    """
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    original_agent_id: str = ""
    current_agent_id: str = ""
    task: str = ""
    context: Dict = field(default_factory=dict)
    path: List[str] = field(default_factory=list)  # Agents visited
    attempts: int = 0
    max_hops: int = 10
    timeout: float = 30.0  # seconds
    created_at: float = field(default_factory=time.time)
    
    def forward_to(self, agent_id: str) -> 'DelegationRequest':
        """Create a new request forwarded to another agent."""
        return DelegationRequest(
            request_id=self.request_id,
            original_agent_id=self.original_agent_id,
            current_agent_id=agent_id,
            task=self.task,
            context=self.context,
            path=self.path + [agent_id],
            attempts=self.attempts + 1,
            max_hops=self.max_hops,
            timeout=self.timeout,
            created_at=self.created_at
        )
    
    def has_cycle(self) -> bool:
        """Check if request has visited same agent twice."""
        return len(self.path) != len(set(self.path))
    
    def is_expired(self) -> bool:
        """Check if request has exceeded timeout."""
        return (time.time() - self.created_at) > self.timeout
    
    def exceeds_depth(self) -> bool:
        """Check if request has exceeded max hops."""
        return self.attempts >= self.max_hops


@dataclass
class DelegationResponse:
    """
    Response from an agent regarding a delegation request.
    """
    request_id: str
    responding_agent_id: str
    status: DelegationStatus
    result: str = ""
    confidence: float = 0.0  # 0.0-1.0
    path: List[str] = field(default_factory=list)  # Path taken to fulfill
    child_responses: List['DelegationResponse'] = field(default_factory=list)
    error_message: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    
    def is_successful(self) -> bool:
        """Check if response successfully fulfilled request."""
        return self.status == DelegationStatus.FULFILLED
    
    def is_failure(self) -> bool:
        """Check if response failed to fulfill."""
        return self.status in [DelegationStatus.UNABLE, DelegationStatus.ERROR, DelegationStatus.TIMEOUT]


@dataclass
class AgentCapability:
    """
    Describes what an agent can handle.
    """
    agent_id: str
    agent_name: str
    can_handle: List[str] = field(default_factory=list)  # Keywords/topics
    confidence: float = 0.5  # How well it handles these
    depth: int = 0  # Distance from root (0 = root, 1 = child, 2 = grandchild, etc.)
    children: List['AgentCapability'] = field(default_factory=list)
    
    def get_all_capabilities(self) -> List[str]:
        """Get all capabilities including from children."""
        caps = self.can_handle.copy()
        for child in self.children:
            caps.extend(child.get_all_capabilities())
        return list(set(caps))  # Deduplicate
    
    def find_agent(self, agent_id: str) -> Optional['AgentCapability']:
        """Find a specific agent in the capability tree."""
        if self.agent_id == agent_id:
            return self
        for child in self.children:
            result = child.find_agent(agent_id)
            if result:
                return result
        return None
    
    def get_max_depth(self) -> int:
        """Get maximum depth of capability tree."""
        if not self.children:
            return self.depth
        return max(child.get_max_depth() for child in self.children)


class CircuitBreaker:
    """
    Prevents repeatedly trying agents that are failing.
    """
    def __init__(self, failure_threshold: int = 3, timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures: Dict[str, int] = {}
        self.open_until: Dict[str, float] = {}
    
    def should_try(self, agent_id: str) -> bool:
        """Check if we should try this agent."""
        if agent_id in self.open_until:
            if time.time() < self.open_until[agent_id]:
                return False  # Circuit still open
            else:
                # Circuit timeout expired, reset
                del self.open_until[agent_id]
                self.failures[agent_id] = 0
        return True
    
    def record_success(self, agent_id: str):
        """Record successful execution."""
        if agent_id in self.failures:
            self.failures[agent_id] = max(0, self.failures[agent_id] - 1)
    
    def record_failure(self, agent_id: str):
        """Record failed execution."""
        self.failures[agent_id] = self.failures.get(agent_id, 0) + 1
        if self.failures[agent_id] >= self.failure_threshold:
            # Open circuit
            self.open_until[agent_id] = time.time() + self.timeout


class DelegationRouter:
    """
    Routes requests to the best agent based on capabilities.
    """
    
    @staticmethod
    def score_agent_for_task(task: str, capability: AgentCapability) -> float:
        """
        Score how well an agent can handle a task.
        
        Returns score from 0.0 (can't handle) to 1.0 (perfect match).
        """
        task_lower = task.lower()
        
        # Check keyword matches
        matches = sum(1 for keyword in capability.can_handle if keyword.lower() in task_lower)
        
        if matches == 0:
            return 0.0
        
        # Score = (matches / total_keywords) * confidence * depth_penalty
        keyword_score = matches / max(len(capability.can_handle), 1)
        depth_penalty = 1.0 / (1.0 + capability.depth * 0.2)  # Prefer closer agents
        
        return keyword_score * capability.confidence * depth_penalty
    
    @staticmethod
    def find_best_agents(
        task: str,
        capability_map: AgentCapability,
        top_n: int = 3
    ) -> List[tuple[str, float]]:
        """
        Find the top N agents best suited for a task.
        
        Returns list of (agent_id, score) tuples.
        """
        scores = []
        
        def score_recursive(cap: AgentCapability):
            score = DelegationRouter.score_agent_for_task(task, cap)
            if score > 0:
                scores.append((cap.agent_id, score))
            for child in cap.children:
                score_recursive(child)
        
        score_recursive(capability_map)
        
        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        
        return scores[:top_n]
    
    @staticmethod
    def route_request(
        request: DelegationRequest,
        capability_map: AgentCapability
    ) -> Optional[str]:
        """
        Find the best agent to handle this request.
        
        Returns agent_id or None if no suitable agent found.
        """
        candidates = DelegationRouter.find_best_agents(request.task, capability_map, top_n=1)
        
        if not candidates:
            return None
        
        return candidates[0][0]  # Return best agent_id


class ResponseAggregator:
    """
    Aggregates responses from multiple agents.
    """
    
    @staticmethod
    def aggregate(responses: List[DelegationResponse]) -> DelegationResponse:
        """
        Aggregate multiple responses into one.
        
        Priority:
        1. If any fulfilled, return best fulfilled
        2. If all partial, combine partials
        3. If all unable, aggregate failures
        """
        if not responses:
            return DelegationResponse(
                request_id="",
                responding_agent_id="",
                status=DelegationStatus.ERROR,
                error_message="No responses received"
            )
        
        # Separate by status
        fulfilled = [r for r in responses if r.status == DelegationStatus.FULFILLED]
        partial = [r for r in responses if r.status == DelegationStatus.PARTIAL]
        unable = [r for r in responses if r.is_failure()]
        
        # If any fulfilled, return best one
        if fulfilled:
            best = max(fulfilled, key=lambda r: r.confidence)
            return best
        
        # If have partials, combine them
        if partial:
            combined_result = "\n\n".join([r.result for r in partial if r.result])
            avg_confidence = sum(r.confidence for r in partial) / len(partial)
            
            return DelegationResponse(
                request_id=partial[0].request_id,
                responding_agent_id="aggregated",
                status=DelegationStatus.PARTIAL,
                result=combined_result,
                confidence=avg_confidence,
                child_responses=partial
            )
        
        # All unable - aggregate failure messages
        failure_messages = [r.error_message or r.result for r in unable if r.error_message or r.result]
        
        return DelegationResponse(
            request_id=unable[0].request_id if unable else "",
            responding_agent_id="aggregated",
            status=DelegationStatus.UNABLE,
            result="All agents unable to fulfill request",
            error_message="; ".join(failure_messages),
            child_responses=unable
        )
    
    @staticmethod
    def resolve_conflicts(responses: List[DelegationResponse]) -> DelegationResponse:
        """
        When multiple agents fulfill, choose the best one.
        """
        fulfilled = [r for r in responses if r.status == DelegationStatus.FULFILLED]
        
        if not fulfilled:
            return ResponseAggregator.aggregate(responses)
        
        if len(fulfilled) == 1:
            return fulfilled[0]
        
        # Multiple fulfilled - score by confidence and path length
        def score(r: DelegationResponse) -> float:
            path_penalty = len(r.path) * 0.05
            return r.confidence - path_penalty
        
        best = max(fulfilled, key=score)
        return best

