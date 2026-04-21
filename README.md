# LangGraph Error Handling Examples

This repository contains small, runnable examples for the error handling patterns discussed in the article **Better error handling in LangGraph**.

The examples are intentionally narrower than a production agent. They focus on the graph patterns:

- Store serializable workflow errors in state.
- Route failed nodes to a dedicated error handler with `Command`.
- Keep user-facing failure responses inside the graph.
- Compare two retry approaches: manual retries inside a node and LangGraph retry policies inside a child subgraph.

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)

No LLM provider key is required. The examples use deterministic fake services so you can see success, retry, and failure behavior without external APIs.

## Setup

```bash
uv sync
cp .env.example .env
```

The default `.env.example` value makes retry examples fail twice, then succeed:

```env
FAIL_FIRST_N_ATTEMPTS=2
```

Set `FAIL_FIRST_N_ATTEMPTS` higher than the retry limit to see the graph route to the error handler.

## Run The Examples

```bash
uv run python examples/node_error_routing/run.py
uv run python examples/manual_retries/run.py
uv run python examples/subgraph_retry_policy/run.py
```

Each script prints the graph messages and the final error state.
The retry example scripts run both a recovery path and an error-handler path so
you can see the returned failure message from one command.
The final error state is `None` on handled failures because the error handler
turns the internal workflow error into a user-facing message, then clears it.

Each example keeps graph wiring in `graph.py` and node implementations in a local
`nodes/` folder. That mirrors the structure you would usually want in a real
agent while keeping each example self-contained.

## Try The Examples In LangGraph Studio

The repository includes `langgraph.json`, so LangGraph Studio can load all three
example graphs directly:

- `node_error_routing`
- `manual_retries`
- `subgraph_retry_policy`

Start the local LangGraph development server from the repository root:

```bash
uv run langgraph dev
```

The CLI opens LangGraph Studio in your browser. If it does not open
automatically, use the Studio URL printed by the command. In Studio, select one
of the graph IDs above, create a thread, and invoke it with one of these inputs.

For `node_error_routing`, use a normal topic to see the success path:

```json
{
  "messages": [],
  "topic": "LangGraph error handling",
  "draft": null,
  "error": null
}
```

Set `topic` to a value containing `fail` to see the graph route to
`error_handler`:

```json
{
  "messages": [],
  "topic": "fail this node",
  "draft": null,
  "error": null
}
```

For `manual_retries`, use:

```json
{
  "messages": [],
  "query": "How do I handle LangGraph node errors?",
  "result": null,
  "attempts": 0,
  "error": null
}
```

For `subgraph_retry_policy`, use:

```json
{
  "messages": [],
  "query": "How do I use RetryPolicy in LangGraph?",
  "result": null,
  "error": null
}
```

The retry examples read `FAIL_FIRST_N_ATTEMPTS` from `.env`. The default value
of `2` lets both retry examples recover. Set it above the retry limit, for
example `5`, then restart `uv run langgraph dev` to inspect the error-handler
path and returned failure message in Studio.

## Example 1: Node Error Routing

Path: `examples/node_error_routing`

This is the core pattern:

1. A node wraps normal work in `try` / `except Exception`.
2. On failure, it logs or records the exception details.
3. It returns `Command(goto="error_handler", update={...})`.
4. The error handler adds a user-facing message and clears the graph error.

The important detail is that the graph state stores a serializable error shape:

```python
class WorkflowError(TypedDict):
    node: str
    exception_type: str
    message: str
```

Do not put raw exception objects in graph state. State may be checkpointed, streamed, inspected, or serialized.

## Example 2: Manual Retries

Path: `examples/manual_retries`

This example keeps retry control inside the node. It is useful when you want application-level control over:

- which exceptions retry,
- how many attempts happen,
- what gets logged for each failed attempt,
- what state gets updated when retries are exhausted.

After retry exhaustion, the node routes to `error_handler` the same way as the first example.

## Example 3: Subgraph Retry Policy

Path: `examples/subgraph_retry_policy`

This example uses LangGraph's `RetryPolicy` in a child graph:

1. The child node does the flaky work.
2. The child node raises retryable exceptions.
3. LangGraph retries the child node according to `RetryPolicy`.
4. The parent graph calls the child graph from a wrapper node.
5. If the child graph exhausts retries, the wrapper catches the exception and routes to `error_handler`.

This gives you LangGraph-managed retries while keeping the parent graph's user-facing error path.

## Choosing A Pattern

Use direct node error routing when the work is not worth retrying or when any failure should immediately become a graph-level user-facing error.

Use manual retries when you need full control and visibility in normal Python code.

Use the subgraph retry policy pattern when you want LangGraph to own retry behavior, but still want the parent graph to recover cleanly after retries are exhausted.

## Interrupt Warning

The broad `except Exception` examples are scoped around normal node work. Do not wrap `interrupt()` calls in broad `try` / `except` blocks. LangGraph uses control-flow exceptions internally for interrupts, and catching them can turn an intended pause into a failure.

If a graph or subgraph uses interrupts, keep that control flow outside this style of error handling unless you deliberately want to treat the interrupt as an error.

## Notes

These examples are teaching code, not a framework. Production agents will usually add structured logging, tracing, support IDs, checkpointing, alerting, and narrower exception classes around specific provider failures.
