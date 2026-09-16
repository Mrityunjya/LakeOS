from pathlib import Path

from lakeos.workload.benchmark import (
    run_benchmark,
    print_benchmark_summary,
)
from lakeos.workload.queries import WORKLOADS


RAW_PATH = Path("data/sample/orders")
OPTIMIZED_PATH = Path("data/lake/optimized/orders")


def main():
    print()
    print("=" * 75)
    print("LAKEOS AUTOMATIC BENCHMARK")
    print("=" * 75)

    results = run_benchmark(
        raw_path=RAW_PATH,
        optimized_path=OPTIMIZED_PATH,
        workloads=WORKLOADS,
    )

    print_benchmark_summary(results)


if __name__ == "__main__":
    main()