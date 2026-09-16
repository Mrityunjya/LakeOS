from pathlib import Path

from lakeos.workload.benchmark import (
    print_benchmark_summary,
    run_benchmark,
)
from lakeos.workload.queries import (
    WORKLOADS,
)


RAW_PATH = Path(
    "data/sample/orders"
)

OPTIMIZED_PATH = Path(
    "data/lake/optimized/orders"
)


def main():

    comparisons = run_benchmark(
        raw_path=RAW_PATH,
        optimized_path=OPTIMIZED_PATH,
        workloads=WORKLOADS,
    )

    print_benchmark_summary(
        comparisons
    )


if __name__ == "__main__":
    main()

