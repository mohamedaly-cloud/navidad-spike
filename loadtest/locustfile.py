"""Draw-morning traffic for the Navidad API, scaled 1:10 (see docs/capacity.md).

locust -f loadtest/locustfile.py --host http://localhost:30080 --headless \
    --processes 4 --csv loadtest/results/spike --html loadtest/results/spike.html
"""

import random

from locust import FastHttpUser, LoadTestShape, constant_throughput, task


class Player(FastHttpUser):
    # One request per second per user, so users == target req/s.
    wait_time = constant_throughput(1)

    @task(9)
    def check_ticket(self):
        number = f"{random.randrange(100_000):05d}"
        self.client.get(f"/v1/tickets/{number}", name="/v1/tickets/{number}")

    @task(1)
    def results(self):
        self.client.get("/v1/results")


class DrawMorning(LoadTestShape):
    """Baseline, build-up, the Gordo spike, a sustained peak, then decay."""

    # (end time in seconds, users, spawn rate per second)
    stages = (
        (120, 150, 10),     # before the draw
        (240, 500, 5),      # build-up as the draw starts
        (300, 1500, 100),   # El Gordo is announced
        (540, 1500, 100),   # sustained peak
        (660, 300, 20),     # decay
        (720, 300, 20),
    )

    def tick(self):
        run_time = self.get_run_time()
        for end, users, rate in self.stages:
            if run_time < end:
                return users, rate
        return None
