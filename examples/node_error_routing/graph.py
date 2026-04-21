"""Graph wiring for the node error routing example."""

from langgraph.graph import END, START, StateGraph

from examples.node_error_routing.nodes.draft_summary import draft_summary
from examples.node_error_routing.nodes.error_handler import error_handler
from examples.node_error_routing.nodes.publish_summary import publish_summary
from examples.node_error_routing.state import State

workflow = StateGraph(State)
workflow.add_node("draft_summary", draft_summary)
workflow.add_node("publish_summary", publish_summary)
workflow.add_node("error_handler", error_handler)

workflow.add_edge(START, "draft_summary")
workflow.add_edge("publish_summary", END)
workflow.add_edge("error_handler", END)

graph = workflow.compile()
