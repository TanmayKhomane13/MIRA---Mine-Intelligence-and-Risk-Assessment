import json
import pandas as pd
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

INPUT = (
    BASE_DIR /
    "data" /
    "processed" /
    "mines_validated.csv"
)

OUTPUT = (
    BASE_DIR /
    "data" /
    "mines.geojson"
)


def clean(value):

    if pd.isna(value):
        return None

    return value


def main():

    df = pd.read_csv(
        INPUT,
        dtype=str
    )

    features = []

    for index, row in df.iterrows():

        if row.get("coordinate_status") != "VALID":
            continue

        latitude = float(
            row["latitude"]
        )

        longitude = float(
            row["longitude"]
        )

        mine_id = (
            row.get("mine_id")
            or f"MG-{index + 1:04d}"
        )

        properties = {

            "mine_id":
                mine_id,

            "name":
                clean(row.get("name")),

            "state":
                clean(row.get("state")),

            "district":
                clean(row.get("district")),

            "company":
                clean(row.get("company")),

            "mine_type":
                clean(row.get("mine_type")),

            "ownership":
                clean(row.get("ownership")),

            "status":
                clean(row.get("status")),

            # GIS provenance
            "coordinate_source":
                "reference_dataset",

            "coordinate_status":
                "VALID",

            "coordinate_match_method":
                clean(row.get("match_method")),

            "coordinate_match_score":
                clean(row.get("match_score")),

            # MineGuard prototype fields
            "risk_level":
                "LOW",

            "risk_score":
                0,

            "compliance":
                100
        }

        feature = {

            "type":
                "Feature",

            "geometry": {

                "type":
                    "Point",

                "coordinates": [
                    longitude,
                    latitude
                ]
            },

            "properties":
                properties
        }

        features.append(feature)

    geojson = {

        "type":
            "FeatureCollection",

        "name":
            "MineGuard India Coal Mines",

        "features":
            features
    }

    with open(
        OUTPUT,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            geojson,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(
        f"Generated {OUTPUT}"
    )

    print(
        f"Mines: {len(features)}"
    )


if __name__ == "__main__":
    main()