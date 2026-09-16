from dataclasses import asdict, dataclass
from typing import Any

import polars as pl

from lakeos.workload.queries import WORKLOADS, Workload


@dataclass
class WorkloadProfile:
    name: str
    description: str

    filter_columns: list[str]
    time_filter: bool
    aggregation: bool

    estimated_selectivity: float

    workload_type: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ============================================================
# WORKLOAD ANALYSIS
# ============================================================

def profile_workload(
    workload: Workload,
    dataset_path: str,
) -> WorkloadProfile:
    """
    Analyze a workload and classify its query characteristics.

    This is the first layer of the LAKEOS workload-aware
    optimization system.
    """

    lazy_df = pl.scan_parquet(
        f"{dataset_path}/**/*.parquet"
    )

    # --------------------------------------------------------
    # Detect filter columns from the workload definition
    # --------------------------------------------------------

    filter_columns: list[str] = []

    query_name = workload.name

    if query_name == "monthly_orders":
        filter_columns = [
            "order_timestamp"
        ]

    elif query_name == "regional_monthly_orders":
        filter_columns = [
            "order_timestamp",
            "region",
        ]

    # --------------------------------------------------------
    # Detect workload characteristics
    # --------------------------------------------------------

    time_filter = (
        "order_timestamp"
        in filter_columns
    )

    aggregation = (
        query_name
        == "revenue_by_region"
    )

    # --------------------------------------------------------
    # Estimate selectivity
    # --------------------------------------------------------

    total_rows = (
        lazy_df
        .select(
            pl.len().alias("count")
        )
        .collect()
        .item()
    )

    if query_name == "monthly_orders":

        filtered_rows = (
            lazy_df
            .filter(
                (
                    pl.col("order_timestamp")
                    >= pl.datetime(2025, 6, 1)
                )
                & (
                    pl.col("order_timestamp")
                    < pl.datetime(2025, 7, 1)
                )
            )
            .select(
                pl.len()
            )
            .collect()
            .item()
        )

    elif query_name == "regional_monthly_orders":

        filtered_rows = (
            lazy_df
            .filter(
                (
                    pl.col("order_timestamp")
                    >= pl.datetime(2025, 6, 1)
                )
                & (
                    pl.col("order_timestamp")
                    < pl.datetime(2025, 7, 1)
                )
                & (
                    pl.col("region")
                    == "Chennai"
                )
            )
            .select(
                pl.len()
            )
            .collect()
            .item()
        )

    else:
        filtered_rows = total_rows

    selectivity = (
        filtered_rows / total_rows
        if total_rows > 0
        else 1.0
    )

    # --------------------------------------------------------
    # Classify workload
    # --------------------------------------------------------

    if aggregation and not time_filter:

        workload_type = "full_scan_aggregation"

    elif time_filter and len(filter_columns) == 1:

        workload_type = "time_range"

    elif time_filter and len(filter_columns) > 1:

        workload_type = "time_range_with_dimension"

    else:

        workload_type = "general"

    return WorkloadProfile(
        name=workload.name,
        description=workload.description,

        filter_columns=filter_columns,

        time_filter=time_filter,

        aggregation=aggregation,

        estimated_selectivity=round(
            selectivity,
            4,
        ),

        workload_type=workload_type,
    )


# ============================================================
# PROFILE ALL WORKLOADS
# ============================================================

def profile_workloads(
    dataset_path: str,
) -> list[WorkloadProfile]:
    """
    Profile every registered LAKEOS workload.
    """

    profiles = []

    for workload in WORKLOADS:

        print(
            f"Profiling workload: "
            f"{workload.name}"
        )

        profile = profile_workload(
            workload,
            dataset_path,
        )

        profiles.append(profile)

    return profiles


# ============================================================
# HUMAN-READABLE OUTPUT
# ============================================================

def print_workload_profiles(
    profiles: list[WorkloadProfile],
) -> None:
    """Print workload analysis."""

    print()
    print("=" * 75)
    print("LAKEOS WORKLOAD PROFILES")
    print("=" * 75)

    for profile in profiles:

        print()

        print(
            f"WORKLOAD: "
            f"{profile.name}"
        )

        print("-" * 75)

        print(
            f"Type          : "
            f"{profile.workload_type}"
        )

        print(
            f"Filters       : "
            f"{', '.join(profile.filter_columns) or 'None'}"
        )

        print(
            f"Time filter   : "
            f"{profile.time_filter}"
        )

        print(
            f"Aggregation   : "
            f"{profile.aggregation}"
        )

        print(
            f"Selectivity   : "
            f"{profile.estimated_selectivity:.2%}"
        )

    print()
    print("=" * 75)
    