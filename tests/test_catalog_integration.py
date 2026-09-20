from lakeos.metadata.catalog import (
    get_dataset,
    register_dataset,
    update_dataset_after_optimization,
)


def test_optimization_updates_catalog(tmp_path):
    dataset_path = (
        tmp_path / "optimized"
    )

    catalog_path = (
        tmp_path / "catalog.json"
    )

    initial_path = (
        dataset_path
        / "year=2025"
        / "month=5"
    )

    initial_path.mkdir(
        parents=True
    )

    register_dataset(
        dataset_name="orders",
        dataset_path=dataset_path,
        layout="none",
        file_count=1,
        total_rows=1000,
        total_size_bytes=5000,
        catalog_path=catalog_path,
    )

    updated_path = (
        dataset_path
        / "year=2025"
        / "month=6"
    )

    updated_path.mkdir(
        parents=True
    )

    metadata = (
        update_dataset_after_optimization(
            dataset_name="orders",
            dataset_path=dataset_path,
            layout="month",
            file_count=12,
            total_rows=1000,
            total_size_bytes=4800,
            run_id="RUN-001",
            catalog_path=catalog_path,
        )
    )

    assert metadata.layout == "month"

    assert metadata.file_count == 12

    assert metadata.total_rows == 1000

    assert metadata.total_size_bytes == 4800

    assert (
        metadata.last_optimization_run_id
        == "RUN-001"
    )

    stored = get_dataset(
        "orders",
        catalog_path=catalog_path,
    )

    assert stored is not None

    assert stored.layout == "month"

    assert stored.file_count == 12

    assert (
        stored.last_optimization_run_id
        == "RUN-001"
    )