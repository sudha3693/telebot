import logging
import re
from difflib import SequenceMatcher
from typing import Any, Iterable, Sequence

from sqlalchemy import Index, func, or_
from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)
SITE_SEARCH_CANDIDATE_LIMIT = 25
_SITE_ID_NORMALIZER = re.compile(r"[^a-z0-9]+")


def normalize_site_id(value: Any) -> str | None:
    if value is None:
        return None
    normalized = _SITE_ID_NORMALIZER.sub("", str(value).strip().lower())
    return normalized or None


def normalized_site_expression(column):
    expression = func.lower(func.trim(func.coalesce(column, "")))
    for token in ("-", " ", "_", "/", "\\", "."):
        expression = func.replace(expression, token, "")
    return expression


def build_site_search_filter(columns: Sequence, normalized_query: str, partial: bool = False):
    expressions = [normalized_site_expression(column) for column in columns]
    if partial:
        return or_(*(expression.contains(normalized_query) for expression in expressions))
    return or_(*(expression == normalized_query for expression in expressions))


def _candidate_keys(row: Any, string_attrs: Iterable[str]) -> list[str]:
    keys: list[str] = []
    for attr in string_attrs:
        normalized = normalize_site_id(getattr(row, attr, None))
        if normalized:
            keys.append(normalized)
    return keys


def _candidate_score(keys: Sequence[str], normalized_query: str) -> float:
    best_score = -1.0
    for key in keys:
        if key == normalized_query:
            score = 10000 - len(key)
        elif key.startswith(normalized_query):
            score = 8000 - len(key)
        elif normalized_query in key:
            score = 6000 - len(key)
        else:
            score = SequenceMatcher(None, normalized_query, key).ratio() * 1000
        if score > best_score:
            best_score = score
    return best_score


def rank_site_matches(rows: Sequence[Any], normalized_query: str, string_attrs: Sequence[str], limit: int = 10) -> list[Any]:
    ranked = []
    seen_ids = set()
    for row in rows:
        row_identity = getattr(row, "id", id(row))
        if row_identity in seen_ids:
            continue
        seen_ids.add(row_identity)
        keys = _candidate_keys(row, string_attrs)
        if not keys:
            continue
        ranked.append((row, _candidate_score(keys, normalized_query), min((len(key) for key in keys), default=9999)))

    ranked.sort(key=lambda item: (-item[1], item[2]))
    return [row for row, _, _ in ranked[:limit]]


def find_site_matches(
    db: Session,
    model,
    raw_query: str,
    string_attrs: Sequence[str],
    numeric_attr: str | None = None,
    limit: int = 10,
):
    normalized_query = normalize_site_id(raw_query)
    if not normalized_query:
        return []

    query = db.query(model)
    raw_text = str(raw_query).strip()
    if numeric_attr and raw_text.isdigit():
        numeric_match = query.filter(getattr(model, numeric_attr) == int(raw_text)).first()
        if numeric_match:
            return [numeric_match]

    columns = [getattr(model, attr) for attr in string_attrs]
    exact_rows = query.filter(build_site_search_filter(columns, normalized_query, partial=False)).limit(limit).all()
    if exact_rows:
        return rank_site_matches(exact_rows, normalized_query, string_attrs, limit=limit)

    partial_rows = query.filter(build_site_search_filter(columns, normalized_query, partial=True)).limit(max(limit, SITE_SEARCH_CANDIDATE_LIMIT)).all()
    if partial_rows:
        return rank_site_matches(partial_rows, normalized_query, string_attrs, limit=limit)

    return []


def find_best_site_match(
    db: Session,
    model,
    raw_query: str,
    string_attrs: Sequence[str],
    numeric_attr: str | None = None,
):
    matches = find_site_matches(db, model, raw_query, string_attrs, numeric_attr=numeric_attr, limit=1)
    return matches[0] if matches else None


def ensure_normalized_site_indexes(engine, index_specs: Sequence[tuple[str, Any]]):
    for index_name, column in index_specs:
        try:
            Index(index_name, normalized_site_expression(column)).create(bind=engine, checkfirst=True)
        except Exception as exc:
            logger.warning("Skipping normalized site-search index %s: %s", index_name, exc)