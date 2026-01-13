#!/usr/bin/env python3
"""Benchmark script for Rust vs Python pricing engine.

Usage:
    # Benchmark Rust pricing service
    python scripts/benchmark_pricing.py --rust --iterations 1000

    # Benchmark Python implementation
    python scripts/benchmark_pricing.py --python --iterations 1000

    # Compare both
    python scripts/benchmark_pricing.py --compare --iterations 100

Requirements:
    - Rust service running at RUST_PRICING_URL (default: http://localhost:8080/api/pricing)
    - Django settings configured
"""

import argparse
import os
import sys
import time
from decimal import Decimal
from statistics import mean, stdev

# Add src to path for Django imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "diveops.settings.dev")

import django
django.setup()

import httpx


RUST_PRICING_URL = os.environ.get("RUST_PRICING_URL", "http://localhost:8080/api/pricing")


def benchmark_rust_allocate(iterations: int) -> list[float]:
    """Benchmark Rust allocate_shared_costs endpoint."""
    times = []
    payload = {
        "shared_total": "1000.00",
        "diver_count": 7,
        "currency": "MXN",
    }

    with httpx.Client(base_url=RUST_PRICING_URL, timeout=10.0) as client:
        # Warm up
        for _ in range(10):
            client.post("/allocate", json=payload)

        # Benchmark
        for _ in range(iterations):
            start = time.perf_counter()
            response = client.post("/allocate", json=payload)
            elapsed = time.perf_counter() - start
            times.append(elapsed * 1000)  # Convert to ms

            if response.status_code != 200:
                print(f"Error: {response.status_code} - {response.text}")
                break

    return times


def benchmark_rust_totals(iterations: int) -> list[float]:
    """Benchmark Rust calculate_totals endpoint."""
    times = []
    payload = {
        "lines": [
            {
                "key": "boat",
                "allocation": "shared",
                "shop_cost_amount": "1800",
                "shop_cost_currency": "MXN",
                "customer_charge_amount": "2000",
                "customer_charge_currency": "MXN",
            },
            {
                "key": "gas",
                "allocation": "per_diver",
                "shop_cost_amount": "100",
                "shop_cost_currency": "MXN",
                "customer_charge_amount": "0",
                "customer_charge_currency": "MXN",
            },
            {
                "key": "guide",
                "allocation": "shared",
                "shop_cost_amount": "500",
                "shop_cost_currency": "MXN",
                "customer_charge_amount": "600",
                "customer_charge_currency": "MXN",
            },
        ],
        "diver_count": 4,
        "currency": "MXN",
        "equipment_rentals": [
            {
                "unit_cost_amount": "50",
                "unit_charge_amount": "100",
                "quantity": 2,
            }
        ],
    }

    with httpx.Client(base_url=RUST_PRICING_URL, timeout=10.0) as client:
        # Warm up
        for _ in range(10):
            client.post("/totals", json=payload)

        # Benchmark
        for _ in range(iterations):
            start = time.perf_counter()
            response = client.post("/totals", json=payload)
            elapsed = time.perf_counter() - start
            times.append(elapsed * 1000)  # Convert to ms

            if response.status_code != 200:
                print(f"Error: {response.status_code} - {response.text}")
                break

    return times


def benchmark_python_allocate(iterations: int) -> list[float]:
    """Benchmark Python allocate_shared_costs function."""
    from diveops.operations.pricing.calculators import allocate_shared_costs

    times = []

    # Warm up
    for _ in range(10):
        allocate_shared_costs(Decimal("1000.00"), 7, "MXN")

    # Benchmark
    for _ in range(iterations):
        start = time.perf_counter()
        allocate_shared_costs(Decimal("1000.00"), 7, "MXN")
        elapsed = time.perf_counter() - start
        times.append(elapsed * 1000)  # Convert to ms

    return times


def benchmark_python_totals(iterations: int) -> list[float]:
    """Benchmark Python calculate_totals equivalent."""
    from diveops.operations.pricing.calculators import round_money

    times = []
    lines = [
        {"allocation": "shared", "shop_cost_amount": Decimal("1800"), "customer_charge_amount": Decimal("2000")},
        {"allocation": "per_diver", "shop_cost_amount": Decimal("100"), "customer_charge_amount": Decimal("0")},
        {"allocation": "shared", "shop_cost_amount": Decimal("500"), "customer_charge_amount": Decimal("600")},
    ]
    diver_count = 4
    rentals = [{"unit_cost_amount": Decimal("50"), "unit_charge_amount": Decimal("100"), "quantity": 2}]

    def calculate_totals_python():
        shared_cost = Decimal("0")
        shared_charge = Decimal("0")
        per_diver_cost = Decimal("0")
        per_diver_charge = Decimal("0")

        for line in lines:
            if line["allocation"] == "shared":
                shared_cost += line["shop_cost_amount"]
                shared_charge += line["customer_charge_amount"]
            else:
                per_diver_cost += line["shop_cost_amount"]
                per_diver_charge += line["customer_charge_amount"]

        for rental in rentals:
            per_diver_cost += rental["unit_cost_amount"] * rental["quantity"]
            per_diver_charge += rental["unit_charge_amount"] * rental["quantity"]

        shared_cost_per_diver = round_money(shared_cost / diver_count) if diver_count > 0 else Decimal("0")
        shared_charge_per_diver = round_money(shared_charge / diver_count) if diver_count > 0 else Decimal("0")

        total_cost_per_diver = shared_cost_per_diver + per_diver_cost
        total_charge_per_diver = shared_charge_per_diver + per_diver_charge

        return {
            "total_cost_per_diver": total_cost_per_diver,
            "total_charge_per_diver": total_charge_per_diver,
        }

    # Warm up
    for _ in range(10):
        calculate_totals_python()

    # Benchmark
    for _ in range(iterations):
        start = time.perf_counter()
        calculate_totals_python()
        elapsed = time.perf_counter() - start
        times.append(elapsed * 1000)  # Convert to ms

    return times


def print_stats(name: str, times: list[float]):
    """Print benchmark statistics."""
    if not times:
        print(f"{name}: No data")
        return

    avg = mean(times)
    std = stdev(times) if len(times) > 1 else 0
    min_t = min(times)
    max_t = max(times)
    p50 = sorted(times)[len(times) // 2]
    p95 = sorted(times)[int(len(times) * 0.95)]
    p99 = sorted(times)[int(len(times) * 0.99)]

    print(f"\n{name}:")
    print(f"  Iterations: {len(times)}")
    print(f"  Mean:       {avg:.3f} ms")
    print(f"  Std Dev:    {std:.3f} ms")
    print(f"  Min:        {min_t:.3f} ms")
    print(f"  Max:        {max_t:.3f} ms")
    print(f"  P50:        {p50:.3f} ms")
    print(f"  P95:        {p95:.3f} ms")
    print(f"  P99:        {p99:.3f} ms")


def check_rust_health() -> bool:
    """Check if Rust pricing service is available."""
    try:
        response = httpx.get(f"{RUST_PRICING_URL}/health", timeout=5.0)
        return response.status_code == 200
    except Exception as e:
        print(f"Rust service not available: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Benchmark pricing implementations")
    parser.add_argument("--rust", action="store_true", help="Benchmark Rust implementation")
    parser.add_argument("--python", action="store_true", help="Benchmark Python implementation")
    parser.add_argument("--compare", action="store_true", help="Compare both implementations")
    parser.add_argument("--iterations", type=int, default=100, help="Number of iterations (default: 100)")
    args = parser.parse_args()

    if not any([args.rust, args.python, args.compare]):
        parser.print_help()
        return

    print(f"Benchmark Configuration:")
    print(f"  Iterations: {args.iterations}")
    print(f"  Rust URL:   {RUST_PRICING_URL}")

    if args.rust or args.compare:
        if not check_rust_health():
            print("\nError: Rust pricing service is not available.")
            print(f"Make sure the service is running at {RUST_PRICING_URL}")
            if not args.compare:
                return

    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS")
    print("=" * 60)

    if args.rust or args.compare:
        if check_rust_health():
            print("\n--- Rust Implementation ---")
            rust_allocate = benchmark_rust_allocate(args.iterations)
            print_stats("Rust allocate_shared_costs", rust_allocate)

            rust_totals = benchmark_rust_totals(args.iterations)
            print_stats("Rust calculate_totals", rust_totals)

    if args.python or args.compare:
        print("\n--- Python Implementation ---")
        python_allocate = benchmark_python_allocate(args.iterations)
        print_stats("Python allocate_shared_costs", python_allocate)

        python_totals = benchmark_python_totals(args.iterations)
        print_stats("Python calculate_totals", python_totals)

    if args.compare and check_rust_health():
        print("\n--- Comparison Summary ---")
        rust_alloc_avg = mean(rust_allocate)
        python_alloc_avg = mean(python_allocate)
        alloc_speedup = python_alloc_avg / rust_alloc_avg if rust_alloc_avg > 0 else 0

        rust_totals_avg = mean(rust_totals)
        python_totals_avg = mean(python_totals)
        totals_speedup = python_totals_avg / rust_totals_avg if rust_totals_avg > 0 else 0

        print(f"\nallocate_shared_costs:")
        print(f"  Python: {python_alloc_avg:.3f} ms")
        print(f"  Rust:   {rust_alloc_avg:.3f} ms")
        print(f"  Speedup: {alloc_speedup:.1f}x")

        print(f"\ncalculate_totals:")
        print(f"  Python: {python_totals_avg:.3f} ms")
        print(f"  Rust:   {rust_totals_avg:.3f} ms")
        print(f"  Speedup: {totals_speedup:.1f}x")

        # Note: Rust has network overhead, so for pure calculation it might not be faster
        # The real benefit is when Rust handles DB queries that would be slow in Python
        print("\nNote: Rust times include HTTP network overhead.")
        print("Real performance gains come from Rust handling DB queries.")


if __name__ == "__main__":
    main()
