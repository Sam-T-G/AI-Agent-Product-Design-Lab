# Agent Graph Execution

## Overview

The orchestrator executes agent graphs by traversing the parent/child hierarchy, invoking Gemini for each agent, and managing the flow of data between agents.

## Execution Flow

### High-Level Process

1. User initiates run from root agent
2. Orchestrator loads agent graph from database
3. Traverse graph (topological sort or BFS/DFS)
4. Execute each agent with Gemini
5. Pass outputs to child agents
6. Stream logs and outputs to frontend
7. Return final results

## Graph Traversal Strategies

### Strategy 1: Topological Sort (Sequential)

Execute agents in dependency order, ensuring parents complete before children.

```python
def execute_topological(root_agent_id: str, graph: dict) -> dict:
    """Execute agents in topological order."""
    # Build dependency graph
    dependencies = build_dependencies(graph)
    
    # Topological sort
    execution_order = topological_sort(dependencies)
    
    results = {}
    for agent_id in execution_order:
        agent = graph[agent_id]
        parent_outputs = get_parent_outputs(agent_id, results, graph)
        
        # Execute agent
        output = execute_agent(agent, parent_outputs)
        results[agent_id] = output
    
    return results
```

### Strategy 2: Breadth-First Search (Level-based)

Execute all agents at the same level in parallel, then move to next level.

```python
def execute_bfs(root_agent_id: str, graph: dict) -> dict:
    """Execute agents level by level."""
    levels = build_levels(root_agent_id, graph)
    results = {}
    
    for level in levels:
        # Execute all agents in this level
        level_results = execute_level_parallel(level, graph, results)
        results.update(level_results)
    
    return results
```

### Strategy 3: Event-Driven (Future)

More flexible, agents trigger child execution based on conditions.

## Execution Implementation

### Core Orchestrator

```python
# backend/core/orchestrator.py
from typing import Dict, List, Optional, AsyncGenerator
from core.models import Agent, Run, RunLog
from core.gemini_client import generate_text, generate_streaming
import asyncio


class AgentOrchestrator:
    def __init__(self, db_session):
        self.db = db_session
        self.active_runs: Dict[str, Run] = {}
    
    async def execute_run(
        self,
        run_id: str,
        root_agent_id: str,
        input_data: Dict,
        stream: bool = False,
    ) -> AsyncGenerator[Dict, None]:
        """
        Execute a run from root agent.
        
        Yields execution events for streaming.
        """
        # Load agent graph
        graph = await self._load_agent_graph(root_agent_id)
        
        # Initialize run
        run = await self._initialize_run(run_id, root_agent_id, input_data)
        self.active_runs[run_id] = run
        
        try:
            # Execute graph
            if stream:
                async for event in self._execute_graph_streaming(
                    graph, root_agent_id, input_data, run
                ):
                    yield event
            else:
                results = await self._execute_graph(graph, root_agent_id, input_data, run)
                yield {"type": "completed", "results": results}
        
        except Exception as e:
            await self._handle_error(run_id, str(e))
            yield {"type": "error", "error": str(e)}
        
        finally:
            await self._finalize_run(run_id)
    
    async def _execute_graph(
        self,
        graph: Dict[str, Agent],
        root_id: str,
        input_data: Dict,
        run: Run,
    ) -> Dict[str, str]:
        """Execute graph synchronously."""
        results = {}
        execution_order = self._get_execution_order(graph, root_id)
        
        for agent_id in execution_order:
            agent = graph[agent_id]
            
            # Get input from parent or root input
            agent_input = self._prepare_agent_input(
                agent_id, agent, graph, results, input_data
            )
            
            # Log execution start
            await self._log(run.id, agent_id, f"Executing agent: {agent.name}")
            
            # Execute agent
            output = await self._execute_agent(agent, agent_input)
            results[agent_id] = output
            
            # Log completion
            await self._log(run.id, agent_id, f"Completed: {agent.name}")
        
        return results
    
    async def _execute_graph_streaming(
        self,
        graph: Dict[str, Agent],
        root_id: str,
        input_data: Dict,
        run: Run,
    ) -> AsyncGenerator[Dict, None]:
        """Execute graph with streaming output."""
        results = {}
        execution_order = self._get_execution_order(graph, root_id)
        
        for agent_id in execution_order:
            agent = graph[agent_id]
            agent_input = self._prepare_agent_input(
                agent_id, agent, graph, results, input_data
            )
            
            yield {"type": "status", "agent_id": agent_id, "status": "running"}
            
            # Stream agent execution
            full_output = ""
            async for chunk in self._execute_agent_streaming(agent, agent_input):
                full_output += chunk
                yield {
                    "type": "output_chunk",
                    "agent_id": agent_id,
                    "chunk": chunk,
                }
            
            results[agent_id] = full_output
            yield {"type": "output", "agent_id": agent_id, "output": full_output}
            yield {"type": "status", "agent_id": agent_id, "status": "completed"}
    
    async def _execute_agent(
        self,
        agent: Agent,
        input_data: Dict,
    ) -> str:
        """Execute a single agent."""
        # Prepare prompt context
        context = self._build_context(agent, input_data)
        
        # Generate response
        output = generate_text(
            system_prompt=agent.system_prompt,
            user_input=context,
            model=agent.parameters.get("model", "gemini-1.5-pro"),
            temperature=agent.parameters.get("temperature", 0.7),
            max_tokens=agent.parameters.get("max_tokens"),
        )
        
        return output
    
    async def _execute_agent_streaming(
        self,
        agent: Agent,
        input_data: Dict,
    ) -> AsyncGenerator[str, None]:
        """Execute agent with streaming."""
        context = self._build_context(agent, input_data)
        
        for chunk in generate_streaming(
            system_prompt=agent.system_prompt,
            user_input=context,
            model=agent.parameters.get("model", "gemini-1.5-pro"),
            temperature=agent.parameters.get("temperature", 0.7),
        ):
            yield chunk
    
    def _prepare_agent_input(
        self,
        agent_id: str,
        agent: Agent,
        graph: Dict[str, Agent],
        results: Dict[str, str],
        root_input: Dict,
    ) -> str:
        """Prepare input for agent from parent outputs or root input."""
        if agent.parent_id is None:
            # Root agent gets root input
            return str(root_input)
        
        # Child agent gets parent's output
        parent_output = results.get(agent.parent_id, "")
        return parent_output
    
    def _build_context(self, agent: Agent, input_data: str) -> str:
        """Build context string for agent execution."""
        context = f"Input: {input_data}"
        
        # Add tool context if agent has tools
        if agent.tools:
            tool_descriptions = [f"- {tool.name}" for tool in agent.tools]
            context += f"\n\nAvailable tools: {', '.join(tool_descriptions)}"
        
        return context
    
    def _get_execution_order(
        self,
        graph: Dict[str, Agent],
        root_id: str,
    ) -> List[str]:
        """Get execution order using topological sort."""
        # Build dependency map
        dependencies = {}
        for agent_id, agent in graph.items():
            if agent.parent_id:
                dependencies.setdefault(agent_id, []).append(agent.parent_id)
        
        # Topological sort
        visited = set()
        result = []
        
        def visit(node_id: str):
            if node_id in visited:
                return
            visited.add(node_id)
            for dep in dependencies.get(node_id, []):
                visit(dep)
            result.append(node_id)
        
        visit(root_id)
        return result
    
    async def _load_agent_graph(self, root_agent_id: str) -> Dict[str, Agent]:
        """Load entire agent graph starting from root."""
        # Load root agent
        root = await self.db.get_agent(root_agent_id)
        graph = {root_agent_id: root}
        
        # Recursively load children
        await self._load_children(root_agent_id, graph)
        
        return graph
    
    async def _load_children(self, parent_id: str, graph: Dict[str, Agent]):
        """Recursively load child agents."""
        children = await self.db.get_agent_children(parent_id)
        for child in children:
            graph[child.id] = child
            await self._load_children(child.id, graph)
    
    async def _log(self, run_id: str, agent_id: str, message: str):
        """Log execution event."""
        # Save to database
        await self.db.add_run_log(run_id, agent_id, message)
        
        # Could also emit via WebSocket/SSE here
```

## Error Handling

### Retry Logic

```python
async def _execute_agent_with_retry(
    self,
    agent: Agent,
    input_data: Dict,
    max_retries: int = 3,
) -> str:
    """Execute agent with retry logic."""
    for attempt in range(max_retries):
        try:
            return await self._execute_agent(agent, input_data)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### Circuit Breaker

Prevent cascading failures:

```python
class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def call(self, func, *args, **kwargs):
        if self.state == "open":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half-open"
            else:
                raise Exception("Circuit breaker is open")
        
        try:
            result = func(*args, **kwargs)
            if self.state == "half-open":
                self.state = "closed"
                self.failures = 0
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()
            if self.failures >= self.failure_threshold:
                self.state = "open"
            raise
```

## Parallel Execution

For agents at the same level:

```python
async def execute_level_parallel(
    self,
    agent_ids: List[str],
    graph: Dict[str, Agent],
    parent_results: Dict[str, str],
    input_data: Dict,
) -> Dict[str, str]:
    """Execute multiple agents in parallel."""
    tasks = [
        self._execute_agent(
            graph[agent_id],
            self._prepare_agent_input(agent_id, graph[agent_id], graph, parent_results, input_data)
        )
        for agent_id in agent_ids
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return {
        agent_id: result if not isinstance(result, Exception) else str(result)
        for agent_id, result in zip(agent_ids, results)
    }
```

## Performance Optimization

1. **Caching**: Cache agent definitions and prompts
2. **Connection pooling**: Reuse Gemini API connections
3. **Batch processing**: Batch similar agent executions
4. **Lazy loading**: Load agents only when needed
5. **Streaming**: Stream outputs for better UX

