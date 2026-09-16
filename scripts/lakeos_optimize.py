from pathlib import Path

from lakeos.optimizer.adaptive_cost_model import (
    estimate_adaptive_cost,
)
from lakeos.optimizer.execution_engine import (
    execute_optimization,
)
from lakeos.optimizer.what_if import (
    evaluate_layouts,
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

OUTPUT_PATH = Path(
    "data/lake/optimized/orders"
)

TRIALS = 5


def main():

    print()
    print("=" * 75)
    print("LAKEOS END-TO-END OPTIMIZATION")
    print("=" * 75)

    # --------------------------------------------------------
    # 1. Profile workload
    # --------------------------------------------------------

    profiles = profile_workloads(
        str(RAW_PATH)
    )

    # --------------------------------------------------------
    # 2. Evaluate candidate layouts
    # --------------------------------------------------------

    layout_scores = {}

    for profile in profiles:

        results = evaluate_layouts(
            profile
        )

        for result in results:

            layout_scores.setdefault(
                result.layout,
                [],
            )

            layout_scores[
                result.layout
            ].append(
                result.predicted_cost
            )

    # --------------------------------------------------------
    # 3. Global layout decision
    # --------------------------------------------------------

    global_costs = {
        layout: sum(costs) / len(costs)
        for layout, costs
        in layout_scores.items()
    }

    selected_layout = min(
        global_costs,
        key=global_costs.get,
    )

    print()
    print("=" * 75)
    print("GLOBAL LAYOUT DECISION")
    print("=" * 75)

    for layout, cost in sorted(
        global_costs.items(),
        key=lambda item: item[1],
    ):

        print(
            f"{layout:<15}"
            f" {cost:.4f}"
        )

    print()
    print(
        f"Selected layout: "
        f"{selected_layout}"
    )

    # --------------------------------------------------------
    # 4. Execute
    # --------------------------------------------------------

    report = execute_optimization(
        source_path=RAW_PATH,
        output_path=OUTPUT_PATH,
        layout=selected_layout,
    )

    print()
    print("=" * 75)
    print("EXECUTION COMPLETE")
    print("=" * 75)

    print(
        f"Layout      : "
        f"{report.layout}"
    )

    print(
        f"Input rows  : "
        f"{report.input_rows:,}"
    )

    print(
        f"Output rows : "
        f"{report.output_rows:,}"
    )

    print(
        f"Duplicates  : "
        f"{report.duplicates_removed:,}"
    )

    print(
        f"Files       : "
        f"{report.output_files:,}"
    )

    # --------------------------------------------------------
    # 5. Benchmark selected layout
    # --------------------------------------------------------

    print()
    print("=" * 75)
    print("POST-OPTIMIZATION BENCHMARK")
    print("=" * 75)

    for workload in WORKLOADS:

        result = benchmark_workload(
            workload=workload,
            dataset_path=OUTPUT_PATH,
            dataset_name="optimized",
            trials=TRIALS,
        )

        print()
        print(
            f"{workload.name}"
        )

        print(
            f"Median: "
            f"{result.median_time_seconds:.6f}s"
        )

        print(
            f"P95   : "
            f"{result.p95_time_seconds:.6f}s"
        )

    print()
    print("=" * 75)
    print("LAKEOS OPTIMIZATION COMPLETE")
    print("=" * 75)


if __name__ == "__main__":
    main()