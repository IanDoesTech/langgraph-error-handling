"""Graph wiring for the manual retry example."""

from langgraph.graph import END, START, StateGraph

from examples.manual_retries.nodes.answer_user import answer_user
from examples.manual_retries.nodes.error_handler import error_handler
from examples.manual_retries.nodes.search_documentation import search_documentation
from examples.manual_retries.state import State

workflow = StateGraph(State)
workflow.add_node("search_documentation", search_documentation)
workflow.add_node("answer_user", answer_user)
workflow.add_node("error_handler", error_handler)

workflow.add_edge(START, "search_documentation")
workflow.add_edge("answer_user", END)
workflow.add_edge("error_handler", END)

graph = workflow.compile()
