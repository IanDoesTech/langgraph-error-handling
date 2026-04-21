"""Parent graph node that catches exhausted child-subgraph retries."""

from typing import Literal

from langchain_core.messages import AIMessage
from langgraph.types import Command

from examples.subgraph_retry_policy.nodes.search_documentation import reset_attempt_counter
from examples.subgraph_retry_policy.retried_subgraph import retried_subgraph
from examples.subgraph_retry_policy.state import State, create_workflow_error

NODE_NAME = "call_retried_subgraph"

RouterDestination = Literal["error_handler", "answer_user"]


async def call_retried_subgraph(state: State) -> Command[RouterDestination]:
    """Invoke the retried child graph and route exhausted retries to the error handler."""
    reset_attempt_counter()
    try:
        subgraph_output = await retried_subgraph.ainvoke(
            {
                "query": state["query"],
                "result": None,
            }
        )
        return Command(
            goto="answer_user",
            update={
                "result": subgraph_output["result"],
                "messages": [AIMessage(content="Retried subgraph succeeded.")],
            },
        )
    except Exception as exc:
        print(f"[{NODE_NAME}] subgraph failed after retries: {type(exc).__name__}: {exc}")
        return Command(
            goto="error_handler",
            update={
                "error": create_workflow_error(exception=exc, node=NODE_NAME),
            },
        )
