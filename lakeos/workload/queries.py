from dataclasses import dataclass
from typing import Callable

import polars as pl


@dataclass
class Workload:
    name: str
    description: str
    query: Callable[[pl.LazyFrame], pl.LazyFrame]


def monthly_orders(
    df: pl.LazyFrame,
) -> pl.LazyFrame:
    """
    Workload 1:
    Count orders during a specific month.
    """

    return (
        df
        .filter(
            (pl.col("order_timestamp") >= pl.datetime(2025, 6, 1))
            & (pl.col("order_timestamp") < pl.datetime(2025, 7, 1))
        )
        .select(
            pl.len().alias("order_count")
        )
    )


def regional_monthly_orders(
    df: pl.LazyFrame,
) -> pl.LazyFrame:
    """
    Workload 2:
    Count Chennai orders during a specific month.
    """

    return (
        df
        .filter(
            (pl.col("order_timestamp") >= pl.datetime(2025, 6, 1))
            & (pl.col("order_timestamp") < pl.datetime(2025, 7, 1))
            & (pl.col("region") == "Chennai")
        )
        .select(
            pl.len().alias("order_count")
        )
    )


def revenue_by_region(
    df: pl.LazyFrame,
) -> pl.LazyFrame:
    """
    Workload 3:
    Calculate total revenue by region.
    """

    return (
        df
        .group_by("region")
        .agg(
            pl.col("order_amount")
            .sum()
            .alias("total_revenue")
        )
        .sort(
            "total_revenue",
            descending=True,
        )
    )


WORKLOADS = [
    Workload(
        name="monthly_orders",
        description=(
            "Count orders for June 2025."
        ),
        query=monthly_orders,
    ),
    Workload(
        name="regional_monthly_orders",
        description=(
            "Count Chennai orders for June 2025."
        ),
        query=regional_monthly_orders,
    ),
    Workload(
        name="revenue_by_region",
        description=(
            "Calculate total revenue by region."
        ),
        query=revenue_by_region,
    ),
]

