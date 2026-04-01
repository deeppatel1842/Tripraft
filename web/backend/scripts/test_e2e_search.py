"""
Phase 5.1 — End-to-end place search flow test.

Tests the complete search pipeline:
  query -> autocomplete -> search -> cached response -> place detail
Verifies FTS5, caching, pagination headers, structured errors, and ETag.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")

from app.api.factory import create_app


def main():
    app = create_app()
    client = app.test_client()
    passed = 0
    failed = 0

    def check(name, condition, detail=""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  PASS  {name}")
        else:
            failed += 1
            print(f"  FAIL  {name} — {detail}")

    print("\n=== E2E Place Search Flow ===\n")

    # 1. Stats endpoint
    print("[1] Stats")
    r = client.get("/api/v1/place-search/stats")
    data = r.get_json()
    check("stats returns 200", r.status_code == 200)
    check("stats has places count", data.get("stats", {}).get("places", 0) > 0, f"got {data}")

    # 2. Autocomplete (debounce is frontend; we test the API)
    print("\n[2] Autocomplete")
    r = client.get("/api/v1/place-search/autocomplete?q=mum")
    data = r.get_json()
    check("autocomplete 200", r.status_code == 200)
    check("autocomplete has suggestions", len(data.get("suggestions", [])) > 0)
    check("suggestion has type", data["suggestions"][0].get("type") in ("city", "state", "country", "place"))

    # short query → empty suggestions (below AUTOCOMPLETE_MIN_LENGTH)
    r = client.get("/api/v1/place-search/autocomplete?q=m")
    short_data = r.get_json()
    check("short query → 200 empty", r.status_code == 200 and len(short_data.get("suggestions", [])) == 0)

    # 3. Full search (city match)
    print("\n[3] Search — city match")
    r = client.get("/api/v1/place-search/search?q=mumbai&limit=10&page=1")
    data = r.get_json()
    check("search 200", r.status_code == 200)
    check("search has places", len(data.get("places", [])) > 0, f"count={len(data.get('places', []))}")
    check("match_type is city", data.get("match_type") == "city", f"got {data.get('match_type')}")
    check("X-Total-Count header", r.headers.get("X-Total-Count") is not None)
    check("X-Page header", r.headers.get("X-Page") == "1")

    # 4. Cached response (second request)
    print("\n[4] Cache check")
    t0 = time.perf_counter()
    r2 = client.get("/api/v1/place-search/search?q=mumbai&limit=10&page=1")
    t1 = time.perf_counter()
    check("cached search 200", r2.status_code == 200)
    elapsed_ms = (t1 - t0) * 1000
    # Second call should be fast (cache or warm DB)
    check(f"response < 200ms (got {elapsed_ms:.0f}ms)", elapsed_ms < 200)

    # 5. Search — country match
    print("\n[5] Search — country match")
    r = client.get("/api/v1/place-search/search?q=india&limit=5")
    data = r.get_json()
    check("country search 200", r.status_code == 200)
    check("match_type is country", data.get("match_type") == "country", f"got {data.get('match_type')}")

    # 6. Place detail + ETag
    print("\n[6] Place detail + ETag")
    r = client.get("/api/v1/place-search/search?q=mumbai&limit=1")
    place_id = r.get_json()["places"][0]["id"]

    r = client.get(f"/api/v1/place-search/place/{place_id}")
    data = r.get_json()
    check("detail 200", r.status_code == 200)
    check("detail has name", bool(data.get("place", {}).get("name")))
    check("detail has photos array", isinstance(data.get("place", {}).get("photos"), list))
    check("detail has tags", isinstance(data.get("place", {}).get("tags"), list))
    check("detail has opening_hours key", "opening_hours" in data.get("place", {}))
    etag = r.headers.get("ETag")
    check("ETag header present", etag is not None)

    # If-None-Match → 304
    if etag:
        r304 = client.get(f"/api/v1/place-search/place/{place_id}", headers={"If-None-Match": etag})
        check("If-None-Match → 304", r304.status_code == 304, f"got {r304.status_code}")

    # 7. Nonexistent place → 404 structured error
    print("\n[7] Structured errors")
    r = client.get("/api/v1/place-search/place/999999")
    data = r.get_json()
    check("404 for missing place", r.status_code == 404)
    check("error has message field", "message" in data or "error" in data)

    # Empty query → 200 with no results
    r = client.get("/api/v1/place-search/search?q=")
    empty_data = r.get_json()
    check("empty query → 200 empty", r.status_code == 200 and len(empty_data.get("places", [])) == 0)

    # 8. FTS5 speed test
    print("\n[8] FTS5 performance")
    queries = ["tokyo", "paris", "london", "beach", "temple"]
    times = []
    for q in queries:
        t0 = time.perf_counter()
        client.get(f"/api/v1/place-search/search?q={q}&limit=20")
        times.append((time.perf_counter() - t0) * 1000)
    avg_ms = sum(times) / len(times)
    check(f"avg search < 100ms (got {avg_ms:.0f}ms)", avg_ms < 100)

    # Summary
    total = passed + failed
    print(f"\n{'='*40}")
    print(f"Results: {passed}/{total} passed, {failed} failed")
    print(f"{'='*40}\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
