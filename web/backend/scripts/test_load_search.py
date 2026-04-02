"""
Phase 5.2 — Load / concurrency test for the place search API.

Fires N concurrent search requests using ThreadPoolExecutor and reports:
  - Total requests, failures, avg/p95/p99/max latency
  - Throughput (req/s)
"""
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")

from app.api.factory import create_app

QUERIES = [
    "mumbai", "tokyo", "paris", "london", "beach", "temple",
    "rome", "india", "australia", "cafe", "museum", "new york",
    "bali", "dubai", "mountain", "lake", "castle", "garden",
    "thailand", "singapore", "berlin", "madrid", "florence",
    "istanbul", "cairo", "mexico", "brazil", "waterfall",
]

TOTAL_REQUESTS = 100


def worker(app, query):
    """Execute a single search request and return (latency_ms, success)."""
    with app.test_client() as client:
        t0 = time.perf_counter()
        try:
            r = client.get(f"/api/v1/place-search/search?q={query}&limit=20")
            latency = (time.perf_counter() - t0) * 1000
            return latency, r.status_code == 200
        except Exception:
            latency = (time.perf_counter() - t0) * 1000
            return latency, False


def main():
    app = create_app()
    print(f"\n=== Load Test: {TOTAL_REQUESTS} concurrent search requests ===\n")

    latencies = []
    failures = 0

    t_start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = []
        for i in range(TOTAL_REQUESTS):
            q = QUERIES[i % len(QUERIES)]
            futures.append(pool.submit(worker, app, q))

        for f in as_completed(futures):
            lat, ok = f.result()
            latencies.append(lat)
            if not ok:
                failures += 1

    total_time = (time.perf_counter() - t_start) * 1000

    latencies.sort()
    avg = statistics.mean(latencies)
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]
    mx = max(latencies)
    throughput = TOTAL_REQUESTS / (total_time / 1000)

    print(f"  Total requests : {TOTAL_REQUESTS}")
    print(f"  Failures       : {failures}")
    print(f"  Wall time      : {total_time:.0f} ms")
    print(f"  Throughput     : {throughput:.1f} req/s")
    print(f"  Avg latency    : {avg:.1f} ms")
    print(f"  p50            : {p50:.1f} ms")
    print(f"  p95            : {p95:.1f} ms")
    print(f"  p99            : {p99:.1f} ms")
    print(f"  Max            : {mx:.1f} ms")

    ok = failures == 0 and p95 < 500
    print(f"\n  Result: {'PASS' if ok else 'FAIL'}")
    print(f"  (p95 < 500ms and zero failures)\n")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
