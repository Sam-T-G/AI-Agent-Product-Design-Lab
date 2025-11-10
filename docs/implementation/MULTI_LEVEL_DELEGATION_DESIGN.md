# Multi-Level Agent Delegation Architecture

## Problem Analysis

### Current Issues
1. **Two-level works, multi-level fails**: Root → Child works, but Root → Child → Grandchild breaks
2. **No recursive delegation**: Intermediate agents can't delegate to their children
3. **No capability routing**: No way to find which branch can fulfill a request
4. **Premature failure**: System fails if one branch can't help, even if another could
5. **No failure propagation**: Leaf nodes can't report "unable to fulfill" back up

### Root Cause
The current system treats delegation as a one-time, single-level operation. It doesn't support:
- Agents delegating to their own children
- Multi-hop request routing
- Distributed capability discovery
- Failure recovery across branches

## New Architecture: Recursive Delegation with Capability Discovery

### Core Concepts

#### 1. Agent Capabilities
Every agent declares what it can do:
```python
class AgentCapability:
    agent_id: str
    can_handle: List[str]  # ["flights", "hotels", "restaurants"]
    confidence: float  # 0.0-1.0 how well it can handle
```

#### 2. Request Object
Explicit request that can travel through hierarchy:
```python
class DelegationRequest:
    request_id: str
    original_agent_id: str  # Who initiated
    current_agent_id: str  # Who has it now
    task: str
    context: Dict
    path: List[str]  # Agents it's traveled through
    attempts: int
    max_hops: int = 10  # Prevent infinite loops
```

#### 3. Response Object
Explicit response that bubbles up:
```python
class DelegationResponse:
    request_id: str
    responding_agent_id: str
    status: str  # "fulfilled", "unable", "partial"
    result: str
    confidence: float
    path: List[str]  # Path it took to fulfill
```

### Execution Flow

```
┌─────────────────────────────────────────────────────────┐
│ Phase 1: Capability Discovery (Recursive)              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Root Agent receives task                              │
│      ↓                                                  │
│  Ask: "Can I handle this directly?"                    │
│      ├─ Yes → Execute and return                       │
│      └─ No  → Query children's capabilities            │
│           ↓                                             │
│      Children recursively report capabilities          │
│      (Each child asks their children, etc.)            │
│           ↓                                             │
│      Build capability map of entire tree               │
│                                                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Phase 2: Intelligent Routing                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Analyze task → Extract subtasks                       │
│      ↓                                                  │
│  Match subtasks to capability map                      │
│      ↓                                                  │
│  Create DelegationRequest for each subtask             │
│      ↓                                                  │
│  Route to best-matching agent (may be grandchild)      │
│                                                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Phase 3: Recursive Delegation                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Agent receives DelegationRequest                      │
│      ↓                                                  │
│  Check: Can I handle this?                             │
│      ├─ Yes → Execute → Return DelegationResponse     │
│      └─ No  → Do I have children who might?           │
│           ├─ Yes → Forward to children (recursive)    │
│           │    ↓                                        │
│           │   Wait for responses from all children     │
│           │    ↓                                        │
│           │   If any fulfilled → Return best response  │
│           │   If all unable → Aggregate & return unable│
│           │                                             │
│           └─ No children → Return "unable" response    │
│                                                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Phase 4: Response Aggregation                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Parent waits for all child responses                  │
│      ↓                                                  │
│  Classify responses:                                   │
│      - fulfilled: [Response1, Response2]               │
│      - unable: [Response3]                             │
│      - partial: [Response4]                            │
│      ↓                                                  │
│  If any fulfilled → Use best one(s)                    │
│  If all unable → Try next branch or report up          │
│  If partial → Combine or request more info             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Key Features

#### 1. Recursive Capability Discovery
```python
async def discover_capabilities(agent: AgentModel) -> CapabilityMap:
    """Recursively discover what agent and all descendants can do."""
    
    # Agent's own capabilities (from system_prompt analysis)
    own_capabilities = await analyze_agent_capabilities(agent)
    
    # Get children's capabilities recursively
    children = get_children(agent.id)
    child_capabilities = []
    
    for child in children:
        child_cap = await discover_capabilities(child)  # RECURSIVE
        child_capabilities.append(child_cap)
    
    # Build complete capability map
    return CapabilityMap(
        agent_id=agent.id,
        direct_capabilities=own_capabilities,
        child_capabilities=child_capabilities,
        total_depth=max([c.total_depth for c in child_capabilities]) + 1
    )
```

#### 2. Smart Request Routing
```python
async def route_request(
    request: DelegationRequest,
    capability_map: CapabilityMap
) -> List[str]:
    """Find best path to agent that can fulfill request."""
    
    # Score each agent in tree for this request
    scores = {}
    
    def score_agent(agent_id, capabilities, depth):
        # Higher score = better match
        match_score = calculate_match(request.task, capabilities)
        depth_penalty = depth * 0.1  # Prefer closer agents
        scores[agent_id] = match_score - depth_penalty
    
    # Recursively score all agents
    traverse_capability_map(capability_map, score_agent)
    
    # Return sorted list of candidate agents
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

#### 3. Parallel Branch Exploration
```python
async def delegate_with_fallback(
    agent: AgentModel,
    request: DelegationRequest
) -> DelegationResponse:
    """Try to fulfill request, with fallback to children."""
    
    # Try self first
    can_handle = await check_can_handle(agent, request)
    
    if can_handle:
        result = await execute_agent(agent, request)
        return DelegationResponse(
            status="fulfilled",
            result=result,
            confidence=0.9
        )
    
    # Can't handle - try children in PARALLEL
    children = get_children(agent.id)
    
    if not children:
        # Leaf node - can't help
        return DelegationResponse(
            status="unable",
            result=f"{agent.name} cannot fulfill this request",
            confidence=0.0
        )
    
    # Try all children in parallel
    tasks = [
        delegate_with_fallback(child, request)  # RECURSIVE
        for child in children
    ]
    responses = await asyncio.gather(*tasks)
    
    # Aggregate responses
    fulfilled = [r for r in responses if r.status == "fulfilled"]
    
    if fulfilled:
        # At least one child fulfilled - return best one
        best = max(fulfilled, key=lambda r: r.confidence)
        return best
    
    # All children unable - aggregate their failures
    return DelegationResponse(
        status="unable",
        result=f"{agent.name} and children cannot fulfill request",
        confidence=0.0,
        child_responses=responses  # Include for debugging
    )
```

#### 4. Timeout & Circuit Breaker
```python
class DelegationTimeout:
    """Prevent infinite waiting."""
    
    async def delegate_with_timeout(
        agent: AgentModel,
        request: DelegationRequest,
        timeout: float = 30.0
    ) -> DelegationResponse:
        try:
            response = await asyncio.wait_for(
                delegate_with_fallback(agent, request),
                timeout=timeout
            )
            return response
        except asyncio.TimeoutError:
            return DelegationResponse(
                status="unable",
                result=f"Timeout after {timeout}s",
                confidence=0.0
            )

class CircuitBreaker:
    """Prevent hammering failing branches."""
    
    def __init__(self):
        self.failures = defaultdict(int)
        self.open_until = {}
    
    def should_try(self, agent_id: str) -> bool:
        # If circuit open, don't try
        if agent_id in self.open_until:
            if time.time() < self.open_until[agent_id]:
                return False
        return True
    
    def record_failure(self, agent_id: str):
        self.failures[agent_id] += 1
        if self.failures[agent_id] >= 3:
            # Open circuit for 60 seconds
            self.open_until[agent_id] = time.time() + 60
```

### Edge Cases Handled

#### 1. Circular Dependencies
```python
def validate_no_cycles(request: DelegationRequest) -> bool:
    """Ensure request hasn't visited same agent twice."""
    if len(request.path) != len(set(request.path)):
        raise CircularDelegationError(
            f"Cycle detected: {request.path}"
        )
    return True
```

#### 2. Deep Nesting Limits
```python
def check_depth_limit(request: DelegationRequest) -> bool:
    """Prevent too-deep delegation chains."""
    if request.attempts >= request.max_hops:
        raise MaxDepthExceededError(
            f"Request exceeded {request.max_hops} hops"
        )
    return True
```

#### 3. Conflicting Responses
```python
def resolve_conflicts(responses: List[DelegationResponse]) -> DelegationResponse:
    """When multiple agents fulfill, choose best."""
    
    fulfilled = [r for r in responses if r.status == "fulfilled"]
    
    if len(fulfilled) == 1:
        return fulfilled[0]
    
    if len(fulfilled) > 1:
        # Score by confidence and path length (shorter is better)
        scored = [
            (r, r.confidence - len(r.path) * 0.05)
            for r in fulfilled
        ]
        best = max(scored, key=lambda x: x[1])
        return best[0]
    
    # No fulfilled responses
    return DelegationResponse(status="unable", ...)
```

#### 4. Partial Fulfillment
```python
def handle_partial_responses(responses: List[DelegationResponse]) -> DelegationResponse:
    """Combine partial responses into complete answer."""
    
    fulfilled = [r for r in responses if r.status == "fulfilled"]
    partial = [r for r in responses if r.status == "partial"]
    
    if fulfilled and partial:
        # Combine fulfilled + partial
        combined_result = synthesize_results(fulfilled + partial)
        return DelegationResponse(
            status="fulfilled",
            result=combined_result,
            confidence=min([r.confidence for r in fulfilled])
        )
    
    if partial:
        # Only partial - ask user for more info
        return DelegationResponse(
            status="needs_user_input",
            result="Need more information to complete",
            partial_results=partial
        )
```

### Implementation Priority

1. **Phase 1**: Capability discovery system
2. **Phase 2**: DelegationRequest/Response objects
3. **Phase 3**: Recursive delegation logic
4. **Phase 4**: Parallel branch exploration
5. **Phase 5**: Response aggregation
6. **Phase 6**: Edge case handling (timeouts, circuits, cycles)
7. **Phase 7**: Testing with 3+ level hierarchies

### Example: Travel Planning (3 Levels)

```
Root: Head Travel Agent
  ├─ Flight Agent (can handle: flights, airlines)
  ├─ Hotel Agent (can handle: accommodations, hotels)
  └─ Experiences Agent (can handle: activities, restaurants)
      ├─ Restaurant Agent (can handle: dining, food)
      ├─ Tours Agent (can handle: tours, guides)
      └─ Events Agent (can handle: shows, concerts)

User: "Plan a trip to Italy with great food"

Flow:
1. Root analyzes: Need flights, hotels, AND food experiences
2. Capability discovery finds:
   - Flight Agent (direct child)
   - Hotel Agent (direct child)
   - Restaurant Agent (grandchild via Experiences Agent)
3. Root creates 3 DelegationRequests:
   Request A → Flight Agent (direct)
   Request B → Hotel Agent (direct)
   Request C → Experiences Agent (who forwards to Restaurant Agent)
4. All execute in parallel
5. Responses bubble back up:
   - Flight Agent: "fulfilled" (direct)
   - Hotel Agent: "fulfilled" (direct)
   - Restaurant Agent: "fulfilled" (via Experiences Agent)
6. Root synthesizes all 3 responses into final answer
```

### Benefits

1. **Modularity**: Each agent only knows about direct children
2. **Scalability**: Works with arbitrary depth
3. **Robustness**: Handles failures at any level
4. **Parallelism**: Multiple branches explored simultaneously
5. **Flexibility**: Easy to add/remove agents
6. **Debuggability**: Full path tracking for every request

