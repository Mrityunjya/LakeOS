from pathlib import Path

from lakeos.optimizer.adaptive_cost_model import (
    print_adaptive_model,
    update_corrections,
)
from lakeos.optimizer.cost_model import (
    estimate_layout_cost,
)
from lakeos.optimizer.feedback import (
    create_feedback_record,
    print_feedback,
)
from lakeos.workload.benchmark import (
    benchmark_workload,
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

OPTIMIZED_PATH = Path(
    "data/lake/optimized/orders"
)

LAYOUT = "month"

TRIALS = 5


def main():

    print()
    print("=" * 75)
    print("LAKEOS ADAPTIVE FEEDBACK LOOP")
    print("=" * 75)

    profiles = profile_workloads(
        str(RAW_PATH)
    )

    records = []

    for workload, profile in zip(
        WORKLOADS,
        profiles,
    ):

        print()
        print(
            f"Evaluating: "
            f"{workload.name}"
        )

        raw_result = benchmark_workload(
            workload=workload,
            dataset_path=RAW_PATH,
            dataset_name="raw",
            trials=TRIALS,
        )

        optimized_result = benchmark_workload(
            workload=workload,
            dataset_path=OPTIMIZED_PATH,
            dataset_name="optimized",
            trials=TRIALS,
        )

        prediction = estimate_layout_cost(
            profile,
            LAYOUT,
        )

        record = create_feedback_record(
            workload=workload.name,
            layout=LAYOUT,
            predicted_cost=(
                prediction.estimated_cost
            ),
            baseline_time_seconds=(
                raw_result.median_time_seconds
            ),
            actual_time_seconds=(
                optimized_result.median_time_seconds
            ),
        )

        records.append(
            record
        )

    print_feedback(
        records
    )

    # --------------------------------------------------------
    # Update adaptive model
    # --------------------------------------------------------

    corrections = update_corrections(
        records
    )

    print_adaptive_model(
        corrections
    )


if __name__ == "__main__":
    main()