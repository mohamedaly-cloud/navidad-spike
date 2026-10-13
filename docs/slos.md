# SLOs: Navidad results API

What players care about on 22 December: they check their ticket and get a correct answer, quickly. Everything below comes from that.

## Scope

| Counts toward the SLO | Excluded | Why excluded |
|---|---|---|
| `GET /v1/tickets/{number}` | `GET /healthz` | Called by the kubelet, not players. Probes are cheap and frequent and would hide real errors. |
| `GET /v1/results` | `GET /readyz` | Same as above. |

## SLIs

Both SLIs are **request-based**: good requests ÷ all requests. Each minute counts as much as the traffic it carried, which matters for a service whose traffic is concentrated in one morning.

| SLI | Good event | Bad event |
|---|---|---|
| **Availability** | Any response that is not a 5xx | 5xx (including the 503 "results not published yet", which during the draw window means Redis lost its data) |
| **Latency** | Response in under 300 ms | Response in 300 ms or more |

**4xx responses count as good.** A `422` for ticket `abc` is the client's mistake, not ours. A sudden rise in 4xx is still worth watching on a dashboard (it can mean a broken frontend deploy), but it doesn't burn the error budget.

**Correctness** (a winning ticket reported as "no prize") is not measured live. It is covered by the prize-rule tests in `tests/test_prizes.py`.

## SLOs

| SLI | Target |
|---|---|
| Availability | 99.9% of requests |
| Latency | 99% of requests under 300 ms |

These are first estimates, to be validated against the load test.

## Windows

| Window | Period |
|---|---|
| **Draw window** | 22 December, 08:00–17:00 Europe/Madrid. The draw runs until about 14:00, and players keep checking all afternoon. |
| **Rest of year** | Rolling 28 days |

The draw window has its own SLO, so that a quiet year can't hide a bad morning. A time-based monthly SLO (99.9% of minutes) would allow 43 minutes of downtime, which could be 9:00–9:43 on draw day: the worst outage possible, and still within the SLO.

## Error budget

Allowed bad = total requests × (100% − SLO).

| Per 1,000,000 requests | Allowed |
|---|---|
| Availability (99.9%) | 1,000 failed requests |
| Latency (99%) | 10,000 slow requests |

Expected draw-day traffic is estimated in `docs/capacity.md`.

## Error budget policy

- **Change freeze from 15 December** until the end of the draw window. No deploys, only emergency fixes.
- **Pre-scale before 08:00** on 22 December (raise HPA `minReplicas`) instead of waiting for the HPA to react to the spike.
- **Alert in minutes, not hours.** The draw window is short, so a burn-rate alert has to catch a fast burn before the budget is gone.
- **Budget spent during the rest of the year** → pause feature work and fix reliability first.

## SLA

None. The lottery has no contract with players. If there were one, it would be looser than the SLO (for example 99.5% availability) so that we notice and fix problems before owing anything.
