"""Constant load for failure drills: same player behaviour, no load shape.

locust -f loadtest/steady.py --host http://localhost:30080 --headless -u 300 -r 50 -t 4m
"""

from locustfile import Player  # noqa: F401
