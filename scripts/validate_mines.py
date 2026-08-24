import pandas as pd
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

INPUT = (
    BASE_DIR /
    "data" /
    "processed" /
    "mines_with_coordinates.csv"
)

OUTPUT = (
    BASE_DIR /
    "data" /
    "processed" /
    "mines_validated.csv"
)


def valid_coordinate(lat, lon):

    try:

        lat = float(lat)
        lon = float(lon)

    except (TypeError, ValueError):

        return False

    # India bounding box with some margin
    if not (
        6 <= lat <= 38
    ):
        return False

    if not (
        67 <= lon <= 98
    ):
        return False

    return True


def main():

    df = pd.read_csv(
        INPUT,
        dtype=str
    )

    df["coordinate_valid"] = df.apply(
        lambda row:
            valid_coordinate(
                row.get("latitude"),
                row.get("longitude")
            ),
        axis=1
    )

    df["latitude"] = pd.to_numeric(
        df["latitude"],
        errors="coerce"
    )

    df["longitude"] = pd.to_numeric(
        df["longitude"],
        errors="coerce"
    )

    df["coordinate_status"] = (
        df["coordinate_valid"]
        .map({
            True: "VALID",
            False: "MISSING_OR_INVALID"
        })
    )

    df.to_csv(
        OUTPUT,
        index=False
    )

    print(
        "Total:",
        len(df)
    )

    print(
        "Valid:",
        df["coordinate_valid"].sum()
    )

    print(
        "Missing/invalid:",
        (~df["coordinate_valid"]).sum()
    )


if __name__ == "__main__":
    main()