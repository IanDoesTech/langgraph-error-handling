# Better error handling in LangGraph

Before you read any further, I strongly recommend you check to see if there has been any progress on this feature request: [More robust error handling for nodes #6170](https://github.com/langchain-ai/langgraph/issues/6170). If it has been resolved, LangGraph may now have a first-class answer to the problem this article works around, and reading this might be pointless. I may have wasted my time writing it. Oh well...

Otherwise... Great! Hi!

At the time of writing, the official strategy for handling errors in LangGraph can be found at [Thinking in LangGraph: Handle errors appropriately](https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph#handle-errors-appropriately). Along with some code examples, it says this:


| Error Type | Who Fixes It | Strategy | When to Use |
| --- | --- | --- | --- |
| Transient errors (network issues, rate limits) | System (automatic) | Retry policy | Temporary failures that usually resolve on retry |
| LLM-recoverable errors (tool failures, parsing issues) | LLM | Store error in state and loop back | LLM can see the error and adjust its approach |
| User-fixable errors (missing information, unclear instructions) | Human | Pause with `interrupt()` | Need user input to proceed |
| Unexpected errors | Developer | Let them bubble up | Unknown issues that need debugging |

These strategies are reasonable, but...

## Two lacking cases

### Transient errors

This mechanism is useful, but it has several glaring omissions:

1. What if network errors are concerningly frequent, but never exhaust the retries? Will anyone know they're happening?
2. What happens if the retries are exhausted? Does it fall over in a heap, or does the user get a helpful response back to the UI telling them that an error occurred, and support has been made aware of it? (Please say you would prefer the latter!)

### Unexpected errors

This is fine in development, but what if some edge case is missed and the code sneaks into production? Surely, these errors should be handled similar to my suggestion for transient errors.

## How to solve it

Ideally, with the feature request I mentioned earlier, but for now, this is a **simplified** version of what I do:

### Create state to handle the error

```python
from typing_extensions import TypedDict
from langgraph.graph import MessagesState


class WorkflowError(TypedDict, total=False):
    """Structured workflow error for graph-level failure handling."""

    node: str
    exception_type: str
    message: str
    # Other serializable info that might be useful to your error handling node...


class State(MessagesState):
    # The rest of your state goes here...
    error: WorkflowError | None
```

**Important**: Don't put the raw exception object in your graph state. State often needs to be checkpointed, serialized, streamed, or inspected later. Store serializable fields such as `exception_type`, `message`, `node`, and maybe a trace or support ID.

## Create a dedicated error handling node

Its job is to tell the user that something went wrong and that support knows about it. Something like this:

```python
from langchain_core.messages import AIMessage

from agents.content_processor.state import State
from agents.content_processor.config import logger

NODE_NAME = "error_handler"
ERROR_MESSAGE = "Sorry, something went wrong while processing your content. I have reported the issue to our support team."

async def error_handler(state: State):
    """Handle errors"""

    logger.invoked(NODE_NAME)

    ai_message = AIMessage(
        content=ERROR_MESSAGE
    )

    return {
        "messages": [ai_message],
        "error": None
    }
```

**Note:**
- We could notify support from here, or have that in another dedicated node.
- We set the `error` back to `None` so we don't introduce any weird bugs on the next run. You might want to do this in a final `clean-up` node.

## Handle error in nodes

This is where LangGraph's extremely handy [Command](https://reference.langchain.com/python/langgraph/types/Command) comes in.

Basically, any node that needs to handle errors will look something like this:

```python
from typing import Literal

from langgraph.types import Command

from agents.content_processor.config import logger
from agents.content_processor.state import State, WorkflowError
from agents.content_processor.utils.fetch_utils import fetch_url_content
from agents.content_processor.utils.state_utils import get_input_content

NODE_NAME = "fetch_url"

RouterDestination = Literal[
    "error_handler",
    "convert_to_markdown",
]


async def fetch_url(state: State) -> Command[RouterDestination]:
    """Fetch content from a URL."""

    logger.invoked(NODE_NAME)
    url = get_input_content(state)

    try:
        html = await fetch_url_content(url)

        return Command(
            goto="convert_to_markdown",
            update={
                "output": {
                    "raw_html": html,
                },
            },
        )

    except Exception as exc:
        logger.error(f"URL fetch failed for {url}: {exc}", exc_info=True)
        return Command(
            goto="error_handler",
            update={
                "error": WorkflowError(
                    node=NODE_NAME,
                    exception_type=type(exc).__name__,
                    message=str(exc),
                ),
            },
        )
```

This catches `Exception` because the point is to handle any failure in this node the same way: log it, put a serializable error in state, and route to a user-facing error handler. If something surprising happens in production, I still want the graph to route to a useful response instead of leaving the user with a broken run.

The important constraint is that this broad `except Exception` is scoped around work that should not call `interrupt()` or intentionally bubble control flow to a parent graph. This matters in LangGraph because features such as `interrupt()` use internal control-flow exceptions. The [interrupt docs](https://docs.langchain.com/oss/python/langgraph/interrupts#do-not-wrap-interrupt-calls-in-tryexcept) explicitly warn against wrapping interrupt calls in broad `try`/`except` blocks. Keep interrupt calls outside this kind of error-handling block.

## But that example does away with retries!

Well spotted! You're right, and that's why we need a lifecycle hook, but for now, I would consider the following options:

### Implement a custom retry mechanism in the node

See: [The best way in LangGraph to control flow after retries exhausted: IMHO, what do you think about these examples?](https://forum.langchain.com/t/the-best-way-in-langgraph-to-control-flow-after-retries-exhausted/1574/3)

### Have your main node call a subgraph with a child node with retry policies

This is more work, but it could give you the best of both worlds.

If I get time in the future, I'll create a small repo to demonstrate this, but the basic idea would be:

1. You create a subgraph with its own state, containing a `result` field.
2. Within that subgraph, you create the node that might experience transient errors, adding it to the subgraph with something like:

    ```python
    from langgraph.types import RetryPolicy

    workflow.add_node(
        "search_documentation",
        search_documentation,
        retry_policy=RetryPolicy(max_attempts=3, initial_interval=1.0)
    )
    ```

    A small but important detail: `max_attempts` includes the first attempt. Also, make sure the retry policy actually retries the exceptions you care about. The default policy is useful, but for provider-specific rate limits or API errors you may need to pass `retry_on=...`.

3. The node will persist to the `result` field if successful. If not, it should log the error, but then `raise` the error, so it bubbles up to the subgraph and its retry policy.
4. In your main graph, add another node that will call the subgraph (see: [Call a subgraph inside a node](https://docs.langchain.com/oss/python/langgraph/use-subgraphs#call-a-subgraph-inside-a-node)). This wrapper node contains the error trapping. If the child subgraph exhausts its retries, it raises; the wrapper catches that exception and routes to the error handler.

    ```python
    from typing import Literal

    from langgraph.types import Command

    RouterDestination = Literal[
        "error_handler",
        "next_node",
    ]


    async def call_retried_subgraph(state: State) -> Command[RouterDestination]:
        try:
            subgraph_output = await retried_subgraph.ainvoke({
                "query": state["query"],
            })

            return Command(
                goto="next_node",
                update={"result": subgraph_output["result"]},
            )

        except Exception as exc:
            logger.error("Retried subgraph failed", exc_info=True)
            return Command(
                goto="error_handler",
                update={
                    "error": WorkflowError(
                        node="call_retried_subgraph",
                        exception_type=type(exc).__name__,
                        message=str(exc),
                    ),
                },
            )
    ```

    The same warning applies here: this wrapper pattern is best for a child subgraph that is not expected to interrupt or bubble commands to the parent graph. If the child subgraph uses `interrupt()`, don't wrap that subgraph invocation in a broad `except Exception` unless you really do want to turn those pauses into failures.

## Get involved!

Hopefully by now, you've got a few new ideas for possible solutions to the error handling shortfalls, that you can adapt for your own purposes. However, you can also hopefully see why an error handling lifecycle hook would be so beneficial. If so, please add your weight by commenting on [More robust error handling for nodes #6170](https://github.com/langchain-ai/langgraph/issues/6170).

Until next time...
