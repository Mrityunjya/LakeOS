from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


CATALOG_PATH = Path("data/lakeos_catalog.json")


@dataclass
class DatasetMetadata:
    dataset_name: str
    dataset_path: str
    layout: str
    file_count: int
    total_rows: int
    total_size_bytes: int
    partition_columns: list[str]
    created_at: str
    updated_at: str
    last_optimization_run_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _utc_now() -> str:
    """Return the current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def _load_catalog(
    catalog_path: Path,
) -> dict[str, Any]:
    """
    Load the dataset catalog.

    Returns an empty catalog when the file does not exist,
    is invalid JSON, or does not contain the expected structure.
    """

    if not catalog_path.exists():
        return {"datasets": {}}

    try:
        with catalog_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

    except (json.JSONDecodeError, OSError):
        return {"datasets": {}}

    if not isinstance(data, dict):
        return {"datasets": {}}

    datasets = data.get("datasets")

    if not isinstance(datasets, dict):
        data["datasets"] = {}

    return data


def _save_catalog(
    catalog: dict[str, Any],
    catalog_path: Path,
) -> None:
    """Persist the catalog to disk."""

    catalog_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = catalog_path.with_suffix(
        catalog_path.suffix + ".tmp"
    )

    with temporary_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            catalog,
            file,
            indent=2,
            ensure_ascii=False,
        )

    temporary_path.replace(catalog_path)


def infer_partition_columns(
    dataset_path: Path,
) -> list[str]:
    """
    Infer partition columns from Hive-style directories.

    Example:
        data/month=2026-01/region=Chennai

    returns:
        ["month", "region"]
    """

    columns: set[str] = set()

    if not dataset_path.exists():
        return []

    for path in dataset_path.rglob("*"):

        if not path.is_dir():
            continue

        name = path.name

        if "=" not in name:
            continue

        column, value = name.split(
            "=",
            1,
        )

        column = column.strip()
        value = value.strip()

        if column and value:
            columns.add(column)

    return sorted(columns)


def _build_metadata(
    dataset_name: str,
    dataset_path: Path,
    layout: str,
    file_count: int,
    total_rows: int,
    total_size_bytes: int,
    created_at: str,
    run_id: str | None,
) -> DatasetMetadata:
    """Build a DatasetMetadata object."""

    return DatasetMetadata(
        dataset_name=dataset_name,
        dataset_path=str(dataset_path),
        layout=layout,
        file_count=int(file_count),
        total_rows=int(total_rows),
        total_size_bytes=int(total_size_bytes),
        partition_columns=infer_partition_columns(
            dataset_path
        ),
        created_at=created_at,
        updated_at=_utc_now(),
        last_optimization_run_id=run_id,
    )


def register_dataset(
    dataset_name: str,
    dataset_path: str | Path,
    layout: str,
    file_count: int,
    total_rows: int,
    total_size_bytes: int,
    catalog_path: Path = CATALOG_PATH,
    run_id: str | None = None,
) -> DatasetMetadata:
    """
    Register a dataset in the LAKEOS catalog.

    If the dataset already exists, its original created_at
    timestamp is preserved.
    """

    dataset_path = Path(dataset_path)

    catalog = _load_catalog(
        catalog_path
    )

    datasets = catalog.setdefault(
        "datasets",
        {},
    )

    existing = datasets.get(
        dataset_name
    )

    now = _utc_now()

    if isinstance(existing, dict):
        created_at = existing.get(
            "created_at",
            now,
        )

        previous_run_id = existing.get(
            "last_optimization_run_id"
        )

    else:
        created_at = now
        previous_run_id = None

    effective_run_id = (
        run_id
        if run_id is not None
        else previous_run_id
    )

    metadata = _build_metadata(
        dataset_name=dataset_name,
        dataset_path=dataset_path,
        layout=layout,
        file_count=file_count,
        total_rows=total_rows,
        total_size_bytes=total_size_bytes,
        created_at=created_at,
        run_id=effective_run_id,
    )

    datasets[dataset_name] = metadata.to_dict()

    _save_catalog(
        catalog,
        catalog_path,
    )

    return metadata


def update_dataset_after_optimization(
    dataset_name: str,
    dataset_path: str | Path,
    layout: str,
    file_count: int,
    total_rows: int,
    total_size_bytes: int,
    run_id: str,
    catalog_path: Path = CATALOG_PATH,
) -> DatasetMetadata:
    """
    Update dataset metadata after a successful optimization run.

    The optimization run ID is always replaced with the supplied
    run_id because this represents the latest optimization.
    """

    dataset_path = Path(dataset_path)

    catalog = _load_catalog(
        catalog_path
    )

    datasets = catalog.setdefault(
        "datasets",
        {},
    )

    existing = datasets.get(
        dataset_name
    )

    now = _utc_now()

    if isinstance(existing, dict):
        created_at = existing.get(
            "created_at",
            now,
        )
    else:
        created_at = now

    metadata = DatasetMetadata(
        dataset_name=dataset_name,
        dataset_path=str(dataset_path),
        layout=layout,
        file_count=int(file_count),
        total_rows=int(total_rows),
        total_size_bytes=int(total_size_bytes),
        partition_columns=infer_partition_columns(
            dataset_path
        ),
        created_at=created_at,
        updated_at=now,
        last_optimization_run_id=run_id,
    )

    datasets[dataset_name] = metadata.to_dict()

    _save_catalog(
        catalog,
        catalog_path,
    )

    return metadata


def get_dataset(
    dataset_name: str,
    catalog_path: Path = CATALOG_PATH,
) -> DatasetMetadata | None:
    """Return metadata for a single dataset."""

    catalog = _load_catalog(
        catalog_path
    )

    raw = catalog.get(
        "datasets",
        {},
    ).get(
        dataset_name
    )

    if not isinstance(raw, dict):
        return None

    try:
        return DatasetMetadata(
            **raw
        )
    except TypeError:
        return None


def list_datasets(
    catalog_path: Path = CATALOG_PATH,
) -> list[DatasetMetadata]:
    """Return all valid dataset metadata entries."""

    catalog = _load_catalog(
        catalog_path
    )

    datasets = catalog.get(
        "datasets",
        {},
    )

    results: list[DatasetMetadata] = []

    for metadata in datasets.values():

        if not isinstance(metadata, dict):
            continue

        try:
            results.append(
                DatasetMetadata(
                    **metadata
                )
            )
        except TypeError:
            continue

    return results


def print_catalog(
    catalog_path: Path = CATALOG_PATH,
) -> None:
    """Print a human-readable dataset catalog."""

    datasets = list_datasets(
        catalog_path
    )

    print()
    print("=" * 75)
    print("LAKEOS DATASET CATALOG")
    print("=" * 75)

    if not datasets:
        print("No datasets registered.")
        return

    for metadata in datasets:

        print()

        print(
            f"Dataset       : "
            f"{metadata.dataset_name}"
        )

        print(
            f"Path          : "
            f"{metadata.dataset_path}"
        )

        print(
            f"Layout        : "
            f"{metadata.layout}"
        )

        print(
            f"Files         : "
            f"{metadata.file_count:,}"
        )

        print(
            f"Rows          : "
            f"{metadata.total_rows:,}"
        )

        print(
            f"Size          : "
            f"{metadata.total_size_bytes / (1024 ** 2):.2f} MB"
        )

        print(
            f"Partitions    : "
            f"{', '.join(metadata.partition_columns) or 'none'}"
        )

        print(
            f"Created       : "
            f"{metadata.created_at}"
        )

        print(
            f"Updated       : "
            f"{metadata.updated_at}"
        )

        print(
            f"Last run      : "
            f"{metadata.last_optimization_run_id or 'none'}"
        )