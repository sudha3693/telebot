import pandas as pd
from sqlalchemy.orm import Session
from ..models.infra_climate_proofing import InfraClimateProofing
from ..utils.site_search import find_best_site_match

COLUMN_MAP = {
    "Circle": "circle",
    "Siteid": "site_id",
    "Uni": "uni",
    "Toco": "toco",
    "Toco-ID": "toco_id",
    "Cluster": "cluster",
    "District": "district",
    "BZ": "bz",
    "Activity": "activity",
    "Final Status": "final_status",
    "Remarks": "remarks",
}

class InfraClimateProofingService:
    @staticmethod
    def get_records(db: Session):
        return db.query(InfraClimateProofing).all()

    @staticmethod
    def get_record_by_site_id(db: Session, site_id: str):
        return find_best_site_match(db, InfraClimateProofing, site_id, ("site_id",))

    @staticmethod
    def import_records_from_excel(db: Session, excel_file):
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
            deployment = InfraClimateProofing(**record)
            db.add(deployment)
            imported.append(deployment)

        db.commit()
        for deployment in imported:
            db.refresh(deployment)
        return imported