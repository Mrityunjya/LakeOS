from pathlib import Path

from lakeos.optimizer.execution_engine import (
    execute_optimization,
)


RAW_PATH = Path(
    "data/sample/orders"
)

OUTPUT_PATH = Path(
    "data/lake/optimized/orders"
)


def main():

    layout = "month"

    report = execute_optimization(
        source_path=RAW_PATH,
        output_path=OUTPUT_PATH,
        layout=layout,
    )

    print()
    print(
        f"Final layout: "
        f"{report.layout}"
    )

    print(
        f"Rows: "
        f"{report.input_rows:,}"
        f" -> "
        f"{report.output_rows:,}"
    )


if __name__ == "__main__":
    main()