import asyncio

from graph import graph


async def main() -> None:
    result = await graph.ainvoke(
        {
            "messages": [],
            "query": "How do I use RetryPolicy in LangGraph?",
            "result": None,
            "error": None,
        }
    )

    print("\n== subgraph retry policy example ==")
    for message in result["messages"]:
        print(f"- {message.content}")
    print(f"error: {result.get('error')}")


if __name__ == "__main__":
    asyncio.run(main())
