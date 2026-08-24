import pandas as pd
import re
from pathlib import Path
from rapidfuzz import fuzz, process


BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"


def normalize(value):

    if pd.isna(value):
        return ""

    value = str(value).lower()

    value = re.sub(
        r"[^a-z0-9\s]",
        " ",
        value
    )

    stopwords = {
        "coal",
        "mine",
        "colliery",
        "collieries",
        "limited",
        "ltd",
        "company",
        "area",
        "project"
    }

    words = [
        x
        for x in value.split()
        if x not in stopwords
    ]

    return " ".join(words)


def find_column(df, candidates):

    normalized = {
        normalize(column): column
        for column in df.columns
    }

    for candidate in candidates:

        key = normalize(candidate)

        if key in normalized:
            return normalized[key]

    return None


def main():

    cco_path = PROCESSED_DIR / "cco_normalized.csv"

    coordinate_path = (
        RAW_DIR /
        "coal_mines_coordinates.xlsx"
    )

    cco = pd.read_csv(
        cco_path,
        dtype=str
    )

    coordinates = pd.read_excel(
        coordinate_path
    )

    # Find columns automatically
    cco_name = find_column(
        cco,
        ["name", "mine name", "mine_name"]
    )

    coord_name = find_column(
        coordinates,
        ["name", "mine name", "mine_name"]
    )

    coord_lat = find_column(
        coordinates,
        ["latitude", "lat"]
    )

    coord_lon = find_column(
        coordinates,
        ["longitude", "lon", "lng"]
    )

    coord_state = find_column(
        coordinates,
        ["state"]
    )

    coord_district = find_column(
        coordinates,
        ["district"]
    )

    if not coord_name:
        raise ValueError(
            "Could not find mine name column"
        )

    if not coord_lat or not coord_lon:
        raise ValueError(
            "Could not find latitude/longitude columns"
        )

    # Normalize
    cco["_match_name"] = (
        cco[cco_name]
        .apply(normalize)
    )

    coordinates["_match_name"] = (
        coordinates[coord_name]
        .apply(normalize)
    )

    # Coordinate dictionary
    choices = coordinates[
        "_match_name"
    ].dropna().unique().tolist()

    results = []

    for _, mine in cco.iterrows():

        mine_name = mine["_match_name"]

        if not mine_name:

            results.append({
                "match_name": "",
                "match_score": 0,
                "match_method": "NO_NAME"
            })

            continue

        # Exact match
        if mine_name in choices:

            results.append({
                "match_name": mine_name,
                "match_score": 100,
                "match_method": "EXACT"
            })

            continue

        # Fuzzy match
        match = process.extractOne(
            mine_name,
            choices,
            scorer=fuzz.token_sort_ratio
        )

        if match:

            matched_name, score, _ = match

            if score >= 90:

                method = "FUZZY_HIGH"

            elif score >= 75:

                method = "FUZZY_REVIEW"

            else:

                method = "NO_MATCH"

            results.append({
                "match_name": matched_name,
                "match_score": score,
                "match_method": method
            })

        else:

            results.append({
                "match_name": "",
                "match_score": 0,
                "match_method": "NO_MATCH"
            })

    result_df = pd.DataFrame(results)

    cco = pd.concat(
        [
            cco.reset_index(drop=True),
            result_df
        ],
        axis=1
    )

    # Attach coordinates
    coordinate_lookup = coordinates[
        [
            "_match_name",
            coord_name,
            coord_lat,
            coord_lon
        ]
    ].drop_duplicates(
        "_match_name"
    )

    coordinate_lookup = coordinate_lookup.rename(
        columns={
            "_match_name": "match_name",
            coord_name: "coordinate_source_name",
            coord_lat: "latitude",
            coord_lon: "longitude"
        }
    )

    merged = cco.merge(
        coordinate_lookup,
        on="match_name",
        how="left"
    )

    output = (
        PROCESSED_DIR /
        "mines_with_coordinates.csv"
    )

    merged.to_csv(
        output,
        index=False,
        encoding="utf-8"
    )

    print(
        f"Saved {len(merged)} mines to {output}"
    )

    print(
        "\nMatch summary:"
    )

    print(
        merged["match_method"]
        .value_counts()
    )


if __name__ == "__main__":
    main()