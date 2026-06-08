import pandas as pd
from sqlalchemy.orm import Session
from ..models.dg_deployment import DGDeployment
from ..utils.site_search import find_best_site_match

COLUMN_MAP = {
    "Sr ID": "sr_id",
    "Site ID": "site_id",
    "Site ID-A": "site_id_a",
    "Site Type": "site_type",
    "Site Type.1": "site_type_2",
    "Airtel Site Name": "airtel_site_name",
    "EIL Cluster": "eil_cluster",
    "Airtel Zone": "airtel_zone",
    "State": "state",
    "Main TOCO": "main_toco",
    "TOCO ID": "toco_id",
    "DG/Non DG": "dg_non_dg",
    "RFI Date": "rfi_date",
    "RFI Month": "rfi_month",
    "Remarks": "remarks",
    "New Priority": "new_priority",
    "Final Remarks": "final_remarks",
    "Toco Remarks": "toco_remarks",
}

def normalize_duplicate_columns(columns):
    seen = {}
    normalized = []
    for col in columns:
        col = str(col).strip()
        if col in seen:
            seen[col] += 1
            normalized.append(f"{col}.{seen[col]}")
        else:
            seen[col] = 0
            normalized.append(col)
    return normalized

class DGDeploymentService:
    @staticmethod
    def get_deployments(db: Session):
        return db.query(DGDeployment).all()

    @staticmethod
    def get_deployment_by_site_id(db: Session, site_id: str):
        return find_best_site_match(db, DGDeployment, site_id, ("site_id", "site_id_a"))

    @staticmethod
    def get_deployment_by_sr_id(db: Session, sr_id: int):
        return db.query(DGDeployment).filter(DGDeployment.sr_id == sr_id).first()

    @staticmethod
    def import_deployments_from_excel(db: Session, excel_file):
        df = pd.read_excel(excel_file)
        df.columns = normalize_duplicate_columns(df.columns)

        imported = []
        for row in df.to_dict(orient="records"):
            record = {}
            for header, attr in COLUMN_MAP.items():
                if header in row:
                    value = row[header]
                    if pd.isna(value):
                        value = None
                    record[attr] = str(value).strip() if value is not None else None
            deployment = DGDeployment(**record)
            db.add(deployment)
            imported.append(deployment)

        db.commit()
        for deployment in imported:
            db.refresh(deployment)
        return imported
