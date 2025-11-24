from enum import Enum
from typing import Annotated, Literal
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph
from agents.base import AgentState, Step
from agents.categorizer import CategorizationAgent
from agents.orchestrator import OrchestratorAgent
# from agents.summarizer import SummaryAgent


def log_transition(state: AgentState) -> AgentState:
    """Hook that logs state transitions"""
    print(f"State transition occurred. Current state: {state}")
    return state

async def router(state: AgentState) -> str | None:
    """Router function that returns the next node based on state"""
    print("router state next_step: ", state.next_step)
    return state.next_step.value


def create_workflow() -> CompiledStateGraph:
    workflow = StateGraph(AgentState)

    workflow.add_node(Step.ORCHESTRATE.value, OrchestratorAgent().orchestrate)
    workflow.add_node(Step.CATEGORIZE.value, CategorizationAgent().process_batch)
    workflow.add_node(Step.GET_USER_FEEDBACK.value, OrchestratorAgent().get_user_feedback)
    # workflow.add_node(Step.SUMMARIZE.value, SummaryAgent().create_summary)
    workflow.add_node(Step.END.value, lambda x: x)

    workflow.add_conditional_edges(Step.ORCHESTRATE.value, router, None, None)
    workflow.add_edge(Step.CATEGORIZE.value, Step.ORCHESTRATE.value)
    workflow.add_edge(Step.GET_USER_FEEDBACK.value, Step.ORCHESTRATE.value)

    workflow.set_entry_point(Step.ORCHESTRATE.value)
    workflow.set_finish_point(Step.END.value)
    return workflow.compile()
