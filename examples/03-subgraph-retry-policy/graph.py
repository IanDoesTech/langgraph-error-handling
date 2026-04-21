"""Parent graph wiring for the subgraph retry policy example."""

from langgraph.graph import END, START, StateGraph

from nodes.answer_user import answer_user
from nodes.call_retried_subgraph import call_retried_subgraph
from nodes.error_handler import error_handler
from state import State

workflow = StateGraph(State)
workflow.add_node("call_retried_subgraph", call_retried_subgraph)
workflow.add_node("answer_user", answer_user)
workflow.add_node("error_handler", error_handler)

workflow.add_edge(START, "call_retried_subgraph")
workflow.add_edge("answer_user", END)
workflow.add_edge("error_handler", END)

graph = workflow.compile()
