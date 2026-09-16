from dataclasses import asdict, dataclass
from typing import Any

from lakeos.profiler.data_profiler import (
    DatasetProfile,
)


@dataclass
class Recommendation:
    category: str
    severity: str
    title: str
    explanation: str
    action: str
    evidence: dict[str, Any]


def analyze_file_layout(
    profile: DatasetProfile,
) -> list[Recommendation]:

    recommendations = []

    average_size = (
        profile.average_file_size_bytes
    )

    # Files smaller than 128 MB are generally candidates
    # for compaction in a data-lake environment.
    if average_size < 128 * 1024 * 1024:
        recommendations.append(
            Recommendation(
                category="storage",
                severity="high",
                title="Small-file fragmentation detected",
                explanation=(
                    "The dataset contains many Parquet files "
                    "with relatively small average file sizes. "
                    "This can increase metadata overhead and "
                    "file-open operations during queries."
                ),
                action=(
                    "Compact multiple small Parquet files "
                    "into fewer larger files."
                ),
                evidence={
                    "file_count": profile.file_count,
                    "average_file_size_mb": round(
                        average_size / (1024 * 1024),
                        2,
                    ),
                },
            )
        )

    file_sizes = [
        file.size_bytes
        for file in profile.files
    ]

    if file_sizes:
        size_ratio = (
            max(file_sizes)
            / max(min(file_sizes), 1)
        )

        if size_ratio >= 2:
            recommendations.append(
                Recommendation(
                    category="storage",
                    severity="medium",
                    title="File-size imbalance detected",
                    explanation=(
                        "The dataset contains files with "
                        "substantially different physical sizes."
                    ),
                    action=(
                        "Normalize file sizes during the "
                        "next compaction cycle."
                    ),
                    evidence={
                        "smallest_file_mb": round(
                            min(file_sizes)
                            / (1024 * 1024),
                            2,
                        ),
                        "largest_file_mb": round(
                            max(file_sizes)
                            / (1024 * 1024),
                            2,
                        ),
                        "size_ratio": round(
                            size_ratio,
                            2,
                        ),
                    },
                )
            )

    return recommendations


def analyze_data_quality(
    profile: DatasetProfile,
) -> list[Recommendation]:

    recommendations = []

    for column in profile.columns:

        if column.null_percentage >= 5:
            severity = "high"
        elif column.null_percentage > 0:
            severity = "medium"
        else:
            continue

        recommendations.append(
            Recommendation(
                category="data_quality",
                severity=severity,
                title=(
                    f"Missing values in '{column.name}'"
                ),
                explanation=(
                    f"The column contains "
                    f"{column.null_percentage:.2f}% "
                    "missing values."
                ),
                action=(
                    "Evaluate whether missing values "
                    "should be imputed, normalized, "
                    "or explicitly retained."
                ),
                evidence={
                    "column": column.name,
                    "null_count": column.null_count,
                    "null_percentage": (
                        column.null_percentage
                    ),
                },
            )
        )

    if profile.duplicate_order_ids > 0:
        recommendations.append(
            Recommendation(
                category="data_quality",
                severity="high",
                title="Duplicate records detected",
                explanation=(
                    "Multiple records share the same "
                    "order_id across the dataset."
                ),
                action=(
                    "Deduplicate records using the "
                    "dataset's logical primary key."
                ),
                evidence={
                    "duplicate_order_ids": (
                        profile.duplicate_order_ids
                    ),
                },
            )
        )

    return recommendations


def analyze_partitioning(
    profile: DatasetProfile,
) -> list[Recommendation]:

    recommendations = []

    # ----------------------------------------------
    # Timestamp-based partitioning
    # ----------------------------------------------

    timestamp_column = None

    for column in profile.columns:
        if (
            column.name == "order_timestamp"
            and (
                "Datetime" in column.dtype
                or "Date" in column.dtype
            )
        ):
            timestamp_column = column
            break

    if timestamp_column is not None:
        recommendations.append(
            Recommendation(
                category="partitioning",
                severity="medium",
                title="Time-based partitioning candidate",
                explanation=(
                    "The dataset contains a timestamp "
                    "column spanning a meaningful time range. "
                    "Time-based partitioning can reduce "
                    "data scanned for time-bounded queries."
                ),
                action=(
                    "Evaluate partitioning by order date, "
                    "month, or another workload-appropriate "
                    "time granularity."
                ),
                evidence={
                    "column": timestamp_column.name,
                    "minimum": profile.timestamp_min,
                    "maximum": profile.timestamp_max,
                },
            )
        )

    # ----------------------------------------------
    # Detect categorical skew
    # ----------------------------------------------

    total_rows = profile.total_rows

    if total_rows > 0:
        region_distribution = (
            profile.region_distribution
        )

        if region_distribution:

            counts = list(
                region_distribution.values()
            )

            largest_count = max(counts)
            smallest_count = min(counts)

            skew_ratio = (
                largest_count
                / max(smallest_count, 1)
            )

            if skew_ratio >= 3:
                recommendations.append(
                    Recommendation(
                        category="partitioning",
                        severity="high",
                        title="Partition-key skew detected",
                        explanation=(
                            "The region distribution is "
                            "significantly uneven. Partitioning "
                            "directly by region could create "
                            "imbalanced partitions."
                        ),
                        action=(
                            "Avoid using region as the sole "
                            "partition key. Evaluate time-based "
                            "partitioning or a composite strategy."
                        ),
                        evidence={
                            "largest_group": (
                                max(
                                    region_distribution,
                                    key=region_distribution.get,
                                )
                            ),
                            "largest_count": (
                                largest_count
                            ),
                            "smallest_count": (
                                smallest_count
                            ),
                            "skew_ratio": round(
                                skew_ratio,
                                2,
                            ),
                        },
                    )
                )

    return recommendations


def generate_recommendations(
    profile: DatasetProfile,
) -> list[Recommendation]:

    recommendations = []

    recommendations.extend(
        analyze_file_layout(profile)
    )

    recommendations.extend(
        analyze_data_quality(profile)
    )

    recommendations.extend(
        analyze_partitioning(profile)
    )

    return recommendations


def print_recommendations(
    recommendations: list[Recommendation],
) -> None:

    print()
    print("=" * 70)
    print("LAKEOS OPTIMIZATION RECOMMENDATIONS")
    print("=" * 70)

    if not recommendations:
        print("No optimization issues detected.")
        return

    for index, recommendation in enumerate(
        recommendations,
        start=1,
    ):
        print()
        print(
            f"[{index}] "
            f"{recommendation.severity.upper()} | "
            f"{recommendation.category.upper()}"
        )

        print(
            f"Title      : "
            f"{recommendation.title}"
        )

        print(
            f"Explanation: "
            f"{recommendation.explanation}"
        )

        print(
            f"Action     : "
            f"{recommendation.action}"
        )

        print(
            f"Evidence   : "
            f"{recommendation.evidence}"
        )

    print()
    print("=" * 70)