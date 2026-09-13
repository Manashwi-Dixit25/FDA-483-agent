from pathlib import Path
import re

import pandas as pd


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[2]

RAW_DATA_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"

INPUT_FILE = RAW_DATA_DIR / "fda_foia_closed_log_latest.xlsx"
OUTPUT_FILE = PROCESSED_DATA_DIR / "likely_483_requests.xlsx"


# =========================================================
# COLUMN NAMES
# =========================================================

REQUEST_DETAILS_COLUMN = "Request Details"


# =========================================================
# 483 DETECTION PATTERNS
# =========================================================

# These patterns identify rows that are worth sending
# to the next stage of processing.
#
# IMPORTANT:
# This is only a CANDIDATE filter.
# It does NOT decide whether the request is truly
# asking for a Form FDA 483.

LIKELY_483_PATTERNS = [
    r"\bform\s+fda\s+483\b",
    r"\bfda\s+form\s+483\b",
    r"\bform\s+483\b",
    r"\bfda\s+483\b",
    r"\b483\s+observations?\b",
    r"\b483\s+request\b",
    r"\brequest(?:ed|ing)?\s+(?:a\s+)?483\b",
]


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def build_search_text(row):
    """
    Combine useful text columns into one string.

    We use multiple columns because the reference to a
    Form 483 may appear outside Request Details.
    """

    values = []

    for column in [
        "Request Details",
        "Requester Name with Company",
        "Close Case Reason",
    ]:
        if column in row.index:
            value = row[column]

            if pd.notna(value):
                values.append(str(value))

    return " ".join(values)


def find_483_matches(text):
    """
    Find all candidate 483 patterns in a piece of text.
    """

    matches = []

    text_lower = text.lower()

    for pattern in LIKELY_483_PATTERNS:
        if re.search(pattern, text_lower):
            matches.append(pattern)

    return matches


def is_likely_483(text):
    """
    Return True when the row contains a strong Form 483
    related phrase.

    This is intentionally conservative.

    The AI stage will make the final semantic decision.
    """

    return len(find_483_matches(text)) > 0


# =========================================================
# MAIN FILTER
# =========================================================

def filter_likely_483_requests():
    """
    Read the FDA closed log, identify likely Form 483
    requests, and save them into a processed Excel file.
    """

    print("=" * 60)
    print("FDA 483 CANDIDATE FILTER")
    print("=" * 60)

    # -----------------------------------------------------
    # Check input file
    # -----------------------------------------------------

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file was not found:\n{INPUT_FILE}\n\n"
            "Run download.py first."
        )

    print()
    print("Reading FDA closed log:")
    print(INPUT_FILE)

    # -----------------------------------------------------
    # Create processed directory
    # -----------------------------------------------------

    PROCESSED_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # -----------------------------------------------------
    # Read Excel
    # -----------------------------------------------------

    df = pd.read_excel(INPUT_FILE)

    print()
    print(f"Total rows in FDA log: {len(df)}")

    # -----------------------------------------------------
    # Check required column
    # -----------------------------------------------------

    if REQUEST_DETAILS_COLUMN not in df.columns:
        raise ValueError(
            f"Expected column '{REQUEST_DETAILS_COLUMN}' "
            f"was not found.\n\n"
            f"Available columns:\n{list(df.columns)}"
        )

    # -----------------------------------------------------
    # Build searchable text
    # -----------------------------------------------------

    df["_search_text"] = df.apply(
        build_search_text,
        axis=1,
    )

    # -----------------------------------------------------
    # Find likely 483 rows
    # -----------------------------------------------------

    df["_is_likely_483"] = df["_search_text"].apply(
        is_likely_483
    )

    df["_matched_patterns"] = df["_search_text"].apply(
        lambda text: ", ".join(find_483_matches(text))
    )

    candidates = df[df["_is_likely_483"]].copy()

    # -----------------------------------------------------
    # Add useful metadata
    # -----------------------------------------------------

    candidates.insert(
        0,
        "Candidate Number",
        range(1, len(candidates) + 1),
    )

    candidates["Candidate Status"] = "PENDING_AI_REVIEW"

    # -----------------------------------------------------
    # Remove internal helper columns
    # -----------------------------------------------------

    candidates = candidates.drop(
        columns=["_is_likely_483"],
    )

    # Keep _search_text and _matched_patterns for now.
    #
    # These are useful for debugging and understanding
    # why a row was selected.

    # -----------------------------------------------------
    # Save output
    # -----------------------------------------------------

    candidates.to_excel(
        OUTPUT_FILE,
        index=False,
    )

    # -----------------------------------------------------
    # Print summary
    # -----------------------------------------------------

    print()
    print("=" * 60)
    print("FILTER COMPLETE")
    print("=" * 60)

    print()
    print(f"Total FDA rows:       {len(df)}")
    print(f"Likely 483 rows:      {len(candidates)}")
    print(f"Rows filtered out:    {len(df) - len(candidates)}")

    print()
    print("Output file:")
    print(OUTPUT_FILE)

    print()
    print("Candidate status:")
    print("PENDING_AI_REVIEW")

    return candidates


# =========================================================
# PROGRAM ENTRY POINT
# =========================================================

def main():
    filter_likely_483_requests()


if __name__ == "__main__":
    main()