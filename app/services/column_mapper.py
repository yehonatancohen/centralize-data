import json
from rapidfuzz import fuzz
from app.config import SYNONYMS_PATH


def load_synonyms() -> dict[str, list[str]]:
    """Load column synonyms from JSON file."""
    with open(SYNONYMS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def auto_map_columns(source_columns: list[str]) -> dict[str, dict]:
    """Auto-map source column names to canonical fields.
    Returns {source_col: {"field": canonical_or_none, "confidence": score}}.
    """
    synonyms = load_synonyms()
    mapping = {}

    for src_col in source_columns:
        src_clean = src_col.strip().lower()
        best_field = None
        best_score = 0

        for canonical, syn_list in synonyms.items():
            for syn in syn_list:
                syn_lower = syn.lower()
                # Exact match
                if src_clean == syn_lower:
                    best_field = canonical
                    best_score = 100
                    break
                # Fuzzy match
                score = fuzz.token_sort_ratio(src_clean, syn_lower)
                if score > best_score:
                    best_score = score
                    best_field = canonical

            if best_score == 100:
                break

        if best_score >= 70:
            mapping[src_col] = {"field": best_field, "confidence": best_score}
        else:
            mapping[src_col] = {"field": None, "confidence": best_score}

    return mapping
