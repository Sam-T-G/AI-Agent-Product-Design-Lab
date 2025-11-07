"""
New message-based orchestrator with explicit communication and validation.
"""
from typing import Dict, List, Optional, AsyncGenerator
from sqlalchemy.orm import Session
from datetime import datetime
import asyncio

from db.schemas import RunModel, AgentModel
from core.messages import (
    Message, DelegateMessage, ReportMessage, QueryMessage, AnswerMessage,
    RequestUserInputMessage, UserResponseMessage, AgentMailbox, AgentState,
    MessageValidator, MessageType
)
from core.agent_selector import AgentSelector
from core.gemini_client import generate_streaming
from core.agent_tree_cache import get_agent_tree_cache
from core.logging import get_logger

logger = get_logger("orchestrator_v2")


class AgentExecutor:
    """Executes individual agents with their context."""
    
    def __init__(self, agent: AgentModel, api_key: str):
        self.agent = agent
        self.api_key = api_key
        self.mailbox = AgentMailbox(agent.id)
        
    async def execute(
        self,
        task: str,
        context: Optional[Dict] = None
    ) -> AsyncGenerator[Dict, None]:
        """
        Execute the agent with a given task.
        
        Yields events for streaming to frontend.
        """
        self.mailbox.set_state(AgentState.ANALYZING)
        yield {
            "type": "log",
            "agent_id": self.agent.id,
            "data": f"[{self.agent.name}] Analyzing task..."
        }
        
        # Build system prompt
        system_prompt = self._build_system_prompt(context)
        
        self.mailbox.set_state(AgentState.EXECUTING)
        yield {
            "type": "status",
            "agent_id": self.agent.id,
            "data": "executing"
        }
        
        try:
            # Get model and temperature from agent parameters
            model = self.agent.parameters.get("model", "gemini-2.5-flash") if self.agent.parameters else "gemini-2.5-flash"
            temperature = self.agent.parameters.get("temperature", 0.7) if self.agent.parameters else 0.7
            
            # Migrate old model names to new ones
            model_migration = {
                "gemini-1.5-pro": "gemini-2.5-pro",
                "gemini-1.5-flash": "gemini-2.5-flash",
                "gemini-1.0-pro": "gemini-2.5-pro",
                "gemini-pro": "gemini-2.5-pro",
                "gemini-2.0-flash": "gemini-2.5-flash",
                "gemini-2.0-flash-exp": "gemini-2.5-flash",
            }
            if model in model_migration:
                logger.warning(
                    "model_migration",
                    old_model=model,
                    new_model=model_migration[model],
                    agent_id=self.agent.id,
                )
                model = model_migration[model]
            
            # Stream agent output
            full_output = ""
            async for chunk in generate_streaming(
                system_prompt=system_prompt,
                user_input=task,
                model=model,
                temperature=temperature,
                api_key=self.api_key
            ):
                full_output += chunk
                yield {
                    "type": "output_chunk",
                    "agent_id": self.agent.id,
                    "data": chunk
                }
            
            # Agent completed successfully
            self.mailbox.set_state(AgentState.COMPLETED)
            yield {
                "type": "output",
                "agent_id": self.agent.id,
                "data": full_output
            }
            
            yield {
                "type": "log",
                "agent_id": self.agent.id,
                "data": f"[{self.agent.name}] ✓ Completed"
            }
            
        except Exception as e:
            self.mailbox.set_state(AgentState.ERROR)
            logger.error("agent_execution_error", agent_id=self.agent.id, error=str(e))
            yield {
                "type": "error",
                "agent_id": self.agent.id,
                "data": f"Error: {str(e)}"
            }
    
    def _build_system_prompt(self, context: Optional[Dict] = None) -> str:
        """Build system prompt for the agent."""
        # Use the agent's system_prompt as the base, with communication protocol added
        base_prompt = self.agent.system_prompt or f"You are {self.agent.name}, a {self.agent.role}."
        
        prompt = f"""{base_prompt}

IMPORTANT INSTRUCTIONS:
- Make decisions autonomously based on best practices and your expertise
- DO NOT ask the user for additional information - make reasonable assumptions
- If you cannot handle something directly, YOUR CHILD AGENTS WILL BE AUTOMATICALLY INVOKED
- Provide complete, actionable responses with specific recommendations

"""
        
        if context:
            prompt += f"\nContext from parent:\n{context.get('parent_message', '')}\n"
            if context.get('child_agents'):
                prompt += f"""
YOUR CHILD AGENTS (they will be automatically invoked if needed):
{context['child_agents']}

When you provide your response, if you mention needing help from a child agent, they will be automatically delegated to and their results will be incorporated. You don't need to wait - just provide your analysis and recommendations, and the system will ensure child agents contribute.
"""
        
        return prompt
    
    def _extract_user_request(self, output: str) -> str:
        """Extract user input request from output."""
        if "[REQUEST_USER_INPUT:" in output:
            start = output.index("[REQUEST_USER_INPUT:") + len("[REQUEST_USER_INPUT:")
            end = output.index("]", start)
            return output[start:end].strip()
        return "Additional information needed"
    
    def _extract_parent_query(self, output: str) -> str:
        """Extract parent query from output."""
        if "[QUERY_PARENT:" in output:
            start = output.index("[QUERY_PARENT:") + len("[QUERY_PARENT:")
            end = output.index("]", start)
            return output[start:end].strip()
        return "Need clarification"


class MessageBasedOrchestrator:
    """Orchestrates multi-agent execution using explicit messages."""
    
    def __init__(self, db: Session):
        self.db = db
        self.executors: Dict[str, AgentExecutor] = {}
        self.agent_outputs: Dict[str, str] = {}
        
    async def execute_run(
        self,
        run_id: str,
        root_agent_id: str,
        input_data: Dict,
        api_key: Optional[str] = None,
        images: Optional[List[str]] = None,
    ) -> AsyncGenerator[Dict, None]:
        """
        Execute a run using message-based communication.
        
        Phases:
        1. Root agent analyzes task
        2. Root agent selects which children (if any) to delegate to
        3. Children execute in parallel
        4. Children can query parent or request user input
        5. Root agent synthesizes results
        """
        logger.info("orchestrator_v2_start", run_id=run_id, root_agent_id=root_agent_id)
        
        # Load run
        run = self.db.query(RunModel).filter(RunModel.id == run_id).first()
        if not run:
            yield {"type": "error", "data": "Run not found"}
            return
        
        # Update run status
        run.status = "running"
        run.started_at = datetime.utcnow()
        self.db.commit()
        
        try:
            session_id = run.session_id
            
            # Load root agent
            root_agent = self.db.query(AgentModel).filter(
                AgentModel.id == root_agent_id,
                AgentModel.session_id == session_id
            ).first()
            
            if not root_agent:
                yield {"type": "error", "data": "Root agent not found"}
                return
            
            yield {
                "type": "log",
                "agent_id": root_agent_id,
                "data": f"✓ Starting execution with {root_agent.name}"
            }
            
            # Get user task
            user_task = input_data.get("prompt", "") or input_data.get("task", "")
            
            # Phase 1: Build/Get Agent Tree Snapshot
            yield {
                "type": "log",
                "agent_id": root_agent_id,
                "data": "🗺️  Phase 1: Mapping agent ecosystem..."
            }
            
            tree_cache = get_agent_tree_cache()
            tree_snapshot = await tree_cache.get_or_build(
                session_id=session_id,
                root_agent_id=root_agent_id,
                db=self.db,
                api_key=api_key
            )
            
            yield {
                "type": "log",
                "agent_id": root_agent_id,
                "data": f"✓ Mapped ecosystem: {tree_snapshot.agent_count} agents across {tree_snapshot.max_depth + 1} levels"
            }
            
            yield {
                "type": "log",
                "agent_id": root_agent_id,
                "data": f"✓ Available agents: {', '.join([tree_snapshot.capability_map.agent_name] + [c.agent_name for c in tree_snapshot.capability_map.children])}"
            }
            
            # Phase 2: Decide delegation strategy
            yield {
                "type": "log",
                "agent_id": root_agent_id,
                "data": "🎯 Phase 2: Analyzing task and routing..."
            }
            
            # Load available children
            children = self._load_children(root_agent_id, session_id)
            
            # Select relevant agents (immediate children)
            selected_children = await AgentSelector.select_agents(
                task=user_task,
                available_agents=children,
                api_key=api_key
            )
            
            if selected_children:
                child_names = [c.name for c in selected_children]
                yield {
                    "type": "log",
                    "agent_id": root_agent_id,
                    "data": f"✓ Selected {len(selected_children)} immediate agent(s): {', '.join(child_names)}"
                }
                yield {
                    "type": "log",
                    "agent_id": root_agent_id,
                    "data": f"💡 These agents may further delegate to their {tree_snapshot.agent_count - len(selected_children) - 1} sub-agents as needed"
                }
            else:
                yield {
                    "type": "log",
                    "agent_id": root_agent_id,
                    "data": "✓ Root agent handling directly"
                }
            
            # Phase 3: Execute root agent
            yield {
                "type": "log",
                "agent_id": root_agent_id,
                "data": "🚀 Phase 3: Root agent executing..."
            }
            
            root_executor = AgentExecutor(root_agent, api_key)
            self.executors[root_agent_id] = root_executor
            
            # Build context for root
            context = {}
            if selected_children:
                context["child_agents"] = AgentSelector.format_agent_capabilities(selected_children)
            
            # Execute root agent
            async for event in root_executor.execute(user_task, context):
                yield event
                
                # Capture final output
                if event["type"] == "output":
                    self.agent_outputs[root_agent_id] = event["data"]
            
            # Phase 4: Execute selected children (if any) - RECURSIVELY
            if selected_children:
                yield {
                    "type": "log",
                    "agent_id": root_agent_id,
                    "data": f"👥 Phase 4: Executing {len(selected_children)} child agent(s) recursively..."
                }
                
                # Execute children RECURSIVELY (they can invoke their own children)
                for child in selected_children:
                    yield {
                        "type": "log",
                        "agent_id": child.id,
                        "data": f"▶️  Starting {child.name}..."
                    }
                    
                    # Execute child recursively (will handle its own children)
                    async for event in self._execute_agent_recursively(
                        agent=child,
                        task=user_task,
                        parent_output=self.agent_outputs.get(root_agent_id, ""),
                        session_id=session_id,
                        api_key=api_key,
                        depth=1
                    ):
                        yield event
                
                # Phase 5: Root synthesizes results
                yield {
                    "type": "log",
                    "agent_id": root_agent_id,
                    "data": "🔄 Phase 5: Synthesizing results from all levels..."
                }
                
                # Build synthesis prompt
                child_reports = "\n\n".join([
                    f"{child.name} Report:\n{self.agent_outputs.get(child.id, 'No output')}"
                    for child in selected_children
                ])
                
                synthesis_task = f"""Based on the following reports from your team, provide a final comprehensive response to the user.

Original request: {user_task}

Team reports:
{child_reports}

Provide a synthesized, coherent response:"""
                
                # Execute synthesis
                async for event in root_executor.execute(synthesis_task, {}):
                    yield event
                    if event["type"] == "output":
                        self.agent_outputs[f"{root_agent_id}_final"] = event["data"]
            
            # Mark run as completed
            run.status = "completed"
            run.output = self.agent_outputs.get(f"{root_agent_id}_final") or self.agent_outputs.get(root_agent_id, "")
            run.finished_at = datetime.utcnow()
            self.db.commit()
            
            yield {
                "type": "status",
                "agent_id": root_agent_id,
                "data": "completed"
            }
            
            logger.info("orchestrator_v2_complete", run_id=run_id)
            
        except Exception as e:
            logger.error("orchestrator_v2_error", run_id=run_id, error=str(e), exc_info=True)
            run.status = "failed"
            run.error = str(e)
            run.finished_at = datetime.utcnow()
            self.db.commit()
            yield {"type": "error", "data": f"Execution failed: {str(e)}"}
    
    async def _execute_agent_recursively(
        self,
        agent: AgentModel,
        task: str,
        parent_output: str,
        session_id: str,
        api_key: str,
        depth: int = 0
    ) -> AsyncGenerator[Dict, None]:
        """
        Execute an agent and recursively execute its children if needed.
        This enables true multi-level delegation.
        """
        # Load this agent's children
        children = self._load_children(agent.id, session_id)
        
        if children:
            yield {
                "type": "log",
                "agent_id": agent.id,
                "data": f"  {'  ' * depth}└─ {agent.name} has {len(children)} sub-agents: {', '.join([c.name for c in children])}"
            }
        
        # Build context including this agent's children
        context = {
            "parent_message": f"Parent's analysis: {parent_output}\n\nOriginal request: {task}"
        }
        
        if children:
            context["child_agents"] = AgentSelector.format_agent_capabilities(children)
        
        # Execute this agent
        agent_executor = AgentExecutor(agent, api_key)
        self.executors[agent.id] = agent_executor
        
        delegation_task = self._extract_delegation_for_child(
            root_output=parent_output,
            child_name=agent.name,
            original_task=task
        )
        
        agent_output = ""
        async for event in agent_executor.execute(delegation_task, context):
            yield event
            if event["type"] == "output":
                agent_output = event["data"]
                self.agent_outputs[agent.id] = agent_output
        
        # If this agent has children, RECURSIVELY execute them
        if children and agent_output:
            yield {
                "type": "log",
                "agent_id": agent.id,
                "data": f"  {'  ' * depth}↳ {agent.name} invoking its {len(children)} sub-agents..."
            }
            
            for child in children:
                yield {
                    "type": "log",
                    "agent_id": child.id,
                    "data": f"  {'  ' * (depth + 1)}▶️  {child.name} executing..."
                }
                
                # RECURSIVE CALL - child can invoke its children
                async for child_event in self._execute_agent_recursively(
                    agent=child,
                    task=task,
                    parent_output=agent_output,
                    session_id=session_id,
                    api_key=api_key,
                    depth=depth + 1
                ):
                    yield child_event
    
    def _extract_delegation_for_child(self, root_output: str, child_name: str, original_task: str) -> str:
        """Extract or generate delegation task for a child."""
        # Look for explicit delegation in root output
        delegation_markers = [
            f"[DELEGATE to {child_name}:",
            f"@{child_name}:",
            f"{child_name}, please"
        ]
        
        for marker in delegation_markers:
            if marker in root_output:
                # Extract the delegation
                start = root_output.index(marker) + len(marker)
                # Find end (next newline or end of string)
                end = root_output.find("\n", start)
                if end == -1:
                    end = len(root_output)
                return root_output[start:end].strip()
        
        # Fallback: Use original task
        return f"Help with: {original_task}"
    
    def _load_children(self, parent_id: str, session_id: str) -> List[AgentModel]:
        """Load child agents for a parent."""
        children = self.db.query(AgentModel).filter(
            AgentModel.parent_id == parent_id,
            AgentModel.session_id == session_id
        ).all()
        return children

