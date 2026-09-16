from pathlib import Path

from lakeos.optimizer.execution_engine import (
    execute_optimization,
)
from lakeos.profiler.data_profiler import (
    profile_dataset,
)


SOURCE_PATH = Path("data/sample/orders")
OUTPUT_PATH = Path("data/lake/optimized/orders")


def main():
    print("Running LAKEOS execution engine...")

    profile = profile_dataset(SOURCE_PATH)

    report = execute_optimization(
        profile,
        OUTPUT_PATH,
    )

    print()
    print("EXECUTION REPORT")
    print("-" * 70)
    print(report.to_dict())


if __name__ == "__main__":
    main()