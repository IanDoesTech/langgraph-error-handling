import asyncio
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from examples.manual_retries.graph import graph


def print_result(label: str, result: dict) -> None:
    print(f"\n== {label} ==")
    for message in result["messages"]:
        print(f"- {message.content}")
    print(f"attempts: {result['attempts']}")
    print(f"final error state: {result.get('error')}")


async def run_example(*, fail_first_n_attempts: int) -> dict:
    os.environ["FAIL_FIRST_N_ATTEMPTS"] = str(fail_first_n_attempts)
    return await graph.ainvoke(
        {
            "messages": [],
            "query": "How do I handle LangGraph node errors?",
            "result": None,
            "attempts": 0,
            "error": None,
        }
    )


async def main() -> None:
    success = await run_example(fail_first_n_attempts=2)
    print_result("manual retry success path", success)

    failure = await run_example(fail_first_n_attempts=5)
    print_result("manual retry error-handler path", failure)


if __name__ == "__main__":
    asyncio.run(main())
