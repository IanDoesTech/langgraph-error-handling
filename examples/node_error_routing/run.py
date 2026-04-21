import asyncio

from examples.node_error_routing.graph import graph


def print_result(label: str, result: dict) -> None:
    print(f"\n== {label} ==")
    for message in result["messages"]:
        print(f"- {message.content}")
    print(f"error: {result.get('error')}")


async def main() -> None:
    success = await graph.ainvoke(
        {
            "messages": [],
            "topic": "LangGraph error handling",
            "draft": None,
            "error": None,
        }
    )
    print_result("success path", success)

    failure = await graph.ainvoke(
        {
            "messages": [],
            "topic": "fail this node",
            "draft": None,
            "error": None,
        }
    )
    print_result("error-handler path", failure)


if __name__ == "__main__":
    asyncio.run(main())
