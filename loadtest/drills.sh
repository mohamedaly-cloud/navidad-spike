#!/usr/bin/env bash
# Failure drills under a steady 300 req/s. Usage: loadtest/drills.sh [pod-kill|rollout|redis-loss]
set -euo pipefail

HOST=${HOST:-http://localhost:30080}
OUT=loadtest/results
drill=$1

run_load() {
  .venv/bin/locust -f loadtest/steady.py --host "$HOST" --headless \
    -u 300 -r 50 -t 4m --csv "$OUT/drill-$drill" --only-summary > /dev/null 2>&1 &
  LOAD_PID=$!
  sleep 60
}

stamp() { echo "$(date -u +%H:%M:%S) $*"; }

run_load
case $drill in
  pod-kill)
    pod=$(kubectl get pods -l app=api -o name | head -1)
    stamp "force-deleting $pod"
    kubectl delete "$pod" --grace-period=0 --force > /dev/null 2>&1
    ;;
  rollout)
    stamp "rollout restart"
    kubectl rollout restart deploy/api > /dev/null
    kubectl rollout status deploy/api --timeout=180s > /dev/null
    stamp "rollout complete"
    ;;
  redis-loss)
    stamp "deleting the Redis pod"
    kubectl delete pod -l app=redis --wait=false > /dev/null
    sleep 30
    stamp "re-seeding"
    kubectl delete job seed --ignore-not-found > /dev/null
    kubectl apply -f k8s/seed-job.yaml > /dev/null
    kubectl wait --for=condition=complete job/seed --timeout=120s > /dev/null
    stamp "seed complete"
    ;;
esac
wait "$LOAD_PID" || true
stamp "load finished"
