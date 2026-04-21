import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from examples.manual_retries.graph import graph


async def main() -> None:
    result = await graph.ainvoke(
        {
            "messages": [],
            "query": "How do I handle LangGraph node errors?",
            "result": None,
            "attempts": 0,
            "error": None,
        }
    )

    print("\n== manual retry example ==")
    for message in result["messages"]:
        print(f"- {message.content}")
    print(f"attempts: {result['attempts']}")
    print(f"error: {result.get('error')}")


if __name__ == "__main__":
    asyncio.run(main())
