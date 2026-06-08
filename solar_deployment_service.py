import pandas as pd
from sqlalchemy.orm import Session
from ..models.solar_deployment import SolarDeployment
from ..utils.site_search import find_best_site_match

COLUMN_MAP = {
    "Airtel ID": "airtel_id",
    "Airtel ID.1": "airtel_id_2",
    "BZ": "bz",
    "Site Name": "site_name",
    "FSE AREA": "fse_area",
    "Dist": "dist",
    "State": "state",
    "Solar Status": "solar_status",
    "RFAI Date": "rfai_date",
    "Month": "month",
}

class SolarDeploymentService:
    @staticmethod
    def get_deployments(db: Session):
        return db.query(SolarDeployment).all()

    @staticmethod
    def get_deployment_by_airtel_id(db: Session, airtel_id: str):
        return find_best_site_match(db, SolarDeployment, airtel_id, ("airtel_id", "airtel_id_2"))

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
            deployment = SolarDeployment(**record)
            db.add(deployment)
            imported.append(deployment)

        db.commit()
        for deployment in imported:
            db.refresh(deployment)
        return imported
