import pandas as pd
import chardet
from pathlib import Path


def parse_file(file_path: str) -> tuple[pd.DataFrame, list[str]]:
    """Parse an Excel or CSV file into a DataFrame.
    Returns (dataframe, list_of_column_names).
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(file_path, engine="openpyxl")
    elif ext == ".csv":
        # Detect encoding
        with open(file_path, "rb") as f:
            raw = f.read(10000)
        detected = chardet.detect(raw)
        encoding = detected.get("encoding", "utf-8")
        # Try detected encoding, fall back to common ones
        for enc in [encoding, "utf-8-sig", "windows-1255", "iso-8859-8", "latin-1"]:
            try:
                df = pd.read_csv(file_path, encoding=enc)
                break
            except (UnicodeDecodeError, LookupError):
                continue
        else:
            df = pd.read_csv(file_path, encoding="utf-8", errors="replace")
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    # Clean column names
    df.columns = [str(c).strip() for c in df.columns]

    # Drop completely empty rows
    df = df.dropna(how="all").reset_index(drop=True)

    columns = list(df.columns)
    return df, columns
