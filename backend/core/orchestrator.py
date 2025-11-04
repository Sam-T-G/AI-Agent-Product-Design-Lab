"""Agent graph execution orchestrator."""
from typing import Dict, List, Optional, AsyncGenerator, Set
from sqlalchemy.orm import Session
from datetime import datetime
import asyncio

from db.schemas import AgentModel, RunModel
from core.models import RunLog
from core.logging import get_logger
from core.gemini_client import generate_text, generate_streaming

logger = get_logger("orchestrator")


class AgentOrchestrator:
    """Orchestrates multi-agent graph execution."""
    
    def __init__(self, db: Session):
        self.db = db
        self.active_runs: Dict[str, RunModel] = {}
    
    async def execute_run(
        self,
        run_id: str,
        root_agent_id: str,
        input_data: Dict,
    ) -> AsyncGenerator[Dict, None]:
        """
        Execute a run from root agent.
        
        Yields execution events for streaming.
        """
        # Load run
        run = self.db.query(RunModel).filter(RunModel.id == run_id).first()
        if not run:
            logger.error("run_not_found", run_id=run_id)
            yield {"type": "error", "data": f"Run {run_id} not found"}
            return
        
        # Update run status
        run.status = "running"
        run.started_at = datetime.utcnow()
        self.db.commit()
        
        try:
            # Load agent graph
            graph = self._load_agent_graph(root_agent_id)
            
            yield {"type": "status", "agent_id": root_agent_id, "data": "running"}
            yield {"type": "log", "agent_id": root_agent_id, "data": f"Starting hierarchical execution from root agent"}
            
            # Log the input data we received
            yield {
                "type": "log",
                "agent_id": root_agent_id,
                "data": f"[DEBUG] Received input_data type: {type(input_data)}, keys: {list(input_data.keys()) if isinstance(input_data, dict) else 'not a dict'}",
            }
            if isinstance(input_data, dict):
                for key, value in input_data.items():
                    if isinstance(value, str):
                        yield {
                            "type": "log",
                            "agent_id": root_agent_id,
                            "data": f"[DEBUG] input_data['{key}'] = {value[:200]}...",
                        }
            
            results = {}
            # Track child-to-parent communications
            child_messages: Dict[str, List[str]] = {}  # parent_id -> list of child messages
            # Track which agents have been executed in this iteration
            executed_agents: Set[str] = set()
            
            # Execute hierarchically: root first, then each level of children
            # Get hierarchical levels (breadth-first traversal)
            levels = self._get_hierarchical_levels(graph, root_agent_id)
            
            yield {
                "type": "log",
                "agent_id": root_agent_id,
                "data": f"[DEBUG] Agent hierarchy levels: {len(levels)} levels, Level 0: {[graph[aid].name for aid in levels[0]] if levels else 'empty'}",
            }
            
            # Maximum iterations for bidirectional communication
            max_iterations = 3
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                if iteration > 1:
                    yield {
                        "type": "log",
                        "agent_id": "",
                        "data": f"Starting communication iteration {iteration}",
                    }
                
                # Execute each level
                for level_num, level_agents in enumerate(levels):
                    yield {
                        "type": "log",
                        "agent_id": "",
                        "data": f"Executing level {level_num + 1} ({len(level_agents)} agent{'s' if len(level_agents) != 1 else ''})",
                    }
                    
                    # Debug: Log which agents are at this level
                    if level_num == 0:
                        root_agent_at_level = graph.get(level_agents[0] if level_agents else None)
                        if root_agent_at_level:
                            yield {
                                "type": "log",
                                "agent_id": level_agents[0] if level_agents else "",
                                "data": f"[DEBUG] Level 0 agent: {root_agent_at_level.name} (ID: {level_agents[0] if level_agents else 'none'}), root_agent_id: {root_agent_id}",
                            }
                    
                    # Execute all agents at this level IN PARALLEL
                    if len(level_agents) == 1:
                        # Single agent - execute sequentially
                        agent_id = level_agents[0]
                        agent = graph[agent_id]
                        
                        yield {
                            "type": "log",
                            "agent_id": agent_id,
                            "data": f"[DEBUG] Processing single agent at level {level_num}: {agent.name} (ID: {agent_id})",
                        }
                        
                        # Prepare input based on hierarchy and child messages
                        if level_num == 0:
                            # Root agent - ensure it gets the initial user input
                            root_input = self._prepare_root_input(input_data, child_messages.get(root_agent_id))
                            agent_input = root_input
                            
                            # Log input for root agent with full details
                            yield {
                                "type": "log",
                                "agent_id": agent_id,
                                "data": f"[DEBUG] Root agent ({agent.name}) input (iteration {iteration}):\n{agent_input[:800]}...",
                            }
                            yield {
                                "type": "log",
                                "agent_id": agent_id,
                                "data": f"[DEBUG] Root agent input_data keys: {list(input_data.keys()) if isinstance(input_data, dict) else 'not a dict'}",
                            }
                            if isinstance(input_data, dict):
                                yield {
                                    "type": "log",
                                    "agent_id": agent_id,
                                    "data": f"[DEBUG] Root agent prompt: {input_data.get('prompt', 'N/A')[:200]}...",
                                }
                        else:
                            parent_output = results.get(agent.parent_id, "")
                            # Include any child messages this parent has received
                            parent_messages = child_messages.get(agent.parent_id, [])
                            
                            # Log what we're getting from parent
                            parent_agent = graph.get(agent.parent_id)
                            parent_name = parent_agent.name if parent_agent else "Unknown"
                            
                            yield {
                                "type": "log",
                                "agent_id": agent_id,
                                "data": f"[DEBUG] {agent.name} parent ({parent_name}) output length: {len(parent_output)} chars",
                            }
                            if not parent_output or len(parent_output.strip()) < 5:
                                yield {
                                    "type": "log",
                                    "agent_id": agent_id,
                                    "data": f"[WARNING] {agent.name} received empty output from {parent_name}! Parent may not have executed properly.",
                                }
                            
                            # Build agent input from parent output. If parent output is empty,
                            # fall back to seeding first-level children with the root input;
                            # deeper levels will wait until their parent has produced output.
                            if not parent_output or len(parent_output.strip()) < 5:
                                if level_num == 1:
                                    seeded = self._prepare_root_input(input_data)
                                    agent_input = self._prepare_agent_input(seeded, parent_messages)
                                else:
                                    agent_input = ""
                            else:
                                agent_input = self._prepare_agent_input(parent_output, parent_messages)
                            # Log input for child agent
                            yield {
                                "type": "log",
                                "agent_id": agent_id,
                                "data": f"[DEBUG] {agent.name} input from {parent_name}:\n{agent_input[:400]}...",
                            }
                            if parent_messages:
                                yield {
                                    "type": "log",
                                    "agent_id": agent_id,
                                    "data": f"[DEBUG] Child messages to {parent_name}: {parent_messages}",
                                }
                        
                        # Log execution start
                        yield {
                            "type": "log",
                            "agent_id": agent_id,
                            "data": f"Executing {agent.name} (Level {level_num + 1})",
                        }
                        
                        # Execute agent with Gemini
                        output = ""
                        if not agent_input or len(agent_input.strip()) < 5:
                            yield {
                                "type": "log",
                                "agent_id": agent_id,
                                "data": f"[WARNING] {agent.name} has empty or very short input! Input: '{agent_input}'",
                            }
                            # Skip executing children at deeper levels until their parent
                            # produces a meaningful output to avoid redundant empty calls
                            if level_num > 1:
                                results[agent_id] = ""
                                run.output[agent_id] = ""
                                self.db.commit()
                                executed_agents.add(agent_id)
                                continue
                        else:
                            # Log that we're about to call Gemini
                            yield {
                                "type": "log",
                                "agent_id": agent_id,
                                "data": f"[DEBUG] Calling Gemini for {agent.name} with input length: {len(agent_input)}",
                            }
                        
                        try:
                            chunk_count = 0
                            async for chunk in self._execute_agent_streaming(agent, agent_input):
                                output += chunk
                                chunk_count += 1
                                # Always stream root agent outputs to user (even in subsequent iterations)
                                if level_num == 0:
                                    yield {
                                        "type": "output_chunk",
                                        "agent_id": agent_id,
                                        "data": chunk,
                                    }
                            
                            yield {
                                "type": "log",
                                "agent_id": agent_id,
                                "data": f"[DEBUG] {agent.name} received {chunk_count} chunks from Gemini",
                            }
                        except Exception as e:
                            logger.error(f"Error executing {agent.name}: {e}")
                            yield {
                                "type": "log",
                                "agent_id": agent_id,
                                "data": f"[ERROR] Failed to execute {agent.name}: {str(e)}",
                            }
                            output = f"Error: {str(e)}"
                        
                        results[agent_id] = output
                        run.output[agent_id] = output
                        self.db.commit()
                        
                        # Log output for debugging
                        yield {
                            "type": "log",
                            "agent_id": agent_id,
                            "data": f"[DEBUG] {agent.name} output ({len(output)} chars):\n{output[:500]}...",
                        }
                        
                        # For root agent, ensure we have output before proceeding
                        if level_num == 0 and (not output or len(output.strip()) < 10):
                            yield {
                                "type": "log",
                                "agent_id": agent_id,
                                "data": f"[ERROR] Root agent {agent.name} produced no meaningful output! This will cause children to fail.",
                            }
                        
                        # Always show root agent outputs to user (even in subsequent iterations)
                        if level_num == 0:
                            yield {
                                "type": "output",
                                "agent_id": agent_id,
                                "data": output,
                            }
                            yield {
                                "type": "log",
                                "agent_id": agent_id,
                                "data": f"[ROOT OUTPUT] {agent.name} final output streamed to user",
                            }
                        
                        yield {
                            "type": "log",
                            "agent_id": agent_id,
                            "data": f"Completed: {agent.name}",
                        }
                        
                        executed_agents.add(agent_id)
                else:
                    # Multiple agents - execute in parallel
                    # Log execution start for all agents
                    for agent_id in level_agents:
                        agent = graph[agent_id]
                        yield {
                            "type": "log",
                            "agent_id": agent_id,
                            "data": f"Executing {agent.name} (Level {level_num + 1})",
                        }
                    
                    # Create tasks for parallel execution
                    async def execute_and_collect_events(agent_id: str):
                        """Execute agent and return events plus output."""
                        agent = graph[agent_id]
                        
                        # Prepare input based on hierarchy and child messages
                        if level_num == 0:
                            agent_input = self._prepare_root_input(input_data, child_messages.get(agent_id))
                            # Log will be handled outside parallel execution
                        else:
                            parent_output = results.get(agent.parent_id, "")
                            # Include any child messages this parent has received
                            parent_messages = child_messages.get(agent.parent_id, [])
                            # Fallback seeding for first-level children; skip deeper levels
                            if not parent_output or len(parent_output.strip()) < 5:
                                if level_num == 1:
                                    seeded = self._prepare_root_input(input_data)
                                    agent_input = self._prepare_agent_input(seeded, parent_messages)
                                else:
                                    agent_input = ""
                            else:
                                agent_input = self._prepare_agent_input(parent_output, parent_messages)
                        
                        # Collect streaming chunks
                        chunks = []
                        if not agent_input or len(agent_input.strip()) < 5:
                            # Skip execution for deeper levels with no usable input
                            return {
                                "agent_id": agent_id,
                                "agent_name": agent.name,
                                "output": "",
                                "chunks": [],
                            }
                        async for chunk in self._execute_agent_streaming(agent, agent_input):
                            chunks.append(chunk)
                        
                        output = "".join(chunks)
                        results[agent_id] = output
                        run.output[agent_id] = output
                        self.db.commit()
                        
                        return {
                            "agent_id": agent_id,
                            "agent_name": agent.name,
                            "output": output,
                            "chunks": chunks,
                        }
                    
                    # Log inputs for parallel agents
                    if level_num == 0:
                        for agent_id in level_agents:
                            agent = graph[agent_id]
                            agent_input = self._prepare_root_input(input_data, child_messages.get(agent_id))
                            yield {
                                "type": "log",
                                "agent_id": agent_id,
                                "data": f"[DEBUG] Root agent input (iteration {iteration}):\n{agent_input[:500]}...",
                            }
                    else:
                        for agent_id in level_agents:
                            agent = graph[agent_id]
                            parent_output = results.get(agent.parent_id, "")
                            parent_messages = child_messages.get(agent.parent_id, [])
                            agent_input = self._prepare_agent_input(parent_output, parent_messages)
                            parent_agent = graph.get(agent.parent_id)
                            parent_name = parent_agent.name if parent_agent else "Unknown"
                            yield {
                                "type": "log",
                                "agent_id": agent_id,
                                "data": f"[DEBUG] {agent.name} input from {parent_name}:\n{agent_input[:300]}...",
                            }
                            if parent_messages:
                                yield {
                                    "type": "log",
                                    "agent_id": agent_id,
                                    "data": f"[DEBUG] Child messages to {parent_name}: {parent_messages}",
                        }
                    
                    # Execute all agents in parallel
                    tasks = [execute_and_collect_events(agent_id) for agent_id in level_agents]
                    agent_results = await asyncio.gather(*tasks)
                    
                    # Yield events for each agent as they complete
                    for result in agent_results:
                        agent_id = result["agent_id"]
                        agent_name = result["agent_name"]
                        output = result["output"]
                        chunks = result["chunks"]
                        
                        # Log output for debugging
                        yield {
                            "type": "log",
                            "agent_id": agent_id,
                            "data": f"[DEBUG] {agent_name} output ({len(output)} chars):\n{output[:500]}...",
                        }
                        
                        # Always stream root agent outputs (even in subsequent iterations)
                        if level_num == 0:
                            for chunk in chunks:
                                yield {
                                    "type": "output_chunk",
                                    "agent_id": agent_id,
                                    "data": chunk,
                                }
                            
                            # Stream complete output (only for root agent)
                            yield {
                                "type": "output",
                                "agent_id": agent_id,
                                "data": output,
                            }
                            yield {
                                "type": "log",
                                "agent_id": agent_id,
                                "data": f"[ROOT OUTPUT] {agent_name} final output streamed to user",
                            }
                        
                        executed_agents.add(agent_id)
                        
                        # Log completion
                        yield {
                            "type": "log",
                            "agent_id": agent_id,
                            "data": f"Completed: {agent_name}",
                        }
                
                # After all levels execute, allow children to communicate back to parents
                if iteration < max_iterations:
                    yield {
                        "type": "log",
                        "agent_id": "",
                        "data": f"[DEBUG] Collecting child messages after iteration {iteration}...",
                    }
                    
                    new_messages = await self._collect_child_messages(
                        graph, levels, results, executed_agents
                    )
                    
                    # Log collected messages
                    if new_messages:
                        for parent_id, messages in new_messages.items():
                            parent_agent = graph.get(parent_id)
                            parent_name = parent_agent.name if parent_agent else "Unknown"
                            yield {
                                "type": "log",
                                "agent_id": parent_id,
                                "data": f"[DEBUG] Collected {len(messages)} message(s) for {parent_name}: {messages}",
                            }
                    else:
                        yield {
                            "type": "log",
                            "agent_id": "",
                            "data": "[DEBUG] No child messages collected - ending communication cycles",
                        }
                    
                    # If no new messages, we can stop iterating
                    if not new_messages:
                        break
                    
                    # Merge new messages into child_messages
                    for parent_id, messages in new_messages.items():
                        if parent_id not in child_messages:
                            child_messages[parent_id] = []
                        child_messages[parent_id].extend(messages)
                    
                    yield {
                        "type": "log",
                        "agent_id": "",
                        "data": f"[DEBUG] Starting next iteration - parents will receive child messages",
                    }
                    
                    # Clear executed agents for next iteration (except root)
                    executed_agents = {root_agent_id}
            
            # Ensure final root agent output is always displayed
            final_root_output = results.get(root_agent_id, "")
            if final_root_output:
                yield {
                    "type": "log",
                    "agent_id": root_agent_id,
                    "data": f"[FINAL OUTPUT] Streaming final root agent output ({len(final_root_output)} chars)",
                }
                yield {
                    "type": "output",
                    "agent_id": root_agent_id,
                    "data": final_root_output,
                }
            else:
                yield {
                    "type": "log",
                    "agent_id": root_agent_id,
                    "data": "[WARNING] Root agent output is empty - no output to display",
                        }
            
            # Mark run as completed
            run.status = "completed"
            run.finished_at = datetime.utcnow()
            self.db.commit()
            
            yield {"type": "status", "agent_id": root_agent_id, "data": "completed"}
            
        except Exception as e:
            logger.error("run_execution_error", run_id=run_id, error=str(e))
            run.status = "failed"
            run.error = str(e)
            run.finished_at = datetime.utcnow()
            self.db.commit()
            yield {"type": "error", "agent_id": root_agent_id, "data": str(e)}
    
    def _load_agent_graph(self, root_agent_id: str) -> Dict[str, AgentModel]:
        """Load entire agent graph starting from root."""
        graph = {}
        
        # Load root agent
        root = self.db.query(AgentModel).filter(AgentModel.id == root_agent_id).first()
        if not root:
            raise ValueError(f"Root agent {root_agent_id} not found")
        
        graph[root_agent_id] = root
        
        # Recursively load children
        self._load_children(root_agent_id, graph)
        
        return graph
    
    def _load_children(self, parent_id: str, graph: Dict[str, AgentModel]):
        """Recursively load child agents."""
        children = self.db.query(AgentModel).filter(AgentModel.parent_id == parent_id).all()
        for child in children:
            graph[child.id] = child
            self._load_children(child.id, graph)
    
    def _get_hierarchical_levels(
        self,
        graph: Dict[str, AgentModel],
        root_id: str,
    ) -> List[List[str]]:
        """
        Get agents organized by hierarchical levels.
        Returns list of levels, where each level is a list of agent IDs.
        Level 0 is the root, level 1 is direct children, etc.
        """
        levels = []
        current_level = [root_id]
        visited = {root_id}
        
        while current_level:
            levels.append(current_level)
            next_level = []
            
            # Find all children of current level agents
            for agent_id in current_level:
                agent = graph[agent_id]
                # Find direct children
                children = [
                    child_id for child_id, child in graph.items()
                    if child.parent_id == agent_id and child_id not in visited
                ]
                for child_id in children:
                    visited.add(child_id)
                    next_level.append(child_id)
            
            current_level = next_level
        
        return levels
    
    def _prepare_root_input(self, root_input: Dict, child_messages: Optional[List[str]] = None) -> str:
        """Prepare input for root agent from user's injected prompt and child messages."""
        # Extract the user's prompt/task from input_data
        if isinstance(root_input, dict):
            # Try multiple keys that might contain the user's prompt
            prompt = (
                root_input.get("prompt") or 
                root_input.get("task") or 
                root_input.get("input") or
                root_input.get("message") or
                root_input.get("query")
            )
            
            if prompt:
                base_input = str(prompt).strip()
            else:
                # If no prompt/task found, try to extract from dict values
                # Look for the longest string value as it's likely the prompt
                string_values = [str(v) for v in root_input.values() if isinstance(v, (str, int, float))]
                if string_values:
                    # Use the longest string value as it's likely the main prompt
                    base_input = max(string_values, key=len).strip()
                else:
                    # Fallback: format the dict nicely
                    base_input = "\n".join([f"{k}: {v}" for k, v in root_input.items() if v])
        else:
            base_input = str(root_input).strip()
        
        # Ensure we have a meaningful input
        if not base_input or len(base_input.strip()) < 3:
            base_input = "Please process this request and delegate tasks to your child agents as needed."
        
        # Add child messages if any (these come from previous iterations)
        if child_messages:
            # Separate reports from questions
            reports = [msg for msg in child_messages if "[Report]" in msg]
            questions = [msg for msg in child_messages if "[Question]" in msg]
            
            if reports:
                # Child agents have completed their work - compile and organize
                reports_text = "\n\n".join(reports)
                base_input += f"\n\n=== WORK COMPLETED BY YOUR CHILD AGENTS ===\n{reports_text}"
                base_input += "\n\n=== YOUR TASK ===\n"
                base_input += "Your child agents have completed their research and provided you with their findings. "
                base_input += "Please compile, organize, and synthesize all of this information into a comprehensive, well-structured response for the user. "
                base_input += "Compartmentalize the information by category (e.g., flights, activities, timing, costs) and present organized findings. "
                base_input += "Make sure the final response is clear, actionable, and addresses the user's original request."
            
            if questions:
                # Child agents have questions - address them first
                questions_text = "\n\n".join(questions)
                base_input += f"\n\n=== QUESTIONS FROM YOUR CHILD AGENTS ===\n{questions_text}"
                base_input += "\n\nPlease address these questions and provide clear guidance to your child agents."
            
            if not reports and not questions:
                # Fallback: just show all messages
                messages_text = "\n\n".join(child_messages)
                base_input += f"\n\n=== MESSAGES FROM YOUR CHILD AGENTS ===\n{messages_text}"
                base_input += "\n\nPlease review these messages and respond appropriately."
        
        return base_input
    
    def _prepare_agent_input(self, parent_output: str, child_messages: Optional[List[str]] = None) -> str:
        """Prepare input for agent from parent output and child messages."""
        # Extract intent/goals from parent output instead of passing raw output
        input_text = self._extract_intent_from_parent(parent_output)
        
        # Add child messages if any (only for parents receiving child outputs)
        if child_messages:
            # Separate reports from questions
            reports = [msg for msg in child_messages if "[Report]" in msg]
            questions = [msg for msg in child_messages if "[Question]" in msg]
            
            if reports:
                reports_text = "\n\n".join(reports)
                input_text += f"\n\n=== WORK COMPLETED BY YOUR CHILD AGENTS ===\n{reports_text}"
                input_text += "\n\nPlease compile and organize this information into your final response."
            
            if questions:
                questions_text = "\n\n".join(questions)
                input_text += f"\n\n=== QUESTIONS FROM YOUR CHILD AGENTS ===\n{questions_text}"
                input_text += "\n\nPlease address these questions."
        
        return input_text
    
    def _extract_intent_from_parent(self, parent_output: str) -> str:
        """
        Extract actionable intent and goals from parent output.
        Modular system that works with any prompt structure by:
        1. Extracting key entities (locations, dates, numbers, etc.)
        2. Identifying action verbs and directives
        3. Building a structured task description
        4. Preserving context while focusing on actionable items
        """
        if not parent_output or len(parent_output.strip()) < 10:
            return parent_output
        
        import re
        
        # Step 1: Extract key entities (modular - works for any domain)
        entities = {
            "locations": [],
            "dates": [],
            "numbers": [],
            "keywords": [],
        }
        
        # Extract locations (common patterns: "to X", "in X", "at X", "X and Y")
        location_patterns = [
            r'\bto\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
            r'\bin\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
            r'\bat\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+and\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
        ]
        for pattern in location_patterns:
            matches = re.findall(pattern, parent_output)
            for match in matches:
                if isinstance(match, tuple):
                    entities["locations"].extend([m for m in match if m])
                else:
                    entities["locations"].append(match)
        
        # Extract dates (flexible date patterns)
        date_patterns = [
            r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}\b',
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            r'\b\d{4}-\d{2}-\d{2}\b',
            r'\b(spring|summer|fall|autumn|winter)\s+\d{4}\b',
        ]
        for pattern in date_patterns:
            entities["dates"].extend(re.findall(pattern, parent_output, re.IGNORECASE))
        
        # Extract numbers (prices, quantities, etc.)
        entities["numbers"] = re.findall(r'\$\d+(?:,\d{3})*(?:\.\d{2})?|\d+(?:,\d{3})*', parent_output)
        
        # Step 2: Extract action verbs and directives (domain-agnostic)
        action_indicators = [
            r'\b(?:please|can you|could you|I need|I want|help|find|search|get|compile|research|analyze|create|plan|book|schedule|recommend|look for|provide|give|show)\b',
        ]
        
        # Extract sentences containing action verbs
        sentences = re.split(r'[.!?]\s+', parent_output)
        action_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if any(re.search(pattern, sentence, re.IGNORECASE) for pattern in action_indicators):
                # Keep sentences that are directives or requests
                if len(sentence) > 10 and len(sentence) < 200:
                    action_sentences.append(sentence)
        
        # Step 3: Build structured intent (modular format)
        intent_parts = []
        
        # Add extracted entities
        if entities["locations"]:
            unique_locs = list(set([loc.strip() for loc in entities["locations"] if len(loc.strip()) > 2]))
            if unique_locs:
                intent_parts.append(f"Location(s): {', '.join(unique_locs[:5])}")
        
        if entities["dates"]:
            unique_dates = list(set(entities["dates"]))
            if unique_dates:
                intent_parts.append(f"Date(s): {', '.join(unique_dates[:3])}")
        
        if entities["numbers"]:
            intent_parts.append(f"Numbers mentioned: {', '.join(entities['numbers'][:3])}")
        
        # Step 4: Combine into structured task
        if intent_parts or action_sentences:
            task_description = ""
            
            # Add key information
            if intent_parts:
                task_description = "Key information from parent:\n" + "\n".join(intent_parts) + "\n\n"
            
            # Add action directives (most relevant first)
            if action_sentences:
                # Prioritize shorter, more direct sentences
                action_sentences.sort(key=len)
                task_description += "Task: " + ". ".join(action_sentences[:2]) + "\n\n"
            
            # Add context for clarity
            task_description += "Context: " + parent_output[:200] + ("..." if len(parent_output) > 200 else "")
            task_description += "\n\nUse the information above to complete your task. If you need clarification, ask your parent using [QUESTION: ...]"
            
            return task_description
        
        # Fallback: Smart summary that preserves intent
        # If output is long, create a focused summary
        if len(parent_output) > 300:
            # Take first and last sentences (often contain the most important info)
            all_sentences = re.split(r'[.!?]\s+', parent_output)
            if len(all_sentences) > 2:
                summary = all_sentences[0] + ". ... " + all_sentences[-1]
            else:
                summary = parent_output[:300]
            
            return f"Parent's request:\n{summary}...\n\nFull context: {parent_output[:200]}...\n\nTry to infer what action you should take from this context. If unclear, ask your parent using [QUESTION: ...]"
        
        # If output is already concise, pass it through
        return parent_output
    
    
    async def _execute_agent_with_events(
        self,
        agent: AgentModel,
        agent_id: str,
        level_num: int,
        results: Dict[str, str],
        input_data: Dict,
        run: RunModel,
    ) -> str:
        """Execute an agent and yield events, returning the output."""
        # Prepare input based on hierarchy
        if level_num == 0:
            agent_input = self._prepare_root_input(input_data)
        else:
            parent_output = results.get(agent.parent_id, "")
            agent_input = parent_output
        
        # Execute agent with Gemini
        output = ""
        async for chunk in self._execute_agent_streaming(agent, agent_input):
            output += chunk
        
        # Store result
        results[agent_id] = output
        run.output[agent_id] = output
        self.db.commit()
        
        return output
    
    async def _execute_agent_streaming(
        self,
        agent: AgentModel,
        input_data: str,
    ) -> AsyncGenerator[str, None]:
        """Execute agent with streaming output using Gemini."""
        # Get model and parameters from agent
        model = agent.parameters.get("model", "gemini-2.5-flash")
        temperature = agent.parameters.get("temperature", 0.7)
        max_tokens = agent.parameters.get("max_tokens", 1000)
        
        # Migrate old model names to new ones
        model_migration = {
            "gemini-1.5-pro": "gemini-2.5-flash",
            "gemini-1.0-pro": "gemini-2.5-flash",
            "gemini-pro": "gemini-2.5-flash",
        }
        if model in model_migration:
            logger.warning(
                "model_migration",
                old_model=model,
                new_model=model_migration[model],
                agent_id=agent.id,
            )
            model = model_migration[model]
            # Update agent parameters in database
            if agent.parameters:
                agent.parameters["model"] = model
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(agent, "parameters")  # Force SQLAlchemy to detect JSON change
                self.db.commit()
        
        # Build context
        context = self._build_context(agent, input_data)
        
        # Generate with streaming
        async for chunk in generate_streaming(
            system_prompt=agent.system_prompt,
            user_input=context,
            model=model,
            temperature=temperature,
        ):
            yield chunk
    
    async def _collect_child_messages(
        self,
        graph: Dict[str, AgentModel],
        levels: List[List[str]],
        results: Dict[str, str],
        executed_agents: Set[str],
    ) -> Dict[str, List[str]]:
        """
        Collect outputs from child agents to their parents.
        Children send their complete work outputs to parents, and optionally questions.
        Parents compile these outputs into organized final responses.
        """
        child_messages: Dict[str, List[str]] = {}
        
        # Process levels from bottom to top (reverse order)
        for level_num in range(len(levels) - 1, -1, -1):
            level_agents = levels[level_num]
            
            for agent_id in level_agents:
                if agent_id not in executed_agents:
                    continue
                
                agent = graph[agent_id]
                agent_output = results.get(agent_id, "")
                
                # If agent has a parent, send its complete output to parent
                if agent.parent_id and agent_output:
                    # Always send the complete output from child to parent
                    # This allows parent to compile all child work
                    if agent.parent_id not in child_messages:
                        child_messages[agent.parent_id] = []
                    
                    # Format child output for parent
                    child_output_message = f"[{agent.name} Report]:\n{agent_output}"
                    child_messages[agent.parent_id].append(child_output_message)
                    
                    logger.info(
                        "child_output_sent_to_parent",
                        child_id=agent_id,
                        child_name=agent.name,
                        parent_id=agent.parent_id,
                        output_length=len(agent_output),
                    )
                    
                    # Also check if child has a question/request (for clarification)
                    question = self._extract_child_message(agent_output)
                    if question and question != agent_output:
                        # If there's a specific question (not just the full output), add it separately
                        child_messages[agent.parent_id].append(
                            f"[{agent.name} Question]: {question}"
                        )
        
        return child_messages
    
    def _extract_child_message(self, output: str) -> Optional[str]:
        """
        Extract message/question from child agent output that should be sent to parent.
        Looks for explicit markers like [QUESTION], [REQUEST], or natural language patterns.
        """
        output = output.strip()
        if not output:
            return None
        
        # Look for explicit markers (highest priority)
        markers = [
            ("[QUESTION:", "]"),
            ("[REQUEST:", "]"),
            ("[MESSAGE:", "]"),
            ("[ASK:", "]"),
            ("Question for parent:", None),
            ("Request to parent:", None),
            ("Message to parent:", None),
            ("I need help:", None),
            ("Can you clarify:", None),
            ("Need clarification:", None),
        ]
        
        for marker, closing in markers:
            marker_lower = marker.lower()
            if marker_lower in output.lower():
                # Extract content after marker
                idx = output.lower().find(marker_lower)
                message = output[idx + len(marker):].strip()
                
                # Remove closing bracket if present
                if closing and message.startswith(closing):
                    message = message[len(closing):].strip()
                elif closing and closing in message:
                    # Find and remove closing bracket
                    closing_idx = message.find(closing)
                    message = message[:closing_idx].strip()
                
                # Clean up common prefixes
                if message.lower().startswith("to parent:"):
                    message = message[len("to parent:"):].strip()
                
                if message and len(message) > 5:  # Ensure meaningful message
                    return message
        
        # Look for question patterns in short outputs
        if len(output) < 300:
            # Check if it's a direct question
            question_indicators = ["?", "can you", "could you", "should I", "what", "how", "why", "when", "where"]
            if any(indicator in output.lower() for indicator in question_indicators):
                # Extract the question part (usually the last sentence)
                sentences = output.split(".")
                questions = [s.strip() + "?" for s in sentences if "?" in s]
                if questions:
                    return questions[-1].strip("?")
                return output
        
        # If no explicit marker found, return None (child doesn't need to communicate)
        return None
    
    def _build_context(self, agent: AgentModel, input_data: str) -> str:
        """Build context string for agent execution."""
        context = f"Input: {input_data}"
        
        # Add information about child agents if this agent has children
        children = self.db.query(AgentModel).filter(
            AgentModel.parent_id == agent.id
        ).all()
        
        if children:
            child_names = [child.name for child in children]
            context += f"\n\nYou have child agents that can help you: {', '.join(child_names)}"
            context += "\nYou can delegate tasks to them by providing clear instructions about what you need."
            context += "\nIMPORTANT: When delegating to child agents, be specific about what you want them to do."
            context += "\nExample: Instead of just passing along the full context, say 'Please find flights to [destination] for [dates]' or 'Search for activities in [location]'."
            context += "\n\nWhen your child agents complete their work, they will send you their complete findings as reports."
            context += "\nYour job is to compile, organize, and synthesize all their findings into a comprehensive, well-structured response."
            context += "\nCompartmentalize information by category and present organized findings to address the user's original request."
            context += "\nYour child agents may ask you questions using markers like [QUESTION: ...] or [REQUEST: ...]"
        
        # Add information about parent if this agent has one
        if agent.parent_id:
            parent = self.db.query(AgentModel).filter(AgentModel.id == agent.parent_id).first()
            if parent:
                context += f"\n\nYou are a child agent of {parent.name}."
                context += "\nYour parent has given you a task. Try to understand what they want you to do and proceed accordingly."
                context += "\nWhen you complete your work, provide a comprehensive report with your findings, research, and recommendations."
                context += "\nYour complete output will be sent back to your parent agent, who will compile all child agent reports into a final organized response."
                context += "\nIf the task is unclear or you need more information, you can ask your parent using:"
                context += "\n- [QUESTION: your question here]"
                context += "\n- [REQUEST: your request here]"
                context += "\n- [MESSAGE: your message here]"
                context += "\nHowever, try to infer what you can from the context and proceed with reasonable assumptions when possible."
                context += "\nProvide thorough, detailed work - your parent will organize and present it to the user."
        
        # Add tool context if agent has tools
        if agent.tools:
            tool_descriptions = [f"- {tool.get('name', 'unknown')}" for tool in agent.tools]
            context += f"\n\nAvailable tools: {', '.join(tool_descriptions)}"
        
        return context
    

