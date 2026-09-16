from pathlib import Path

from lakeos.optimizer.execution_engine import (
    execute_optimization,
)
from lakeos.optimizer.workload_optimizer import (
    optimize_for_workload,
    print_workload_optimization,
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


def main():

    print()
    print("=" * 75)
    print("LAKEOS AUTOMATIC OPTIMIZATION")
    print("=" * 75)

    # --------------------------------------------------------
    # 1. Profile workloads
    # --------------------------------------------------------

    profiles = profile_workloads(
        str(RAW_PATH)
    )

    # --------------------------------------------------------
    # 2. Evaluate candidate layouts
    # --------------------------------------------------------

    evaluations = optimize_for_workload(
        profiles
    )

    print_workload_optimization(
        evaluations
    )

    # --------------------------------------------------------
    # 3. Select global layout
    # --------------------------------------------------------

    selected_layout = (
        evaluations[0].layout
    )

    print()
    print(
        f"Optimizer selected: "
        f"{selected_layout}"
    )

    # --------------------------------------------------------
    # 4. Execute selected layout
    # --------------------------------------------------------

    report = execute_optimization(
        source_path=RAW_PATH,
        output_path=OUTPUT_PATH,
        layout=selected_layout,
    )

    # --------------------------------------------------------
    # 5. Final result
    # --------------------------------------------------------

    print()
    print("=" * 75)
    print("LAKEOS OPTIMIZATION RESULT")
    print("=" * 75)

    print(
        f"Selected layout : "
        f"{report.layout}"
    )

    print(
        f"Input rows      : "
        f"{report.input_rows:,}"
    )

    print(
        f"Output rows     : "
        f"{report.output_rows:,}"
    )

    print(
        f"Duplicates      : "
        f"{report.duplicates_removed:,}"
    )

    print(
        f"Partitions      : "
        f"{report.partitions_created:,}"
    )

    print(
        f"Output files    : "
        f"{report.output_files:,}"
    )

    print(
        f"Output size     : "
        f"{report.output_size_bytes / (1024 ** 2):.2f} MB"
    )

    print()
    print("=" * 75)


if __name__ == "__main__":
    main()