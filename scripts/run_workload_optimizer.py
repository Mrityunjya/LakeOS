from pathlib import Path

from lakeos.optimizer.workload_optimizer import (
    optimize_for_workload,
    print_workload_optimization,
)
from lakeos.workload.workload_profiler import (
    profile_workloads,
)


DATASET_PATH = Path(
    "data/sample/orders"
)


def main():

    profiles = profile_workloads(
        str(DATASET_PATH)
    )

    evaluations = optimize_for_workload(
        profiles
    )

    print_workload_optimization(
        evaluations
    )


if __name__ == "__main__":
    main()