import pandas as pd
from datetime import date, datetime
import re
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from ..models.day_wise import DayWise4G
from ..utils.site_search import find_best_site_match

logger = logging.getLogger(__name__)

COLUMN_MAP = {
    "SITE ID": "site_id",
    "Cluster": "cluster",
    "Current Site Status": "current_site_status",
    "Owner issue Sites": "owner_issue_sites",
    "5G Available": "five_g_available",
    "District": "district",
    "Town": "town",
    "Top 8 Towns": "top_8_towns",
    "Circle": "circle",
    "BZ": "bz",
    "2-Feb": "d2_feb",
    "3-Feb": "d3_feb",
    "4-Feb": "d4_feb",
    "5-Feb": "d5_feb",
    "6-Feb": "d6_feb",
    "7-Feb": "d7_feb",
    "8-Feb": "d8_feb",
    "9-Feb": "d9_feb",
    "10-Feb": "d10_feb",
    "11-Feb": "d11_feb",
    "12-Feb": "d12_feb",
    "13-Feb": "d13_feb",
    "14-Feb": "d14_feb",
    "15-Feb": "d15_feb",
    "16-Feb": "d16_feb",
    "17-Feb": "d17_feb",
    "18-Feb": "d18_feb",
    "19-Feb": "d19_feb",
    "20-Feb": "d20_feb",
    "21-Feb": "d21_feb",
    "22-Feb": "d22_feb",
    "23-Feb": "d23_feb",
    "24-Feb": "d24_feb",
    "25-Feb": "d25_feb",
    "26-Feb": "d26_feb",
    "27-Feb": "d27_feb",
    "28-Feb": "d28_feb",
    "1-Mar": "d1_mar",
    "2-Mar": "d2_mar",
    "3-Mar": "d3_mar",
    "4-Mar": "d4_mar",
    "5-Mar": "d5_mar",
    "6-Mar": "d6_mar",
    "7-Mar": "d7_mar",
    "8-Mar": "d8_mar",
    "9-Mar": "d9_mar",
    "10-Mar": "d10_mar",
    "11-Mar": "d11_mar",
    "12-Mar": "d12_mar",
    "13-Mar": "d13_mar",
    "14-Mar": "d14_mar",
    "15-Mar": "d15_mar",
    "16-Mar": "d16_mar",
    "17-Mar": "d17_mar",
    "18-Mar": "d18_mar",
    "19-Mar": "d19_mar",
    "20-Mar": "d20_mar",
    "21-Mar": "d21_mar",
    "22-Mar": "d22_mar",
    "23-Mar": "d23_mar",
    "24-Mar": "d24_mar",
    "25-Mar": "d25_mar",
    "26-Mar": "d26_mar",
    "27-Mar": "d27_mar",
    "28-Mar": "d28_mar",
    "29-Mar": "d29_mar",
    "30-Mar": "d30_mar",
    "31-Mar": "d31_mar",
}

MONTH_PREFIXES = {
    "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"
}

MONTH_ORDER = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

STATIC_DAYWISE_FIELDS = {
    "id",
    "site_id",
    "cluster",
    "current_site_status",
    "owner_issue_sites",
    "five_g_available",
    "district",
    "town",
    "top_8_towns",
    "circle",
    "bz",
}

def _canonical_day_month(normalized: str) -> str:
    tokens = normalized.split()
    if len(tokens) >= 2:
        first = tokens[0]
        second = tokens[1][:3]
        if first.isdigit() and second in MONTH_PREFIXES:
            return f"{int(first)} {second}"
        first_month = tokens[0][:3]
        if first_month in MONTH_PREFIXES and len(tokens) >= 2 and tokens[1].isdigit():
            return f"{int(tokens[1])} {first_month}"

    # Handles compact formats like 02feb24 or feb022024.
    compact = normalized.replace(" ", "")
    match_day_first = re.fullmatch(r"(\d{1,2})([a-z]{3})(\d{2,4})?", compact)
    if match_day_first and match_day_first.group(2) in MONTH_PREFIXES:
        return f"{int(match_day_first.group(1))} {match_day_first.group(2)}"

    match_month_first = re.fullmatch(r"([a-z]{3})(\d{1,2})(\d{2,4})?", compact)
    if match_month_first and match_month_first.group(1) in MONTH_PREFIXES:
        return f"{int(match_month_first.group(2))} {match_month_first.group(1)}"

    return normalized

def normalize_header(header: str) -> str:
    if isinstance(header, pd.Timestamp):
        header = f"{header.day}-{header.strftime('%b')}"
    elif isinstance(header, (datetime, date)):
        header = f"{header.day}-{header.strftime('%b')}"

    normalized = str(header or "").strip().lower()
    normalized = normalized.replace("\u00a0", " ")
    normalized = normalized.replace("\n", " ")
    normalized = normalized.replace("\r", " ")
    normalized = normalized.replace("/", " ")
    normalized = normalized.replace("-", " ")
    normalized = normalized.replace(".", " ")
    normalized = normalized.replace("'", " ")
    normalized = " ".join(normalized.split())
    return _canonical_day_month(normalized)

def _build_normalized_map():
    normalized_map = {normalize_header(header): attr for header, attr in COLUMN_MAP.items()}
    normalized_map.update({normalize_header(attr.columns[0].name): attr.key for attr in DayWise4G.__mapper__.column_attrs})
    return normalized_map

def _first_non_empty(values):
    for value in values:
        if pd.isna(value):
            continue
        text = str(value).strip()
        if text != "":
            return text
    return None

def _build_record(row_values, header_positions, normalized_map):
    record = {}
    for header, positions in header_positions.items():
        attr = normalized_map.get(header)
        if not attr:
            continue

        chosen_value = _first_non_empty(
            row_values[position] for position in positions if position < len(row_values)
        )

        if chosen_value is None:
            continue

        existing_value = record.get(attr)
        if existing_value in (None, ""):
            record[attr] = chosen_value

    return record

def _read_daywise_dataframe(excel_file, normalized_map):
    if hasattr(excel_file, "seek"):
        excel_file.seek(0)

    workbook = pd.ExcelFile(excel_file)
    best_sheet = workbook.sheet_names[0]
    best_header_row = 0
    best_score = -1

    for sheet_name in workbook.sheet_names:
        raw_df = pd.read_excel(workbook, sheet_name=sheet_name, header=None, dtype=object)
        max_scan_rows = min(20, len(raw_df.index))

        for row_idx in range(max_scan_rows):
            candidate_headers = [normalize_header(value) for value in raw_df.iloc[row_idx].tolist()]
            score = sum(1 for header in candidate_headers if header in normalized_map)
            if score > best_score:
                best_score = score
                best_sheet = sheet_name
                best_header_row = row_idx

    df = pd.read_excel(workbook, sheet_name=best_sheet, header=best_header_row)
    original_headers = [str(column).strip() for column in df.columns]
    return df, original_headers, best_score, best_sheet, best_header_row

def _collect_mapped_attrs_from_headers(headers, normalized_map):
    mapped_attrs = set()
    for header in headers:
        attr = normalized_map.get(header)
        if attr:
            mapped_attrs.add(attr)
    return mapped_attrs

def _get_daywise_date_columns() -> List[Dict[str, str]]:
    columns = []
    for attribute in DayWise4G.__mapper__.column_attrs:
        if attribute.key in STATIC_DAYWISE_FIELDS:
            continue

        column = attribute.columns[0]
        match = re.fullmatch(r"(\d{1,2})-([A-Za-z]{3})", column.name)
        if not match:
            continue

        day_number = int(match.group(1))
        month_key = match.group(2).lower()
        month_order = MONTH_ORDER.get(month_key)
        if month_order is None:
            continue

        columns.append(
            {
                "label": column.name,
                "attribute": attribute.key,
                "month_order": month_order,
                "day_number": day_number,
            }
        )

    columns.sort(key=lambda item: (item["month_order"], item["day_number"]))
    return columns

def _sanitize_value(value: Optional[str]):
    if value is None:
        return None
    text = str(value).strip()
    return text or None

def _build_daywise_trend_points(row: DayWise4G, include_empty: bool = False) -> List[Dict[str, Optional[str]]]:
    trend_points = []
    for column in _get_daywise_date_columns():
        value = _sanitize_value(getattr(row, column["attribute"], None))
        if value is None and not include_empty:
            continue

        trend_points.append(
            {
                "label": column["label"],
                "attribute": column["attribute"],
                "value": value,
            }
        )

    return trend_points

def _build_daywise_payload(row: Optional[DayWise4G], include_empty: bool = False):
    if not row:
        return None

    trend_points = _build_daywise_trend_points(row, include_empty=include_empty)
    return {
        "id": row.id,
        "site_id": _sanitize_value(row.site_id),
        "cluster": _sanitize_value(row.cluster),
        "current_site_status": _sanitize_value(row.current_site_status),
        "owner_issue_sites": _sanitize_value(row.owner_issue_sites),
        "five_g": _sanitize_value(getattr(row, "five_g", None) or getattr(row, "five_g_available", None)),
        "district": _sanitize_value(row.district),
        "team": _sanitize_value(getattr(row, "team", None) or getattr(row, "town", None)),
        "topo": _sanitize_value(getattr(row, "topo", None) or getattr(row, "top_8_towns", None)),
        "circle": _sanitize_value(row.circle),
        "dz": _sanitize_value(getattr(row, "dz", None) or getattr(row, "bz", None)),
        "trend_points": trend_points,
        "trend_column_labels": [point["label"] for point in trend_points],
    }

class DayWiseService:
    @staticmethod
    def get_daywise_rows(db: Session):
        return db.query(DayWise4G).all()

    @staticmethod
    def get_daywise_by_site_id(db: Session, site_id: str):
        return find_best_site_match(db, DayWise4G, site_id, ("site_id",))

    @staticmethod
    def get_daywise_trend_columns():
        return _get_daywise_date_columns()

    @staticmethod
    def get_daywise_payload_by_site_id(db: Session, site_id: str, include_empty: bool = False):
        row = DayWiseService.get_daywise_by_site_id(db, site_id)
        return _build_daywise_payload(row, include_empty=include_empty)

    @staticmethod
    def serialize_daywise_row(row: Optional[DayWise4G], include_empty: bool = False):
        return _build_daywise_payload(row, include_empty=include_empty)

    @staticmethod
    def import_daywise_from_excel(db: Session, excel_file):
        normalized_map = _build_normalized_map()
        df, original_headers, header_score, sheet_name, header_row = _read_daywise_dataframe(excel_file, normalized_map)
        logger.info(
            "DayWise import: selected sheet=%s header_row=%s score=%s rows=%s",
            sheet_name,
            header_row + 1,
            header_score,
            len(df.index),
        )

        if header_score <= 0:
            expected_headers = ", ".join(COLUMN_MAP.keys())
            received_headers = ", ".join(original_headers)
            raise ValueError(
                "No recognizable 4G Day Wise headers found. "
                f"Sheet: {sheet_name}, header row: {header_row + 1}. "
                f"Received headers: [{received_headers}]. "
                f"Expected headers include: [{expected_headers}]"
            )

        df.columns = [normalize_header(column) for column in df.columns]
        duplicate_headers = [header for header in set(df.columns) if list(df.columns).count(header) > 1]
        if duplicate_headers:
            logger.warning("DayWise import: duplicate normalized headers found: %s", duplicate_headers)

        # Keep duplicate headers by storing all column positions per normalized header.
        header_positions = {}
        for index, header in enumerate(df.columns):
            header_positions.setdefault(header, []).append(index)

        mapped_attrs_from_headers = _collect_mapped_attrs_from_headers(header_positions.keys(), normalized_map)
        required_attrs = {"site_id", "cluster", "current_site_status"}
        missing_required = sorted(required_attrs - mapped_attrs_from_headers)
        if missing_required:
            raise ValueError(
                "Missing required mapped columns for 4G Day Wise import: "
                + ", ".join(missing_required)
            )

        logger.info(
            "DayWise import: mapped_fields=%s unmatched_headers=%s",
            sorted(mapped_attrs_from_headers),
            sorted([header for header in header_positions.keys() if header not in normalized_map]),
        )

        imported = []
        skipped_rows = 0
        for row_values in df.itertuples(index=False, name=None):
            record = _build_record(row_values, header_positions, normalized_map)

            # Avoid inserting weak/null rows caused by header mismatch.
            non_empty_count = sum(value not in (None, "") for value in record.values())
            if not record.get("site_id") or non_empty_count < 3:
                skipped_rows += 1
                continue

            daywise = DayWise4G(**record)
            db.add(daywise)
            imported.append(daywise)

        if not imported:
            expected_headers = ", ".join(COLUMN_MAP.keys())
            received_headers = ", ".join(original_headers)
            raise ValueError(
                "No valid 4G Day Wise rows were imported. "
                f"Received headers: [{received_headers}]. "
                f"Expected headers include: [{expected_headers}]"
            )

        logger.info(
            "DayWise import completed: inserted_rows=%s skipped_rows=%s",
            len(imported),
            skipped_rows,
        )

        db.commit()
        for daywise in imported:
            db.refresh(daywise)
        return imported
