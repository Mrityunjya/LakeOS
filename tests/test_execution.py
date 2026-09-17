from pathlib import Path

from lakeos.optimizer.execution_engine import (
    execute_optimization,
)


DATASET_PATH = Path("data/sample/orders")


def test_month_layout_removes_duplicates(tmp_path):
    output_path = tmp_path / "month"

    report = execute_optimization(
        source_path=DATASET_PATH,
        output_path=output_path,
        layout="month",
    )

    assert report.input_rows == 1_005_000
    assert report.output_rows == 1_000_000
    assert report.duplicates_removed == 5_000


def test_month_layout_creates_expected_partitions(tmp_path):
    output_path = tmp_path / "month"

    report = execute_optimization(
        source_path=DATASET_PATH,
        output_path=output_path,
        layout="month",
    )

    assert report.partitions_created == 12
    assert report.output_files == 12


def test_month_region_layout_creates_more_partitions(tmp_path):
    output_path = tmp_path / "month_region"

    report = execute_optimization(
        source_path=DATASET_PATH,
        output_path=output_path,
        layout="month_region",
    )

    assert report.output_rows == 1_000_000
    assert report.output_files == 60


def test_output_contains_parquet_files(tmp_path):
    output_path = tmp_path / "month"

    execute_optimization(
        source_path=DATASET_PATH,
        output_path=output_path,
        layout="month",
    )

    parquet_files = list(
        output_path.rglob("*.parquet")
    )

    assert len(parquet_files) == 12