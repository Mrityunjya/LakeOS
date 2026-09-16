from pathlib import Path
from shutil import rmtree

from lakeos.optimizer.adaptive_cost_model import (
    estimate_adaptive_cost,
    update_corrections,
    print_adaptive_model,
    calculate_confidence,
)
from lakeos.optimizer.execution_engine import (
    execute_optimization,
)
from lakeos.optimizer.feedback import (
    create_feedback_record,
    print_feedback,
)
from lakeos.optimizer.optimization_report import (
    WorkloadReport,
    OptimizationReport,
    calculate_percentage_change,
    calculate_file_count_change,
    calculate_storage_change,
    calculate_workload_weighted_improvement,
    calculate_pruning_prediction_error,
    build_decision_reason,
    save_report,
    print_report,
)
from lakeos.optimizer.what_if import (
    estimate_partition_pruning,
)
from lakeos.metadata.optimization_history import (
    OptimizationObservation,
    append_observations,
    create_run_id,
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

FINAL_OUTPUT_PATH = Path(
    "data/lake/optimized/orders"
)

TEMP_ROOT = Path(
    "data/lake/closed_loop"
)

TRIALS = 5

LAYOUTS = [
    "none",
    "month",
    "month_region",
]

WORKLOAD_FREQUENCIES = {
    "monthly_orders": 0.50,
    "regional_monthly_orders": 0.35,
    "revenue_by_region": 0.15,
}


def weighted_average(
    values: dict[str, float],
) -> float:

    total = 0.0
    weight = 0.0

    for workload, value in values.items():

        frequency = WORKLOAD_FREQUENCIES.get(
            workload,
            0.0,
        )

        total += value * frequency
        weight += frequency

    if weight == 0:
        return 0.0

    return total / weight


def clean_temp_directory() -> None:

    if TEMP_ROOT.exists():
        rmtree(TEMP_ROOT)

    TEMP_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )


def benchmark_layout(
    layout: str,
) -> dict[str, object]:

    output_path = TEMP_ROOT / layout

    report = execute_optimization(
        source_path=RAW_PATH,
        output_path=output_path,
        layout=layout,
    )

    results = {}

    for workload in WORKLOADS:

        result = benchmark_workload(
            workload=workload,
            dataset_path=output_path,
            dataset_name=layout,
            trials=TRIALS,
        )

        results[workload.name] = result

    return {
        "execution": report,
        "benchmarks": results,
        "path": output_path,
    }


def main():

    print()
    print("=" * 80)
    print("LAKEOS CLOSED-LOOP OPTIMIZER")
    print("=" * 80)

    run_id = create_run_id()

    clean_temp_directory()

    # ---------------------------------------------------------
    # 1. PROFILE
    # ---------------------------------------------------------

    print()
    print("=" * 80)
    print("STEP 1 — WORKLOAD PROFILING")
    print("=" * 80)

    profiles = profile_workloads(
        str(RAW_PATH)
    )

    # ---------------------------------------------------------
    # 2. ADAPTIVE PREDICTIONS
    # ---------------------------------------------------------

    print()
    print("=" * 80)
    print("STEP 2 — ADAPTIVE COST PREDICTIONS")
    print("=" * 80)

    predictions = {}

    # Store What-If pruning predictions separately
    # so they can later be compared with observations.
    pruning_predictions = {}

    for profile in profiles:

        predictions[profile.name] = {}
        pruning_predictions[profile.name] = {}

        print()
        print(
            f"WORKLOAD: {profile.name}"
        )

        for layout in LAYOUTS:

            # -------------------------------------------------
            # What-If pruning prediction
            # -------------------------------------------------

            pruning = estimate_partition_pruning(
                profile,
                layout,
            )

            predicted_pruning = float(
                pruning["pruning_ratio"]
            )

            pruning_predictions[
                profile.name
            ][layout] = predicted_pruning

            # -------------------------------------------------
            # Adaptive cost prediction
            # -------------------------------------------------

            cost = estimate_adaptive_cost(
                profile,
                layout,
                pruning_ratio=predicted_pruning,
            )

            predictions[
                profile.name
            ][layout] = cost

            print(
                f"  {layout:<15}"
                f"cost={cost:.4f} "
                f"pruning={predicted_pruning:.2%}"
            )

    # ---------------------------------------------------------
    # 3. EMPIRICAL CANDIDATE EVALUATION
    # ---------------------------------------------------------

    print()
    print("=" * 80)
    print("STEP 3 — EMPIRICAL CANDIDATE EVALUATION")
    print("=" * 80)

    candidate_results = {}

    for layout in LAYOUTS:

        print()
        print("-" * 80)
        print(
            f"EVALUATING LAYOUT: {layout}"
        )
        print("-" * 80)

        candidate_results[
            layout
        ] = benchmark_layout(layout)

        execution = (
            candidate_results[
                layout
            ]["execution"]
        )

        print(
            f"Rows          : "
            f"{execution.output_rows:,}"
        )

        print(
            f"Files         : "
            f"{execution.output_files:,}"
        )

        print(
            f"Size          : "
            f"{execution.output_size_bytes / (1024 ** 2):.2f} MB"
        )

        for workload in WORKLOADS:

            result = (
                candidate_results[
                    layout
                ]["benchmarks"][
                    workload.name
                ]
            )

            print(
                f"{workload.name:<28}"
                f"median={result.median_time_seconds:.6f}s "
                f"p95={result.p95_time_seconds:.6f}s "
                f"pruning={result.pruning_ratio:.2%}"
            )

    # ---------------------------------------------------------
    # 4. EMPIRICAL COST NORMALIZATION
    # ---------------------------------------------------------

    print()
    print("=" * 80)
    print("STEP 4 — EMPIRICAL COST ANALYSIS")
    print("=" * 80)

    baseline_layout = "none"

    empirical_costs = {
        workload.name: {}
        for workload in WORKLOADS
    }

    for workload in WORKLOADS:

        baseline_result = (
            candidate_results[
                baseline_layout
            ]["benchmarks"][
                workload.name
            ]
        )

        baseline_time = (
            baseline_result.median_time_seconds
        )

        print()
        print(
            f"WORKLOAD: {workload.name}"
        )

        for layout in LAYOUTS:

            result = (
                candidate_results[
                    layout
                ]["benchmarks"][
                    workload.name
                ]
            )

            actual_time = (
                result.median_time_seconds
            )

            if baseline_time <= 0:

                relative_cost = 1.0

            else:

                relative_cost = (
                    actual_time
                    / baseline_time
                )

            empirical_costs[
                workload.name
            ][layout] = relative_cost

            print(
                f"  {layout:<15}"
                f"actual_cost={relative_cost:.4f}"
            )

    # ---------------------------------------------------------
    # 5. COMPARE PREDICTION VS REALITY
    # ---------------------------------------------------------

    print()
    print("=" * 80)
    print("STEP 5 — PREDICTION VS REALITY")
    print("=" * 80)

    feedback_records = []
    observations = []

    for workload in WORKLOADS:

        baseline_result = (
            candidate_results[
                baseline_layout
            ]["benchmarks"][
                workload.name
            ]
        )

        baseline_time = (
            baseline_result.median_time_seconds
        )

        for layout in LAYOUTS:

            prediction = (
                predictions[
                    workload.name
                ][layout]
            )

            benchmark_result = (
                candidate_results[
                    layout
                ]["benchmarks"][
                    workload.name
                ]
            )

            actual_time = (
                benchmark_result
                .median_time_seconds
            )

            record = create_feedback_record(
                workload=workload.name,
                layout=layout,
                predicted_cost=prediction,
                baseline_time_seconds=baseline_time,
                actual_time_seconds=actual_time,
            )

            feedback_records.append(
                record
            )

            observations.append(
                OptimizationObservation(
                    run_id=run_id,
                    timestamp=run_id,
                    workload=workload.name,
                    layout=layout,
                    predicted_cost=prediction,
                    actual_cost=(
                        record.actual_relative_cost
                    ),
                    median_time_seconds=(
                        benchmark_result
                        .median_time_seconds
                    ),
                    p95_time_seconds=(
                        benchmark_result
                        .p95_time_seconds
                    ),
                    baseline_time_seconds=(
                        baseline_time
                    ),
                    prediction_error_percentage=(
                        record.error_percentage
                    ),
                )
            )

            predicted_pruning = (
                pruning_predictions[
                    workload.name
                ][layout]
            )

            observed_pruning = (
                benchmark_result.pruning_ratio
            )

            pruning_error = (
                calculate_pruning_prediction_error(
                    predicted_pruning,
                    observed_pruning,
                )
            )

            print(
                f"{workload.name:<28}"
                f"{layout:<15}"
                f"predicted_pruning={predicted_pruning:.2%} "
                f"observed_pruning={observed_pruning:.2%} "
                f"error={pruning_error:+.2f}%"
            )

    print_feedback(
        feedback_records
    )

    append_observations(
        observations
    )

    print()
    print(
        f"Recorded {len(observations)} "
        f"optimization observations."
    )

    print(
        f"Run ID: {run_id}"
    )

    # ---------------------------------------------------------
    # 6. GLOBAL EMPIRICAL DECISION
    # ---------------------------------------------------------

    print()
    print("=" * 80)
    print("STEP 6 — GLOBAL WORKLOAD-AWARE DECISION")
    print("=" * 80)

    layout_scores = {}

    for layout in LAYOUTS:

        workload_costs = {}

        for workload in WORKLOADS:

            workload_costs[
                workload.name
            ] = empirical_costs[
                workload.name
            ][layout]

        score = weighted_average(
            workload_costs
        )

        layout_scores[
            layout
        ] = score

        print(
            f"{layout:<15}"
            f"weighted_cost={score:.4f}"
        )

    selected_layout = min(
        layout_scores,
        key=layout_scores.get,
    )

    print()
    print(
        f"Empirically selected layout: "
        f"{selected_layout}"
    )

    # ---------------------------------------------------------
    # 7. UPDATE ADAPTIVE MODEL
    # ---------------------------------------------------------

    print()
    print("=" * 80)
    print("STEP 7 — MODEL UPDATE")
    print("=" * 80)

    corrections = update_corrections(
        feedback_records
    )

    print_adaptive_model(
        corrections
    )

    # ---------------------------------------------------------
    # 8. FINAL EXECUTION
    # ---------------------------------------------------------

    print()
    print("=" * 80)
    print("STEP 8 — FINAL OPTIMIZATION")
    print("=" * 80)

    final_report = execute_optimization(
        source_path=RAW_PATH,
        output_path=FINAL_OUTPUT_PATH,
        layout=selected_layout,
    )

    print()
    print(
        f"Selected layout : "
        f"{final_report.layout}"
    )

    print(
        f"Input rows      : "
        f"{final_report.input_rows:,}"
    )

    print(
        f"Output rows     : "
        f"{final_report.output_rows:,}"
    )

    print(
        f"Duplicates      : "
        f"{final_report.duplicates_removed:,}"
    )

    print(
        f"Partitions      : "
        f"{final_report.partitions_created:,}"
    )

    print(
        f"Output files    : "
        f"{final_report.output_files:,}"
    )

    print(
        f"Output size     : "
        f"{final_report.output_size_bytes / (1024 ** 2):.2f} MB"
    )

    # ---------------------------------------------------------
    # 9. FINAL VALIDATION
    # ---------------------------------------------------------

    print()
    print("=" * 80)
    print("STEP 9 — FINAL VALIDATION")
    print("=" * 80)

    final_results = {}

    for workload in WORKLOADS:

        result = benchmark_workload(
            workload=workload,
            dataset_path=FINAL_OUTPUT_PATH,
            dataset_name="final",
            trials=TRIALS,
        )

        final_results[
            workload.name
        ] = result

        print()
        print(
            workload.name
        )

        print(
            f"Median : "
            f"{result.median_time_seconds:.6f}s"
        )

        print(
            f"P95    : "
            f"{result.p95_time_seconds:.6f}s"
        )

        print(
            f"Files  : "
            f"{result.available_files}"
        )

        print(
            f"Eligible : "
            f"{result.eligible_files}"
        )

        print(
            f"Pruned : "
            f"{result.pruned_files}"
        )

        print(
            f"Pruning : "
            f"{result.pruning_ratio:.2%}"
        )

    # ---------------------------------------------------------
    # 10. BUILD OPTIMIZATION REPORT
    # ---------------------------------------------------------

    print()
    print("=" * 80)
    print("STEP 10 — BUILDING OPTIMIZATION REPORT")
    print("=" * 80)

    selected_candidate_execution = (
        candidate_results[
            selected_layout
        ]["execution"]
    )

    baseline_execution = (
        candidate_results[
            baseline_layout
        ]["execution"]
    )

    report_workloads = []

    for workload in WORKLOADS:

        baseline_result = (
            candidate_results[
                baseline_layout
            ]["benchmarks"][
                workload.name
            ]
        )

        selected_result = (
            final_results[
                workload.name
            ]
        )

        selected_feedback = next(
            (
                record
                for record in feedback_records
                if (
                    record.workload
                    == workload.name
                    and record.layout
                    == selected_layout
                )
            ),
            None,
        )

        if selected_feedback is None:
            continue

        median_improvement = (
            calculate_percentage_change(
                baseline_result.median_time_seconds,
                selected_result.median_time_seconds,
            )
        )

        p95_improvement = (
            calculate_percentage_change(
                baseline_result.p95_time_seconds,
                selected_result.p95_time_seconds,
            )
        )

        predicted_pruning = (
            pruning_predictions[
                workload.name
            ][selected_layout]
        )

        observed_pruning = (
            selected_result.pruning_ratio
        )

        pruning_error = (
            calculate_pruning_prediction_error(
                predicted_pruning,
                observed_pruning,
            )
        )

        report_workloads.append(
            WorkloadReport(
                workload=workload.name,
                frequency=WORKLOAD_FREQUENCIES[
                    workload.name
                ],
                baseline_time_seconds=(
                    baseline_result
                    .median_time_seconds
                ),
                selected_time_seconds=(
                    selected_result
                    .median_time_seconds
                ),
                median_improvement_percentage=(
                    median_improvement
                ),
                p95_improvement_percentage=(
                    p95_improvement
                ),
                predicted_cost=(
                    selected_feedback
                    .predicted_cost
                ),
                actual_relative_cost=(
                    selected_feedback
                    .actual_relative_cost
                ),
                prediction_error_percentage=(
                    selected_feedback
                    .error_percentage
                ),
                predicted_pruning_ratio=(
                    predicted_pruning
                ),
                observed_pruning_ratio=(
                    observed_pruning
                ),
                pruning_prediction_error_percentage=(
                    pruning_error
                ),
            )
        )

    baseline_files = (
        baseline_execution.output_files
    )

    selected_files = (
        selected_candidate_execution.output_files
    )

    baseline_size = (
        baseline_execution.output_size_bytes
    )

    selected_size = (
        selected_candidate_execution.output_size_bytes
    )

    weighted_improvement = (
        calculate_workload_weighted_improvement(
            report_workloads
        )
    )

    report = OptimizationReport(
        run_id=run_id,
        selected_layout=selected_layout,
        candidate_layouts=LAYOUTS,
        baseline_files=baseline_files,
        selected_files=selected_files,
        baseline_size_bytes=baseline_size,
        selected_size_bytes=selected_size,
        file_count_change_percentage=(
            calculate_file_count_change(
                baseline_files,
                selected_files,
            )
        ),
        storage_change_percentage=(
            calculate_storage_change(
                baseline_size,
                selected_size,
            )
        ),
        workload_weighted_improvement_percentage=(
            weighted_improvement
        ),
        workloads=report_workloads,
        decision_reason=(
            build_decision_reason(
                selected_layout,
                report_workloads,
            )
        ),
        confidence=calculate_confidence(
            len(observations)
        ),
    )

    save_report(
        report
    )

    print_report(
        report
    )

    # ---------------------------------------------------------
    # 11. CLEANUP
    # ---------------------------------------------------------

    if TEMP_ROOT.exists():
        rmtree(TEMP_ROOT)

    print()
    print("=" * 80)
    print("LAKEOS CLOSED LOOP COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
