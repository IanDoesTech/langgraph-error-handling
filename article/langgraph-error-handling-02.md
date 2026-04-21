# Better error handling in LangGraph

Before you read any further, I strongly recommend checking whether there has been progress on this feature request: [More robust error handling for nodes #6170](https://github.com/langchain-ai/langgraph/issues/6170). If it has been resolved, LangGraph may now have a first-class answer to the problem this article works around.

If not, this article is about a pattern I use when I want LangGraph failures to stay inside the graph long enough to produce a useful user-facing response.

There is also a small repo with runnable examples: [langgraph-error-handling](https://github.com/IanDoesTech/langgraph-error-handling). The article stands on its own, but the repo is useful if you want to run the examples, inspect the graph shape in LangGraph Studio, or compare the retry approaches without wiring everything from scratch.

At the time of writing, the official strategy for handling errors in LangGraph is described in [Thinking in LangGraph: Handle errors appropriately](https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph#handle-errors-appropriately). The guidance separates errors into roughly these categories:

| Error Type | Who Fixes It | Strategy | When to Use |
| --- | --- | --- | --- |
| Transient errors | System | Retry policy | Temporary failures that usually resolve on retry |
| LLM-recoverable errors | LLM | Store error in state and loop back | The LLM can see the error and adjust |
| User-fixable errors | Human | Pause with `interrupt()` | You need user input to proceed |
| Unexpected errors | Developer | Let them bubble up | Unknown issues that need debugging |

Those categories are reasonable. I still think two production cases need more care.

## Two lacking cases

### Transient errors

LangGraph's `RetryPolicy` is useful, but retrying a node is not always the whole story.

1. What if network errors are frequent, but never exhaust the retries? Will anyone know they are happening?
2. What happens if retries are exhausted? Does the run fail in a way your UI can turn into a helpful response, or does the user just see a broken workflow?

In a production app, I usually want the user to get a graceful message and I want the system to have enough structured information to log, trace, alert, or create a support event.

### Unexpected errors

Letting unexpected errors bubble up is great in development. It is less comforting when an edge case sneaks into production.

There are still errors you should let crash loudly. But when a node is performing ordinary application work and any failure should become the same user-facing failure path, I prefer to route the graph to a dedicated error handler.

## The core pattern

The first example in the repo is [`examples/node_error_routing`](https://github.com/IanDoesTech/langgraph-error-handling/tree/master/examples/node_error_routing). It demonstrates the minimum version of the pattern:

1. Store a serializable workflow error in state.
2. Catch failures inside a node.
3. Return `Command(goto="error_handler", update={...})`.
4. Let the error handler add a friendly message and clear the internal error.

Here is a simplified version.

### Create state for workflow errors

```python
from typing import Annotated
from typing_extensions import TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class WorkflowError(TypedDict):
    node: str
    exception_type: str
    message: str


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    topic: str
    draft: str | None
    error: WorkflowError | None


def create_workflow_error(*, exception: Exception, node: str) -> WorkflowError:
    return {
        "node": node,
        "exception_type": type(exception).__name__,
        "message": str(exception),
    }
```

Do not put raw exception objects in graph state. State may be checkpointed, serialized, streamed, inspected, or passed across process boundaries. Store fields such as `node`, `exception_type`, `message`, and maybe a support ID or trace ID.

### Create a dedicated error handler

The error handler turns the internal workflow error into something the user can see.

```python
from langchain_core.messages import AIMessage


ERROR_MESSAGE = (
    "Sorry, something went wrong while processing your latest submission. "
    "The issue has been reported to support."
)


async def error_handler(state: State) -> dict:
    logger.info("[error_handler] handled error: %s", state["error"])
    return {
        "messages": [AIMessage(content=ERROR_MESSAGE)],
        "error": None,
    }
```

The repo example only logs the error. In a real system, this is also where you might notify support, attach a support ID, emit telemetry, or route to a cleanup node. I clear `error` so the final graph state does not keep a handled internal failure around longer than needed.

### Route failed nodes with `Command`

Any node that should recover through this shared path can return a `Command`.

```python
import logging
from typing import Literal

from langchain_core.messages import AIMessage
from langgraph.types import Command


NODE_NAME = "draft_summary"
logger = logging.getLogger(__name__)

RouterDestination = Literal["error_handler", "publish_summary"]


async def draft_summary(state: State) -> Command[RouterDestination]:
    try:
        topic = state["topic"]
        if "fail" in topic.lower():
            raise ValueError("The demo topic intentionally triggered a node failure.")

        return Command(
            goto="publish_summary",
            update={
                "draft": f"Short summary for: {topic}",
                "messages": [AIMessage(content="Drafted the summary.")],
            },
        )
    except Exception as exc:
        logger.info("[%s] failed: %s: %s", NODE_NAME, type(exc).__name__, exc)
        return Command(
            goto="error_handler",
            update={
                "error": create_workflow_error(exception=exc, node=NODE_NAME),
            },
        )
```

This catches `Exception` because the example is deliberately treating every ordinary failure in that node the same way: record it, route to the shared error handler, and return a useful message from the graph.

In production, you may still choose narrower exception classes around known failure modes. The important part is not the exact exception type. The important part is that the graph has an intentional failure path instead of relying on the caller to interpret a crashed run.

One warning: do not wrap `interrupt()` calls in broad `try` / `except` blocks. LangGraph's interrupt docs explain that interrupts use internal control flow. If you catch that control flow as a normal exception, you can turn an intended pause into a handled failure. Keep interrupts outside this pattern unless you are deliberately treating them as errors.

## But that example does away with retries!

Well spotted! That basic node-routing example is not a replacement for retries. It is the failure path you want after you decide the node cannot recover.

The repo includes two retry examples:

1. [`examples/manual_retries`](https://github.com/IanDoesTech/langgraph-error-handling/tree/main/examples/manual_retries)
2. [`examples/subgraph_retry_policy`](https://github.com/IanDoesTech/langgraph-error-handling/tree/main/examples/subgraph_retry_policy)

Both examples use deterministic fake services, so you can run the success and exhausted-retry paths without an LLM provider key or external API.

### Option 1: Implement manual retries inside the node

Manual retries are plain Python. They are useful when you want full control over the retry loop, including:

- which exceptions retry,
- how attempts are counted,
- what gets logged for every failed attempt,
- what state is updated when retries are exhausted,
- whether retry behavior depends on application state.

In the repo, `examples/manual_retries/nodes/search_documentation.py` calls a small `retry_async` helper. If the fake documentation search eventually succeeds, the node routes to `answer_user`. If retries are exhausted, it routes to `error_handler`.

The high-level shape is:

```python
RouterDestination = Literal["error_handler", "answer_user"]


async def search_documentation(state: State) -> Command[RouterDestination]:
    try:
        result, attempts = await retry_async(
            lambda attempt: flaky_documentation_search(state["query"], attempt),
            max_attempts=3,
            retry_exceptions=(TemporarySearchError,),
        )
        return Command(
            goto="answer_user",
            update={
                "attempts": attempts,
                "result": result,
            },
        )
    except Exception as exc:
        return Command(
            goto="error_handler",
            update={
                "attempts": 3,
                "error": create_workflow_error(exception=exc, node="search_documentation"),
            },
        )
```

This approach is boring, explicit, and easy to instrument. That is sometimes exactly what you want.

The trade-off is that LangGraph is not managing the retry behavior for you. If you want exponential backoff, jitter, per-exception policies, attempt-level tracing, or cancellation behavior, you own that code.

### Option 2: Put `RetryPolicy` in a child graph

If you want LangGraph to own retries but you still want a graceful parent-graph failure path, one workable pattern is to put the retrying node inside a child graph.

The child graph owns the retry policy:

```python
from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy


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
```

The child node raises retryable exceptions. If it succeeds, the child graph returns a result. If it exhausts retries, the child graph raises to its caller.

Then the parent graph calls the child graph from a wrapper node:

```python
RouterDestination = Literal["error_handler", "answer_user"]


async def call_retried_subgraph(state: State) -> Command[RouterDestination]:
    try:
        subgraph_output = await retried_subgraph.ainvoke(
            {
                "query": state["query"],
                "result": None,
            }
        )
        return Command(
            goto="answer_user",
            update={"result": subgraph_output["result"]},
        )
    except Exception as exc:
        return Command(
            goto="error_handler",
            update={
                "error": create_workflow_error(
                    exception=exc,
                    node="call_retried_subgraph",
                ),
            },
        )
```

This gives you LangGraph-managed retries in the child graph and graph-level recovery in the parent graph.

There are trade-offs. You have an extra graph boundary, separate child state, and a wrapper node whose job is mostly orchestration. I would not reach for this for every node. But when retry behavior belongs naturally to a small sub-workflow, it gives you a clean separation:

- the child graph retries transient work,
- the parent graph decides what the user sees if the child graph cannot recover.

Again, be careful with interrupts. This wrapper pattern is best for child graphs that are not expected to pause with `interrupt()` or bubble parent-level control flow. If the child graph uses interrupts, do not casually wrap `ainvoke()` in `except Exception`.

## Running the examples

The repo examples are intentionally small. They use fake deterministic services so the behavior is easy to inspect.

```bash
uv sync
cp .env.example .env

uv run python examples/node_error_routing/run.py
uv run python examples/manual_retries/run.py
uv run python examples/subgraph_retry_policy/run.py
```

The retry examples read `FAIL_FIRST_N_ATTEMPTS` from `.env`. The default value makes the fake service fail twice, then succeed. Set it above the retry limit to watch the graph route to `error_handler`.

You can also open the graphs in LangGraph Studio:

```bash
uv run langgraph dev
```

The repo's `langgraph.json` exposes three graph IDs:

- `node_error_routing`
- `manual_retries`
- `subgraph_retry_policy`

That is the best way to see how the examples differ. The article can show the shape, but Studio makes the routing behavior much easier to inspect.

## Choosing a pattern

Use direct node error routing when a failure should immediately become a graph-level user-facing error.

Use manual retries when you need application-level control and visibility in normal Python code.

Use the child-subgraph `RetryPolicy` pattern when you want LangGraph to manage retry attempts, but you still want the parent graph to recover cleanly after retries are exhausted.

None of this removes the need for observability. In a production agent, I would still add structured logging, traces, support IDs, alerting, and narrower exception handling around provider-specific failures. The point is that the graph should have a deliberate failure path, not just a hopeful retry policy and a stack trace.

## Get involved

Hopefully this gives you a few practical options for handling LangGraph failures while still returning useful responses to users.

I still think an error handling lifecycle hook would make this cleaner. If you agree, consider commenting on [More robust error handling for nodes #6170](https://github.com/langchain-ai/langgraph/issues/6170).

Until next time...
