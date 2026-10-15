# Capacity estimate: Navidad results API

How many API pods are needed on draw morning, and does anything else run out first? Demand is estimated, supply is measured, and both are compared to what a laptop can run.

## Demand (estimate)

A Fermi estimate: round numbers, every assumption written down so it can be challenged.

| Assumption | Value |
|---|---|
| People who play | ~30M (Spain has ~48M people, including children) |
| Share who check online | 50% → 15M (others watch TV, or one person checks a shared ticket for a group) |
| Checks per person on draw day | 5 → 75M checks |
| Share in the busiest hour | 25% → ~20M checks |
| Average rate in that hour | 20M ÷ 3,600 s ≈ 5,500 req/s |
| Peak factor (the minute El Gordo is announced) | 3× |
| **Peak demand** | **~15,000 req/s** |

Capacity is sized for the peak, not the average. An hourly average hides the two-minute burst that actually breaks things.

## Supply: one API pod (measured)

Setup: one pod (CPU request 100m, limit 500m), loaded directly by its pod IP with [fortio](https://fortio.org) from inside the cluster. Endpoint `GET /v1/tickets/73105`. 13 October 2026, minikube on a laptop.

| Target rate | Achieved | p50 | p99 | Errors |
|---|---|---|---|---|
| 50/s | 50/s | 9 ms | 28 ms | 0 |
| 100/s | 100/s | 18 ms | 108 ms (outlier) | 0 |
| 200/s | 200/s | 18 ms | 42 ms | 0 |
| 400/s | 400/s | 18 ms | 40 ms | 0 |
| 800/s | 641/s | 97 ms | n/a | 0 |
| max | 645/s | 97 ms | 171 ms | 0 |

- **Ceiling: ~645 req/s per pod.** The pod is CPU-bound: it used 439m of its 500m limit, so Kubernetes throttled it.
- **Latency rises before errors appear.** Near the ceiling, p50 went from 18 ms to 97 ms (5×) while every request still returned 200. Requests were queueing for CPU.
- **Planning number: 400 req/s per pod** (~62% of the ceiling). This leaves room for queueing, the HPA's ~40 s reaction time (measured under load), and losing a pod.

## Pods needed (production)

```
15,000 req/s ÷ 400 req/s per pod = 37.5 → 38 pods
```

With pods spread across 3 Availability Zones, losing one zone must leave enough capacity (N+1):

```
38 pods ÷ 2 surviving zones = 19 per zone × 3 zones = 57 pods
```

57 pods × 0.5 CPU ≈ 29 CPUs at peak.

## Next bottleneck: Redis (measured)

Each ticket check sends Redis two commands in one pipeline (EXISTS + HGET).

| Command | Throughput | p50 |
|---|---|---|
| `HGET navidad:prizes 73105` | ~94,000/s | 0.27 ms |
| `EXISTS navidad:draw` | ~96,000/s | 0.26 ms |

Measured with `redis-benchmark` (50 clients) inside the Redis pod, so no network hop. Real traffic adds network time per request, but throughput stays in the same range.

```
15,000 req/s × 2 commands = 30,000 commands/s ≈ 32% of one Redis
```

Redis is not the capacity bottleneck. It is an **availability** risk: one Redis pod, and if it dies, every check returns 503 (covered by a failure drill).

## The laptop simulation (scaled 1:10)

The laptop has 12 CPUs, shared with the load generator, so the full 29 CPUs won't fit. The simulation runs at 1:10:

| | Production estimate | Simulation |
|---|---|---|
| Peak demand | 15,000 req/s | 1,500 req/s |
| Pods needed at 400 req/s | 38 (57 with zone margin) | 4 |
| HPA range | n/a | 2–8 (room to scale) |
| Redis load | ~32% | ~3% |

## Findings and ideas

- **CPU request is too low.** The request is 100m, but a pod serving 400 req/s uses several times that. The scheduler packs pods by request, so the node is overcommitted under load, and the HPA (80% of the request) reacts at a very low load. Rightsize the request from measured usage (now 250m, see `docs/load-test-report.md`, finding 4).
- **Cache the answers.** There are only 100,000 possible ticket numbers and the results are the same for everyone, so almost every response can be cached at a CDN (e.g. CloudFront). Most of the 15,000 req/s would then never reach the pods.
- **Pre-scale.** Raise `minReplicas` before 08:00 on 22 December instead of waiting for the HPA (see `docs/slos.md`).
