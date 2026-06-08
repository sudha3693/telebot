import pandas as pd
from sqlalchemy.orm import Session
from ..models.site_list import SiteList1
from ..utils.site_search import find_best_site_match, find_site_matches

COLUMN_MAP = {
    "Sr ID": "sr_id",
    "Site ID": "site_id",
    "Tech ID": "tech_id",
    "Airtel Site Name": "airtel_site_name",
    "Airtel Zone": "airtel_zone",
    "Dist": "dist",
    "Airtel Zone1": "airtel_zone1",
    "Airtel Zone.1": "airtel_zone_2",
    "State": "state",
    "Main TOCO": "main_toco",
    "4G - Pay Load": "pay_load_4g",
    "TOCO ID": "toco_id",
    "TOCO Site Name": "toco_site_name",
    "TOCO Zone": "toco_zone",
    "Site Type": "site_type",
    "No of Link": "no_of_link",
    "Tech": "tech",
    "OSS-2G": "oss_2g",
    "BSC": "bsc",
    "BCF No": "bcf_no",
    "Actual BCF Name": "actual_bcf_name",
    "In OSS": "in_oss",
    "OSS-FD": "oss_fd",
    "LNBTS": "lnbts",
    "Correct LN Name": "correct_ln_name",
    "IP": "ip",
    "In-OSS": "in_oss_alt",
    "OSS-L900": "oss_l900",
    "LNBTS1": "lnbts1",
    "Current LN Name": "current_ln_name",
    "IP1": "ip1",
    "In OSS": "in_oss",
    "BSS1 Name": "bss1_name",
    "BSS1 No": "bss1_no",
    "BSS2 Name": "bss2_name",
    "BSS2 No": "bss2_no",
    "ZTM Name": "ztm_name",
    "ZTM No": "ztm_no",
    "Tower Type": "tower_type",
    "BIL Cluster": "bil_cluster",
    "BIL Zone": "bil_zone",
    "BIL Hub": "bil_hub",
    "Technician Name": "technician_name",
    "Technician No": "technician_no",
    "CI Name": "ci_name",
    "CI No": "ci_no",
    "ZOM Name": "zom_name",
    "ZOM No": "zom_no",
    "DG/Non DG": "dg_non_dg",
    "Non DG Type": "non_dg_type",
    "EB/Non-EB": "eb_non_eb",
    "EB Status": "eb_status",
    "Solar/Non-Solar": "solar_non_solar",
    "Vendor": "vendor",
    "RFS Date": "rfs_date",
    "Shared": "shared",
    "No of Cell 2G": "no_of_cell_2g",
    "DHQ/NDHQ": "dhq_ndhq",
    "Site ID.1": "site_id_2",
    "Address": "address",
    "Tower Area": "tower_area",
    "ID/OD": "id_od",
    "RFS Month": "rfs_month",
    "Locator ID": "locator_id",
    "Lat": "lat",
    "Long": "long",
    "Dependency": "dependency",
    "MS-Avg Churn": "ms_avg_churn",
    "Opex Cost": "opex_cost",
    "UBR/FTTH": "ubr_ftth",
    "District": "district",
    "LT/HT": "lt_ht",
    "Pay Load - 5G": "pay_load_5g",
    "5G Available status": "available_5g",
    "Enode B": "enode_b",
    "Enode-B": "enode_b",
    "Site ID 3": "site_id_3",
}


def normalize_header(header: str) -> str:
    normalized = str(header).strip().lower()
    normalized = normalized.replace("\n", " ")
    normalized = normalized.replace("\r", " ")
    normalized = normalized.replace("/", " ")
    normalized = normalized.replace("-", " ")
    normalized = normalized.replace(".", " ")
    normalized = normalized.replace("'", " ")
    normalized = " ".join(normalized.split())
    return normalized

class SiteService:
    @staticmethod
    def get_sites(db: Session):
        return db.query(SiteList1).all()

    @staticmethod
    def get_site_by_sr_id(db: Session, sr_id: int):
        return db.query(SiteList1).filter(SiteList1.sr_id == sr_id).first()

    @staticmethod
    def get_site_by_site_id(db: Session, site_id: str):
        return find_best_site_match(
            db,
            SiteList1,
            site_id,
            ("site_id", "site_id_2", "site_id_3"),
            numeric_attr="sr_id",
        )

    @staticmethod
    def search_sites_by_site_id(db: Session, site_id: str, limit: int = 10):
        return find_site_matches(
            db,
            SiteList1,
            site_id,
            ("site_id", "site_id_2", "site_id_3"),
            numeric_attr="sr_id",
            limit=limit,
        )

    @staticmethod
    def import_sites_from_excel(db: Session, excel_file):
        df = pd.read_excel(excel_file)
        df.columns = [str(column).strip() for column in df.columns]

        normalized_map = {normalize_header(header): attr for header, attr in COLUMN_MAP.items()}
        normalized_map.update({normalize_header(attr.columns[0].name): attr.key for attr in SiteList1.__mapper__.column_attrs})
        imported = []
        for row in df.to_dict(orient="records"):
            normalized_row = {normalize_header(key): value for key, value in row.items()}
            record = {}
            for header, attr in normalized_map.items():
                if header in normalized_row:
                    value = normalized_row[header]
                    if pd.isna(value):
                        value = None
                    record[attr] = str(value).strip() if value is not None else None
            site = SiteList1(**record)
            db.add(site)
            imported.append(site)

        db.commit()
        for site in imported:
            db.refresh(site)
        return imported
