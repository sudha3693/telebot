import pandas as pd
from sqlalchemy.orm import Session
from ..models.bb_deployment import BBDeployment
from ..utils.site_search import find_best_site_match

COLUMN_MAP = {
    "SITE ID": "site_id",
    "SITE ID.1": "site_id_2",
    "Cluster": "cluster",
    "District": "district",
    "BZ": "bz",
    "BB Status Final": "bb_status_final",
    "RFI Date": "rfi_date",
    "Month": "month",
}

class BBDeploymentService:
    @staticmethod
    def get_deployments(db: Session):
        return db.query(BBDeployment).all()

    @staticmethod
    def get_deployment_by_site_id(db: Session, site_id: str):
        return find_best_site_match(db, BBDeployment, site_id, ("site_id", "site_id_2"))

    @staticmethod
    def get_deployment_by_sr_id(db: Session, sr_id: int):
        return db.query(BBDeployment).filter(BBDeployment.id == sr_id).first()

    @staticmethod
    def import_deployments_from_excel(db: Session, excel_file):
        df = pd.read_excel(excel_file)
        df.columns = [str(column).strip() for column in df.columns]

        imported = []
        for row in df.to_dict(orient="records"):
            record = {}
            for header, attr in COLUMN_MAP.items():
                if header in row:
                    value = row[header]
                    if pd.isna(value):
                        value = None
                    record[attr] = str(value).strip() if value is not None else None
            deployment = BBDeployment(**record)
            db.add(deployment)
            imported.append(deployment)

        db.commit()
        for deployment in imported:
            db.refresh(deployment)
        return imported