from pathlib import Path

from lakeos.optimizer.what_if import (
    evaluate_layouts,
    print_what_if_results,
)
from lakeos.workload.queries import (
    WORKLOADS,
)
from lakeos.workload.workload_profiler import (
    profile_workloads,
)


RAW_PATH = Path(
    "data/sample/orders"
)


def main():

    print()
    print("=" * 75)
    print("LAKEOS ADAPTIVE WHAT-IF OPTIMIZER")
    print("=" * 75)

    profiles = profile_workloads(
        str(RAW_PATH)
    )

    print()
    print(
        f"Workloads evaluated: "
        f"{len(profiles)}"
    )

    for profile in profiles:

        results = evaluate_layouts(
            profile
        )

        print_what_if_results(
            profile,
            results,
        )

    print()
    print("=" * 75)
    print("ADAPTIVE WHAT-IF ANALYSIS COMPLETE")
    print("=" * 75)


if __name__ == "__main__":
    main()