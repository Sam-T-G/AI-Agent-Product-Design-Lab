"""
Recursive delegation engine for multi-level agent communication.
"""
from typing import List, Dict, Optional, AsyncGenerator
from sqlalchemy.orm import Session
import asyncio

from db.schemas import AgentModel
from core.delegation import (
    DelegationRequest, DelegationResponse, DelegationStatus,
    AgentCapability, CircuitBreaker, ResponseAggregator
)
from core.gemini_client import generate_streaming
from core.logging import get_logger

logger = get_logger("recursive_delegator")


class RecursiveDelegator:
    """
    Handles recursive delegation with parallel branch exploration.
    
    Any agent can delegate to its children, who can delegate to their children, etc.
    """
    
    def __init__(self, db: Session, api_key: str):
        self.db = db
        self.api_key = api_key
        self.circuit_breaker = CircuitBreaker()
        self.active_requests: Dict[str, DelegationRequest] = {}
    
    async def delegate_recursive(
        self,
        agent: AgentModel,
        request: DelegationRequest,
        capability_map: AgentCapability
    ) -> AsyncGenerator[Dict, None]:
        """
        Recursively delegate a request, trying agent first, then children.
        
        Yields events for streaming to frontend.
        Final event has type "delegation_response" with the DelegationResponse.
        """
        yield {
            "type": "log",
            "agent_id": agent.id,
            "data": f"[{agent.name}] Received delegation request"
        }
        
        # Validation checks
        if request.has_cycle():
            yield {
                "type": "log",
                "agent_id": agent.id,
                "data": f"⚠️ [{agent.name}] Cycle detected in path: {request.path}"
            }
            yield {
                "type": "delegation_response",
                "agent_id": agent.id,
                "response": DelegationResponse(
                    request_id=request.request_id,
                    responding_agent_id=agent.id,
                    status=DelegationStatus.ERROR,
                    error_message=f"Cycle detected: {request.path}"
                )
            }
            return
        
        if request.exceeds_depth():
            yield {
                "type": "log",
                "agent_id": agent.id,
                "data": f"⚠️ [{agent.name}] Max depth exceeded ({request.max_hops} hops)"
            }
            yield {
                "type": "delegation_response",
                "agent_id": agent.id,
                "response": DelegationResponse(
                    request_id=request.request_id,
                    responding_agent_id=agent.id,
                    status=DelegationStatus.ERROR,
                    error_message=f"Max depth exceeded: {request.max_hops} hops"
                )
            }
            return
        
        if request.is_expired():
            yield {
                "type": "log",
                "agent_id": agent.id,
                "data": f"⚠️ [{agent.name}] Request timeout ({request.timeout}s)"
            }
            yield {
                "type": "delegation_response",
                "agent_id": agent.id,
                "response": DelegationResponse(
                    request_id=request.request_id,
                    responding_agent_id=agent.id,
                    status=DelegationStatus.TIMEOUT,
                    error_message=f"Timeout after {request.timeout}s"
                )
            }
            return
        
        # Check circuit breaker
        if not self.circuit_breaker.should_try(agent.id):
            yield {
                "type": "log",
                "agent_id": agent.id,
                "data": f"⚠️ [{agent.name}] Circuit breaker open, skipping"
            }
            yield {
                "type": "delegation_response",
                "agent_id": agent.id,
                "response": DelegationResponse(
                    request_id=request.request_id,
                    responding_agent_id=agent.id,
                    status=DelegationStatus.ERROR,
                    error_message="Circuit breaker open"
                )
            }
            return
        
        # Track active request
        self.active_requests[request.request_id] = request
        
        try:
            # Phase 1: Try to handle directly
            yield {
                "type": "log",
                "agent_id": agent.id,
                "data": f"🤔 [{agent.name}] Analyzing if I can handle this..."
            }
            
            can_handle = await self._check_can_handle(agent, request)
            
            if can_handle:
                # Execute directly
                yield {
                    "type": "log",
                    "agent_id": agent.id,
                    "data": f"✓ [{agent.name}] I can handle this directly"
                }
                
                response = await self._execute_agent_for_request(agent, request)
                
                async for event in response["events"]:
                    yield event
                
                final_response = response["response"]
                
                if final_response.is_successful():
                    self.circuit_breaker.record_success(agent.id)
                else:
                    self.circuit_breaker.record_failure(agent.id)
                
                yield {
                    "type": "delegation_response",
                    "agent_id": agent.id,
                    "response": final_response
                }
                return
            
            # Phase 2: Can't handle directly - try children
            yield {
                "type": "log",
                "agent_id": agent.id,
                "data": f"🔍 [{agent.name}] Can't handle directly, checking children..."
            }
            
            children = self._load_children(agent.id, request.context.get("session_id"))
            
            if not children:
                # Leaf node - can't help
                yield {
                    "type": "log",
                    "agent_id": agent.id,
                    "data": f"❌ [{agent.name}] No children available, cannot fulfill"
                }
                
                self.circuit_breaker.record_failure(agent.id)
                
                yield {
                    "type": "delegation_response",
                    "agent_id": agent.id,
                    "response": DelegationResponse(
                        request_id=request.request_id,
                        responding_agent_id=agent.id,
                        status=DelegationStatus.UNABLE,
                        result=f"{agent.name} cannot handle this request and has no children to delegate to",
                        path=request.path
                    )
                }
                return
            
            # Phase 3: Delegate to children in PARALLEL
            yield {
                "type": "log",
                "agent_id": agent.id,
                "data": f"👥 [{agent.name}] Delegating to {len(children)} children in parallel..."
            }
            
            # Create delegation requests for each child
            child_requests = [
                request.forward_to(child.id)
                for child in children
            ]
            
            # Execute all children in parallel
            child_results = await self._delegate_to_children_parallel(
                children,
                child_requests,
                capability_map
            )
            
            # Stream all child events
            for result in child_results:
                for event in result["events"]:
                    yield event
            
            # Aggregate responses
            child_responses = [r["response"] for r in child_results]
            
            yield {
                "type": "log",
                "agent_id": agent.id,
                "data": f"📊 [{agent.name}] Received {len(child_responses)} responses from children"
            }
            
            # Check if any child fulfilled
            fulfilled = [r for r in child_responses if r.is_successful()]
            
            if fulfilled:
                yield {
                    "type": "log",
                    "agent_id": agent.id,
                    "data": f"✅ [{agent.name}] {len(fulfilled)} child(ren) fulfilled the request"
                }
                
                # Use best response
                final_response = ResponseAggregator.resolve_conflicts(child_responses)
                
                self.circuit_breaker.record_success(agent.id)
                
                yield {
                    "type": "delegation_response",
                    "agent_id": agent.id,
                    "response": final_response
                }
                return
            
            # No child fulfilled
            yield {
                "type": "log",
                "agent_id": agent.id,
                "data": f"❌ [{agent.name}] No children could fulfill the request"
            }
            
            self.circuit_breaker.record_failure(agent.id)
            
            yield {
                "type": "delegation_response",
                "agent_id": agent.id,
                "response": DelegationResponse(
                    request_id=request.request_id,
                    responding_agent_id=agent.id,
                    status=DelegationStatus.UNABLE,
                    result=f"{agent.name} and all children unable to fulfill request",
                    child_responses=child_responses,
                    path=request.path
                )
            }
            return
            
        except Exception as e:
            logger.error("delegation_error", agent_id=agent.id, error=str(e), exc_info=True)
            
            yield {
                "type": "log",
                "agent_id": agent.id,
                "data": f"💥 [{agent.name}] Error: {str(e)}"
            }
            
            self.circuit_breaker.record_failure(agent.id)
            
            yield {
                "type": "delegation_response",
                "agent_id": agent.id,
                "response": DelegationResponse(
                    request_id=request.request_id,
                    responding_agent_id=agent.id,
                    status=DelegationStatus.ERROR,
                    error_message=str(e),
                    path=request.path
                )
            }
            return
        
        finally:
            # Clean up active request
            if request.request_id in self.active_requests:
                del self.active_requests[request.request_id]
    
    async def _check_can_handle(self, agent: AgentModel, request: DelegationRequest) -> bool:
        """
        Check if agent can handle request directly.
        
        Uses LLM to analyze agent's capabilities vs request.
        """
        prompt = f"""Can this agent handle the following request directly?

Agent: {agent.name}
Role: {agent.role}
Capabilities: {agent.system_prompt[:500]}

Request: {request.task}

Respond with ONLY "YES" or "NO".
- YES if the agent can handle this directly
- NO if they need to delegate to specialists"""
        
        try:
            response = await generate_text(
                system_prompt="You determine if an agent can handle a request. Respond ONLY with YES or NO.",
                user_input=prompt,
                model="gemini-2.5-flash",
                temperature=0.1,
                api_key=self.api_key
            )
            
            can_handle = "YES" in response.upper()
            
            logger.info(
                "can_handle_check",
                agent_id=agent.id,
                can_handle=can_handle,
                response=response.strip()
            )
            
            return can_handle
            
        except Exception as e:
            logger.error("can_handle_error", agent_id=agent.id, error=str(e))
            # Default to trying
            return True
    
    async def _execute_agent_for_request(
        self,
        agent: AgentModel,
        request: DelegationRequest
    ) -> Dict:
        """
        Execute agent to fulfill a request.
        
        Returns dict with events and final response.
        """
        events = []
        full_output = ""
        
        # Build prompt
        prompt = f"""Task: {request.task}

Context: {request.context}

Provide a complete, detailed response."""
        
        try:
            # Get model and temperature
            model = agent.parameters.get("model", "gemini-2.5-flash") if agent.parameters else "gemini-2.5-flash"
            temperature = agent.parameters.get("temperature", 0.7) if agent.parameters else 0.7
            
            # Stream generation
            async for chunk in generate_streaming(
                system_prompt=agent.system_prompt,
                user_input=prompt,
                model=model,
                temperature=temperature,
                api_key=self.api_key
            ):
                full_output += chunk
                events.append({
                    "type": "output_chunk",
                    "agent_id": agent.id,
                    "data": chunk
                })
            
            # Final output
            events.append({
                "type": "output",
                "agent_id": agent.id,
                "data": full_output
            })
            
            response = DelegationResponse(
                request_id=request.request_id,
                responding_agent_id=agent.id,
                status=DelegationStatus.FULFILLED,
                result=full_output,
                confidence=0.8,
                path=request.path
            )
            
            return {"events": events, "response": response}
            
        except Exception as e:
            logger.error("agent_execution_error", agent_id=agent.id, error=str(e))
            
            events.append({
                "type": "error",
                "agent_id": agent.id,
                "data": str(e)
            })
            
            response = DelegationResponse(
                request_id=request.request_id,
                responding_agent_id=agent.id,
                status=DelegationStatus.ERROR,
                error_message=str(e),
                path=request.path
            )
            
            return {"events": events, "response": response}
    
    async def _delegate_to_children_parallel(
        self,
        children: List[AgentModel],
        requests: List[DelegationRequest],
        capability_map: AgentCapability
    ) -> List[Dict]:
        """
        Delegate to multiple children in parallel.
        
        Returns list of results, each containing events and response.
        """
        async def delegate_to_child(child: AgentModel, request: DelegationRequest) -> Dict:
            events = []
            async for event in self.delegate_recursive(child, request, capability_map):
                events.append(event)
            
            # Last event should contain the response
            # For now, create a simple response
            return {
                "events": events,
                "response": DelegationResponse(
                    request_id=request.request_id,
                    responding_agent_id=child.id,
                    status=DelegationStatus.UNABLE,  # Placeholder
                    result="Child response"
                )
            }
        
        tasks = [
            delegate_to_child(child, request)
            for child, request in zip(children, requests)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("child_delegation_error", child_id=children[i].id, error=str(result))
                final_results.append({
                    "events": [{
                        "type": "error",
                        "agent_id": children[i].id,
                        "data": str(result)
                    }],
                    "response": DelegationResponse(
                        request_id=requests[i].request_id,
                        responding_agent_id=children[i].id,
                        status=DelegationStatus.ERROR,
                        error_message=str(result)
                    )
                })
            else:
                final_results.append(result)
        
        return final_results
    
    def _load_children(self, parent_id: str, session_id: Optional[str]) -> List[AgentModel]:
        """Load child agents."""
        query = self.db.query(AgentModel).filter(AgentModel.parent_id == parent_id)
        if session_id:
            query = query.filter(AgentModel.session_id == session_id)
        return query.all()

