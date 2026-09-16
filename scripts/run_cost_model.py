from pathlib import Path

from lakeos.optimizer.cost_model import (
    evaluate_candidates,
    print_cost_model,
)
from lakeos.workload.workload_profiler import (
    profile_workloads,
)


DATASET_PATH = Path(
    "data/sample/orders"
)


def main():

    workloads = profile_workloads(
        str(DATASET_PATH)
    )

    for workload in workloads:

        candidates = evaluate_candidates(
            workload
        )

        print_cost_model(
            workload,
            candidates,
        )


if __name__ == "__main__":
    main()