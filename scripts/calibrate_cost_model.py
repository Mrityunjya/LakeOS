from pathlib import Path

from lakeos.optimizer.cost_calibration import (
    calibrate_prediction,
    print_calibration_results,
)
from lakeos.optimizer.cost_model import (
    estimate_layout_cost,
)
from lakeos.workload.benchmark import (
    benchmark_workload,
)
from lakeos.workload.workload_profiler import (
    profile_workloads,
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
            f"Calibrating: "
            f"{workload.name}"
        )

        # ----------------------------------------------------
        # Benchmark baseline
        # ----------------------------------------------------

        raw_result = benchmark_workload(
            workload,
            RAW_PATH,
            "raw",
        )

        # ----------------------------------------------------
        # Benchmark optimized layout
        # ----------------------------------------------------

        optimized_result = benchmark_workload(
            workload,
            OPTIMIZED_PATH,
            "optimized",
        )

        # ----------------------------------------------------
        # Model prediction
        # ----------------------------------------------------

        prediction = estimate_layout_cost(
            profile,
            "month",
        )

        # ----------------------------------------------------
        # Calibration
        # ----------------------------------------------------

        record = calibrate_prediction(
            workload=workload.name,
            layout="month",
            predicted_cost=(
                prediction.estimated_cost
            ),
            baseline_time_seconds=(
                raw_result.execution_time_seconds
            ),
            actual_time_seconds=(
                optimized_result.execution_time_seconds
            ),
        )

        records.append(
            record
        )

    print_calibration_results(
        records
    )


if __name__ == "__main__":
    main()