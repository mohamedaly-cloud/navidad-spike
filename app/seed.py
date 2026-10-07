"""Publish a simulated Navidad draw: build the prize table and load it into Redis.

Run with python -m app.seed. In Kubernetes it runs as a one-off Job.
"""

import json
import os
import random

import redis

from app.prizes import as_ticket, build_prize_table

SEED = 2025  # reproducible draw


def simulate_draw(seed: int = SEED) -> dict:
    """Pick 1,807 different numbers and hand them out as the drawn prizes."""
    rng = random.Random(seed)
    numbers = [as_ticket(n) for n in rng.sample(range(100_000), 1_807)]
    return {
        "first": numbers[0],
        "second": numbers[1],
        "third": numbers[2],
        "fourth": numbers[3:5],     # 2 numbers
        "fifth": numbers[5:13],     # 8 numbers
        "pedrea": numbers[13:],     # 1,794 numbers
    }


def main() -> None:
    draw = simulate_draw()
    table = build_prize_table(draw)

    r = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
    )

    # Atomic swap: readers see the old table or the new one, never a mix
    pipe = r.pipeline(transaction=True)
    pipe.delete("navidad:prizes")
    pipe.hset("navidad:prizes", mapping={n: json.dumps(c) for n, c in table.items()})
    pipe.set("navidad:draw", json.dumps(draw))
    pipe.execute()

    print(f"Published draw: Gordo {draw['first']}, {len(table)} winning numbers")


if __name__ == "__main__":
    main()
