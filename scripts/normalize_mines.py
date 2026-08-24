import pandas as pd
import re
import unicodedata
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def normalize_text(value):

    if pd.isna(value):
        return ""

    value = str(value)

    # Unicode normalization
    value = unicodedata.normalize("NFKD", value)

    # Lowercase
    value = value.lower()

    # Replace punctuation with spaces
    value = re.sub(r"[^a-z0-9\s]", " ", value)

    # Remove common words that create matching noise
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
        word
        for word in value.split()
        if word not in stopwords
    ]

    # Remove duplicate whitespace
    return " ".join(words).strip()


def normalize_dataframe(df):

    df = df.copy()

    for column in [
        "name",
        "mine_name",
        "company",
        "operator",
        "state",
        "district"
    ]:

        if column in df.columns:

            df[f"{column}_normalized"] = (
                df[column]
                .apply(normalize_text)
            )

    return df


def main():

    cco_file = RAW_DIR / "cco_mines.csv"

    df = pd.read_csv(
        cco_file,
        dtype=str
    )

    df = normalize_dataframe(df)

    output = PROCESSED_DIR / "cco_normalized.csv"

    df.to_csv(
        output,
        index=False,
        encoding="utf-8"
    )

    print(f"Saved: {output}")
    print(f"Records: {len(df)}")


if __name__ == "__main__":
    main()