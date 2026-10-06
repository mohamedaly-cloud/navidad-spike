"""Prize rules of the Lotería de Navidad (Sorteo Extraordinario, 22 December).

Pure logic: no Redis, no web. Give it a draw, get back every number that
wins something. The rules follow the official prize program (BOE):

- Prizes stack: one décimo can win several categories at once.
- Centenas, terminaciones and reintegro never go to the number they come
  from (the Gordo does not also win its own reintegro).
- Aproximaciones wrap around: before 00000 is 99999, after 99999 is 00000.

All amounts are euros per décimo (one 20 € ticket).
"""

from collections import defaultdict

TOTAL_NUMBERS = 100_000  # tickets go from 00000 to 99999

AMOUNTS = {
    "first": 400_000,        # 1º premio, El Gordo
    "second": 125_000,       # 2º premio
    "third": 50_000,         # 3º premio
    "fourth": 20_000,        # 4º premios (2 numbers)
    "fifth": 6_000,          # 5º premios (8 numbers)
    "pedrea": 100,           # pedrea (1,794 numbers)
    "approx_first": 2_000,   # aproximaciones: number before/after the 1º
    "approx_second": 1_250,
    "approx_third": 960,
    "hundred_first": 100,    # centena: same first 3 digits as the 1º
    "hundred_second": 100,
    "hundred_third": 100,
    "hundred_fourth": 100,
    "last_two_first": 100,   # dos últimas cifras: same last 2 digits as the 1º
    "last_two_second": 100,
    "last_two_third": 100,
    "refund": 20,            # reintegro: same last digit as the 1º
}


def as_ticket(n: int) -> str:
    """Format a number as a 5-digit ticket: 123 -> "00123"."""
    return f"{n:05d}"


def build_prize_table(draw: dict) -> dict[str, list[str]]:
    """Return {ticket number: [prize categories]} for every winning number."""
    table: dict[str, list[str]] = defaultdict(list)

    def award(number: str, category: str) -> None:
        table[number].append(category)

    # Who carries each drawn prize. Fourth, fifth and pedrea have several numbers.
    winners = {
        "first": [draw["first"]],
        "second": [draw["second"]],
        "third": [draw["third"]],
        "fourth": draw["fourth"],
        "fifth": draw["fifth"],
        "pedrea": draw["pedrea"],
    }

    # 1. The drawn numbers themselves.
    for category, numbers in winners.items():
        for number in numbers:
            award(number, category)

    # 2. Aproximaciones: the number just before and just after.
    for rank in ("first", "second", "third"):
        n = int(draw[rank])
        award(as_ticket((n - 1) % TOTAL_NUMBERS), f"approx_{rank}")
        award(as_ticket((n + 1) % TOTAL_NUMBERS), f"approx_{rank}")

    # 3. Centenas: the other 99 numbers with the same first three digits.
    for rank in ("first", "second", "third", "fourth"):
        for winner in winners[rank]:
            for ending in range(100):
                number = winner[:3] + f"{ending:02d}"
                if number != winner:
                    award(number, f"hundred_{rank}")

    # 4. Dos últimas cifras: the other 999 numbers ending in the same two digits.
    for rank in ("first", "second", "third"):
        winner = draw[rank]
        for prefix in range(1_000):
            number = f"{prefix:03d}" + winner[-2:]
            if number != winner:
                award(number, f"last_two_{rank}")

    # 5. Reintegro: the other 9,999 numbers ending in the Gordo's last digit.
    gordo = draw["first"]
    for prefix in range(10_000):
        number = f"{prefix:04d}" + gordo[-1]
        if number != gordo:
            award(number, "refund")

    return dict(table)
