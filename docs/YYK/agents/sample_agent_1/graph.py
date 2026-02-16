from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from app.agents.sample_agent_1.nodes.sample_node import generate_korean_sentence
from app.agents.sample_agent_1.state.sample_state import SampleAgent1State


class Agent1GraphState(BaseModel):
    korean_sentence: str | None = None


def _generate_sentence_node(state: Agent1GraphState) -> dict[str, str]:
    return {"korean_sentence": generate_korean_sentence()}


def build_agent_1_sub_graph():
    graph_builder = StateGraph(Agent1GraphState)
    graph_builder.add_node("generate_sentence", _generate_sentence_node)
    graph_builder.add_edge(START, "generate_sentence")
    graph_builder.add_edge("generate_sentence", END)
    return graph_builder.compile()


sample_agent_1_sub_graph = build_agent_1_sub_graph()


def run_agent_1() -> SampleAgent1State:
    result = sample_agent_1_sub_graph.invoke(Agent1GraphState())
    return SampleAgent1State(korean_sentence=result["korean_sentence"])
