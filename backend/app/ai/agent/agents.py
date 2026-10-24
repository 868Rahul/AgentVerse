from dataclasses import dataclass

from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field
from ai.agent.oa_assistant import oa_assistant
from ai.agent.multi_agent import supervisor_agent
from ai.agent.weather_agent import weather_calculator_agent


DEFAULT_AGENT = "oa-assistant"

class AgentInfo(BaseModel):
    """Info about an available agent."""

    key: str = Field(
        description="Agent key.",
        examples=["oa-assistant"],
    )
    description: str = Field(
        description="Description of the agent.",
        examples=["A oa assistant for company"],
    )

@dataclass
class Agent:
    description: str
    graph: CompiledStateGraph


agents: dict[str, Agent] = {
    "oa-assistant": Agent(description="HR assistant: Employee Handbook policies and employee lookup.", graph=oa_assistant),
    "weather-calculator": Agent(description="Current weather, forecasts and exact calculations.", graph=weather_calculator_agent),
    "multi-agent-supervisor": Agent(description="Supervisor that routes to HR, weather, math, code and general agents.", graph=supervisor_agent),
}

## Get agent by agent_id
def get_agent(agent_id: str) -> CompiledStateGraph:
    """Get agent by agent_id"""
    return agents[agent_id].graph


def get_all_agent_info() -> list[AgentInfo]:
    return [
        AgentInfo(key=agent_id, description=agent.description) for agent_id, agent in agents.items()
    ]
