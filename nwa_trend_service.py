import pandas as pd
import logging
import re
from datetime import date, datetime
from sqlalchemy.orm import Session
from ..models.nwa_trend import NWATrend
from ..utils.site_search import find_best_site_match

logger = logging.getLogger(__name__)

MONTH_PREFIXES = {
    "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"
}

COLUMN_MAP = {
    "SITE ID": "site_id",
    "Cluster": "cluster",
    "Site- Principal Owner": "site_principal_owner",
    "DG/Non-DG": "dg_non_dg",
    "ULS": "uls",
    "Current Site Status": "current_site_status",
    "Owner issue Sites": "owner_issue_sites",
    "District": "district",
    "Circle": "circle",
    "BZ": "bz",
    "CEM": "cem",
    "Av Tech": "avl_tech",
    "Avl Tech": "avl_tech",
    "CMO": "cmo",
    "CMO Repeat Day": "cmo",
    "5th Nov Incidence": "fifth_nov_incidence",
    "MTD incidence": "mtd_incidence",
    "MTD Incidence": "mtd_incidence",
    "Nov '22": "nov_22",
    "Dec '22": "dec_22",
    "Jan '23": "jan_23",
    "Feb '23": "feb_23",
    "Mar '23": "mar_23",
    "Apr '23": "apr_23",
    "May '23": "may_23",
    "Jun '23": "jun_23",
    "Jul '23": "jul_23",
    "Aug '23": "aug_23",
    "Sep '23": "sep_23",
    "Oct '23": "oct_23",
    "Nov '23": "nov_23",
    "Dec '23": "dec_23",
    "Jan '24": "jan_24",
    "Feb '24": "feb_24",
    "Mar '24": "mar_24",
    "Apr '24": "apr_24",
    "May '24": "may_24",
    "Jun '24": "jun_24",
    "June '24": "jun_24",
    "Jul '24": "jul_24",
    "July '24": "jul_24",
    "Aug '24": "aug_24",
    "Sep '24": "sep_24",
    "Oct '24": "oct_24",
    "Nov '24": "nov_24",
    "Dec '24": "dec_24",
    "Jan '25": "jan_25",
    "Feb '25": "feb_25",
    "Mar '25": "mar_25",
    "Apr '25": "apr_25",
    "May '25": "may_25",
    "Jun '25": "jun_25",
    "Jul '25": "jul_25",
    "Aug '25": "aug_25",
    "Sep '25": "sep_25",
    "Oct '25": "oct_25",
    "Nov '25": "nov_25",
    "Dec '25": "dec_25",
    "Jan-26": "jan_26",
    "Feb-26": "feb_26",
    "Mar-26": "mar_26",
    "Apr-26": "apr_26",
    "May-26": "may_26",
    "Jun-26": "jun_26",
    "Jul-26": "jul_26",
    "Aug-26": "aug_26",
    "Sep-26": "sep_26",
    "Oct-26": "oct_26",
    "Nov-26": "nov_26",
    "Dec-26": "dec_26",
}

class NWATrendService:
    @staticmethod
    def get_trends(db: Session):
        return db.query(NWATrend).all()

    @staticmethod
    def get_trend_by_site_id(db: Session, site_id: str):
        return find_best_site_match(db, NWATrend, site_id, ("site_id",))

    @staticmethod
    def import_trends_from_excel(db: Session, excel_file):
        def normalize_header(header):
            if isinstance(header, pd.Timestamp):
                header = header.strftime("%b-%y")
            elif isinstance(header, (datetime, date)):
                header = header.strftime("%b-%y")

            normalized = str(header or "").strip().lower()
            normalized = normalized.replace("\u00a0", " ")
            normalized = normalized.replace("\n", " ")
            normalized = normalized.replace("\r", " ")
            normalized = normalized.replace("/", " ")
            normalized = normalized.replace("-", " ")
            normalized = normalized.replace(".", " ")
            normalized = normalized.replace("'", " ")
            normalized = " ".join(normalized.split())

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

        def sanitize_cell(value):
            if pd.isna(value):
                return None
            text = str(value).strip()
            return text if text else None

        def first_non_empty(values):
            for value in values:
                sanitized = sanitize_cell(value)
                if sanitized is not None:
                    return sanitized
            return None

        def build_normalized_map():
            normalized_map = {normalize_header(header): attr for header, attr in COLUMN_MAP.items()}
            normalized_map.update(
                {
                    normalize_header(column.name): attribute.key
                    for attribute in NWATrend.__mapper__.column_attrs
                    for column in attribute.columns
                    if column.name != "id"
                }
            )
            return normalized_map

        def read_nwa_dataframe(source, normalized_map):
            if hasattr(source, "seek"):
                source.seek(0)

            workbook = pd.ExcelFile(source)
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

        normalized_map = build_normalized_map()
        df, original_headers, header_score, sheet_name, header_row = read_nwa_dataframe(excel_file, normalized_map)
        logger.info(
            "NWATrend import: selected sheet=%s header_row=%s score=%s rows=%s",
            sheet_name,
            header_row + 1,
            header_score,
            len(df.index),
        )

        if header_score <= 0:
            expected_headers = ", ".join(COLUMN_MAP.keys())
            received_headers = ", ".join(original_headers)
            raise ValueError(
                "No recognizable 4G NWA Trend headers found. "
                f"Sheet: {sheet_name}, header row: {header_row + 1}. "
                f"Received headers: [{received_headers}]. "
                f"Expected headers include: [{expected_headers}]"
            )

        df.columns = [normalize_header(column) for column in df.columns]

        imported = []

        header_positions = {}
        for index, header in enumerate(df.columns):
            header_positions.setdefault(header, []).append(index)

        mapped_attrs_from_headers = {
            normalized_map[header]
            for header in header_positions.keys()
            if header in normalized_map
        }
        if "site_id" not in mapped_attrs_from_headers:
            raise ValueError("Missing required mapped column for NWA Trend import: site_id")

        logger.info(
            "NWATrend import: rows=%s normalized_headers=%s mapped_fields=%s unmatched_headers=%s",
            len(df.index),
            list(df.columns),
            sorted(mapped_attrs_from_headers),
            sorted([header for header in header_positions.keys() if header not in normalized_map]),
        )

        skipped_rows = 0
        for row_index, row_values in enumerate(df.itertuples(index=False, name=None), start=1):
            record = {}
            for header, attr in normalized_map.items():
                positions = header_positions.get(header)
                if not positions:
                    continue
                value = first_non_empty(
                    row_values[position] for position in positions if position < len(row_values)
                )
                record[attr] = value

            non_empty_count = sum(value not in (None, "") for value in record.values())
            if not record.get("site_id") or non_empty_count < 2:
                logger.info("NWATrend import: skipping row=%s values=%s", row_index, record)
                skipped_rows += 1
                continue

            logger.info("NWATrend import: inserting row=%s values=%s", row_index, record)
            trend = NWATrend(**record)
            db.add(trend)
            imported.append(trend)

        if not imported:
            expected_headers = ", ".join(COLUMN_MAP.keys())
            received_headers = ", ".join(original_headers)
            raise ValueError(
                "No valid 4G NWA Trend rows were imported. "
                f"Received headers: [{received_headers}]. "
                f"Expected headers include: [{expected_headers}]"
            )

        logger.info(
            "NWATrend import completed: inserted_rows=%s skipped_rows=%s",
            len(imported),
            skipped_rows,
        )

        db.commit()
        for trend in imported:
            db.refresh(trend)
        return imported