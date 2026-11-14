import asyncio

from game import main as run_game


async def main() -> None:
    await run_game()


asyncio.run(main())
