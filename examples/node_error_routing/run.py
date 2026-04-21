import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from examples.node_error_routing.graph import graph


def print_result(label: str, result: dict) -> None:
    print(f"\n== {label} ==")
    for message in result["messages"]:
        print(f"- {message.content}")
    print(f"final error state: {result.get('error')}")


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
