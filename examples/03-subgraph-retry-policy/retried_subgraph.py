"""Child graph wiring that applies LangGraph RetryPolicy to a flaky node."""

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from nodes.search_documentation import (
    TemporarySearchError,
    search_documentation,
)
from state import SearchState


workflow = StateGraph(SearchState)
workflow.add_node(
    "search_documentation",
    search_documentation,
    retry_policy=RetryPolicy(
        max_attempts=3,
        initial_interval=0.1,
        retry_on=(TemporarySearchError,),
    ),
)

workflow.add_edge(START, "search_documentation")
workflow.add_edge("search_documentation", END)

retried_subgraph = workflow.compile()
