import json
import logging
import re
from datetime import date, datetime
from io import BytesIO
from typing import Dict, List, Tuple

import pandas as pd

from .day_wise_service import COLUMN_MAP as DAYWISE_COLUMN_MAP
from .nwa_trend_service import COLUMN_MAP as NWA_COLUMN_MAP

logger = logging.getLogger(__name__)

MONTH_PREFIXES = {
    "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"
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

    compact = normalized.replace(" ", "")
    match_day_first = re.fullmatch(r"(\d{1,2})([a-z]{3})(\d{2,4})?", compact)
    if match_day_first and match_day_first.group(2) in MONTH_PREFIXES:
        return f"{int(match_day_first.group(1))} {match_day_first.group(2)}"

    match_month_first = re.fullmatch(r"([a-z]{3})(\d{1,2})(\d{2,4})?", compact)
    if match_month_first and match_month_first.group(1) in MONTH_PREFIXES:
        return f"{int(match_month_first.group(2))} {match_month_first.group(1)}"

    return normalized


def _canonical_month_year(normalized: str) -> str:
    tokens = normalized.split()
    if len(tokens) >= 2:
        first = tokens[0][:3]
        second = tokens[1]
        if first in MONTH_PREFIXES and second.isdigit():
            return f"{first} {int(second) % 100:02d}"

        first = tokens[0]
        second = tokens[1][:3]
        if first.isdigit() and second in MONTH_PREFIXES:
            return f"{second} {int(first) % 100:02d}"

    compact = normalized.replace(" ", "")
    match_month_first = re.fullmatch(r"([a-z]{3})(\d{2,4})", compact)
    if match_month_first and match_month_first.group(1) in MONTH_PREFIXES:
        return f"{match_month_first.group(1)} {int(match_month_first.group(2)) % 100:02d}"

    match_year_first = re.fullmatch(r"(\d{2,4})([a-z]{3})", compact)
    if match_year_first and match_year_first.group(2) in MONTH_PREFIXES:
        return f"{match_year_first.group(2)} {int(match_year_first.group(1)) % 100:02d}"

    return normalized


class UploadIntelligenceService:
    DATASET_MAPS = {
        "daywise": DAYWISE_COLUMN_MAP,
        "nwa": NWA_COLUMN_MAP,
    }

    DATASET_HEADER_MODES = {
        "daywise": "day_month",
        "nwa": "month_year",
    }

    @staticmethod
    def normalize_header(header, dataset: str = "") -> str:
        dataset_key = (dataset or "").strip().lower()
        mode = UploadIntelligenceService.DATASET_HEADER_MODES.get(dataset_key, "generic")

        if isinstance(header, pd.Timestamp):
            if mode == "month_year":
                header = header.strftime("%b-%y")
            else:
                header = f"{header.day}-{header.strftime('%b')}"
        elif isinstance(header, (datetime, date)):
            if mode == "month_year":
                header = header.strftime("%b-%y")
            else:
                header = f"{header.day}-{header.strftime('%b')}"

        normalized = str(header or "").strip().lower()
        normalized = normalized.replace("\u00a0", " ").replace("\n", " ").replace("\r", " ")
        normalized = normalized.replace("/", " ").replace("-", " ").replace(".", " ").replace("'", " ")
        normalized = " ".join(normalized.split())

        if mode == "day_month":
            return _canonical_day_month(normalized)
        if mode == "month_year":
            return _canonical_month_year(normalized)
        return normalized

    @classmethod
    def get_expected_map(cls, dataset: str) -> Dict[str, str]:
        key = (dataset or "").strip().lower()
        mapping = cls.DATASET_MAPS.get(key)
        if not mapping:
            raise ValueError(f"Unsupported dataset '{dataset}'. Supported datasets: {', '.join(sorted(cls.DATASET_MAPS.keys()))}")
        return mapping

    @staticmethod
    def _best_sheet_header(df_raw: pd.DataFrame, normalized_expected: Dict[str, str], dataset: str) -> Tuple[int, int]:
        best_row = 0
        best_score = -1
        max_rows = min(20, len(df_raw.index))
        for idx in range(max_rows):
            candidates = [UploadIntelligenceService.normalize_header(v, dataset=dataset) for v in df_raw.iloc[idx].tolist()]
            score = sum(1 for header in candidates if header in normalized_expected)
            if score > best_score:
                best_score = score
                best_row = idx
        return best_row, best_score

    @classmethod
    def parse_workbook(cls, file_bytes: bytes, dataset: str, preview_rows: int = 10):
        expected_map = cls.get_expected_map(dataset)
        normalized_expected = {cls.normalize_header(k, dataset=dataset): v for k, v in expected_map.items()}

        workbook = pd.ExcelFile(BytesIO(file_bytes))
        best_sheet = workbook.sheet_names[0]
        best_header_row = 0
        best_score = -1

        for sheet in workbook.sheet_names:
            raw = pd.read_excel(workbook, sheet_name=sheet, header=None, dtype=object)
            row_idx, score = cls._best_sheet_header(raw, normalized_expected, dataset)
            if score > best_score:
                best_score = score
                best_sheet = sheet
                best_header_row = row_idx

        df = pd.read_excel(workbook, sheet_name=best_sheet, header=best_header_row)
        original_headers = [str(h).strip() for h in df.columns]
        normalized_headers = [cls.normalize_header(h, dataset=dataset) for h in df.columns]

        header_positions: Dict[str, List[int]] = {}
        for i, h in enumerate(normalized_headers):
            header_positions.setdefault(h, []).append(i)

        mapped_headers = [h for h in header_positions if h in normalized_expected]
        unmatched_headers = [h for h in header_positions if h not in normalized_expected]

        preview_df = df.head(preview_rows).copy()
        preview_df = preview_df.where(pd.notnull(preview_df), None)
        preview_records = json.loads(preview_df.to_json(orient="records", date_format="iso"))

        logger.info(
            "Upload preview dataset=%s sheet=%s header_row=%s mapped=%s unmatched=%s",
            dataset,
            best_sheet,
            best_header_row + 1,
            len(mapped_headers),
            len(unmatched_headers),
        )

        return {
            "dataset": dataset,
            "sheet": best_sheet,
            "header_row": best_header_row + 1,
            "score": best_score,
            "total_rows": len(df.index),
            "original_headers": original_headers,
            "normalized_headers": normalized_headers,
            "mapped_headers": mapped_headers,
            "unmatched_headers": unmatched_headers,
            "mapped_fields": sorted({normalized_expected[h] for h in mapped_headers}),
            "preview": preview_records,
        }

    @classmethod
    def validate_required_headers(cls, parsed_payload: dict, required_fields: List[str]):
        present = set(parsed_payload.get("mapped_fields", []))
        missing = [field for field in required_fields if field not in present]
        if missing:
            raise ValueError(f"Missing required mapped fields: {', '.join(missing)}")

    @staticmethod
    def sanitize_cell(value):
        if pd.isna(value):
            return None
        text = str(value).strip()
        return text if text else None
