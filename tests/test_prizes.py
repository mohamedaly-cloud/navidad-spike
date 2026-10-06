"""Tests for the prize rules."""

from collections import Counter

from app.prizes import AMOUNTS, build_prize_table

# Hand-made draw covering edge cases:
# - the second prize is 99999, so its "next number" must wrap to 00000
# - a pedrea number with leading zeros (00123)
DRAW = {
    "first": "12345",
    "second": "99999",
    "third": "50700",
    "fourth": ["20000", "31313"],
    "fifth": ["40001", "40002", "40003", "40004", "40005", "40006", "40007", "40008"],
    "pedrea": ["00123", "65432"],
}

TABLE = build_prize_table(DRAW)


def total(number: str) -> int:
    """Euros that one décimo of this number wins (0 if nothing)."""
    return sum(AMOUNTS[category] for category in TABLE.get(number, []))


def test_gordo_does_not_win_its_own_derived_prizes():
    # No centena, terminación or reintegro coming from itself.
    assert TABLE["12345"] == ["first"]


def test_last_two_digits_match_any_number_ending_in_them():
    # Regression: terminations must match by suffix, not as an exact key.
    for number in ("00045", "54345", "98745"):
        assert set(TABLE[number]) == {"last_two_first", "refund"}
        assert total(number) == 120


def test_refund_matches_on_last_digit():
    assert TABLE["88885"] == ["refund"]
    assert total("88885") == 20


def test_prizes_stack():
    # 12344 is right before the Gordo AND in the Gordo's hundred.
    assert set(TABLE["12344"]) == {"approx_first", "hundred_first"}
    assert total("12344") == 2_100


def test_approximations_wrap_around():
    # The second prize is 99999: the number after it is 00000.
    assert "approx_second" in TABLE["99998"]
    assert "approx_second" in TABLE["00000"]


def test_leading_zeros_are_kept():
    assert TABLE["00123"] == ["pedrea"]
    assert all(len(number) == 5 for number in TABLE)


def test_number_with_no_prize_is_not_in_table():
    assert "55556" not in TABLE
    assert total("55556") == 0


def test_prize_counts_match_official_program():
    counts = Counter(category for categories in TABLE.values() for category in categories)
    assert counts == {
        "first": 1,
        "second": 1,
        "third": 1,
        "fourth": 2,
        "fifth": 8,
        "pedrea": 2,  # 1,794 in the real draw, 2 in this small test draw
        "approx_first": 2,
        "approx_second": 2,
        "approx_third": 2,
        "hundred_first": 99,
        "hundred_second": 99,
        "hundred_third": 99,
        "hundred_fourth": 198,
        "last_two_first": 999,
        "last_two_second": 999,
        "last_two_third": 999,
        "refund": 9_999,
    }
    # Every category we award has an amount, and every amount gets awarded.
    assert set(counts) == set(AMOUNTS)
