"""Dynamic agent selection based on task requirements."""
from typing import List, Dict
from db.schemas import AgentModel
from core.gemini_client import generate_text
from core.logging import get_logger
import json

logger = get_logger("agent_selector")


class AgentSelector:
    """Selects relevant agents for a given task."""
    
    @staticmethod
    async def select_agents(
        task: str,
        available_agents: List[AgentModel],
        api_key: str
    ) -> List[AgentModel]:
        """
        Determine which child agents are needed for this task.
        
        Only selects agents that are NECESSARY for the task.
        
        Args:
            task: The task to be accomplished
            available_agents: List of available child agents
            api_key: Gemini API key for selection
            
        Returns:
            List of selected agents (may be empty if parent can handle alone)
        """
        if not available_agents:
            return []
        
        # Format agent descriptions
        agent_descriptions = []
        for agent in available_agents:
            desc = {
                "id": agent.id,
                "name": agent.name,
                "role": agent.role,
                "system_prompt": agent.system_prompt or "No system prompt"
            }
            agent_descriptions.append(desc)
        
        # Create selection prompt
        prompt = f"""You are a task coordinator. Your job is to determine which agents (if any) are needed for a given task.

Task to accomplish:
{task}

Available child agents:
{json.dumps(agent_descriptions, indent=2)}

For each agent, use the "system_prompt" field to understand their capabilities.

Instructions:
1. Analyze the task carefully
2. Determine if the task requires delegation or if it can be handled directly
3. If delegation is needed, select ONLY the agents that are NECESSARY
4. Don't select agents "just in case" - only select if truly needed
5. It's perfectly fine to select NO agents if the task can be handled directly

Respond with ONLY a JSON array of agent IDs that are needed. Examples:
- If agents are needed: ["agent-id-1", "agent-id-2"]
- If no agents needed: []

Your response (JSON array only):"""

        try:
            # Get LLM selection
            response = await generate_text(
                system_prompt="You are a task coordinator that selects relevant agents. Respond ONLY with a JSON array.",
                user_input=prompt,
                model="gemini-2.5-flash",
                temperature=0.1,  # Low temperature for consistent selection
                api_key=api_key
            )
            
            # Parse response
            response = response.strip()
            if response.startswith("```json"):
                response = response.split("```json")[1].split("```")[0].strip()
            elif response.startswith("```"):
                response = response.split("```")[1].split("```")[0].strip()
            
            selected_ids = json.loads(response)
            
            if not isinstance(selected_ids, list):
                logger.warning("agent_selection_invalid_format", response=response)
                return []
            
            # Filter agents
            selected_agents = [a for a in available_agents if a.id in selected_ids]
            
            logger.info(
                "agents_selected",
                task_length=len(task),
                available_count=len(available_agents),
                selected_count=len(selected_agents),
                selected_names=[a.name for a in selected_agents]
            )
            
            return selected_agents
            
        except json.JSONDecodeError as e:
            logger.error("agent_selection_json_error", error=str(e), response=response)
            # Fallback: select no agents
            return []
        except Exception as e:
            logger.error("agent_selection_error", error=str(e))
            # Fallback: select no agents
            return []
    
    @staticmethod
    def format_agent_capabilities(agents: List[AgentModel]) -> str:
        """Format agent capabilities for context."""
        if not agents:
            return "No child agents available."
        
        formatted = []
        for agent in agents:
            # Use role and system_prompt (truncated) for description
            prompt_preview = (agent.system_prompt or "General assistant")[:100]
            formatted.append(
                f"- {agent.name} ({agent.role}): {prompt_preview}..."
            )
        
        return "\n".join(formatted)

