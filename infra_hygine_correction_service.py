import pandas as pd
from sqlalchemy.orm import Session
from ..models.bb_deployment import BBDeployment
from ..models.dg_deployment import DGDeployment
from ..models.infra_hygine_correction import InfraHygineCorrection
from ..models.solar_deployment import SolarDeployment
from ..utils.site_search import find_best_site_match, normalize_site_id

COLUMN_MAP = {
    "SITEID": "site_id",
    "Site Name": "site_name",
    "Site- Principal Owner": "principal_owner",
    "DG/Non-DG": "dg_non_dg",
    "BZ": "bz",
    "Cluster": "cluster",
    "District": "district",
    "Circle": "circle",
    "Bucket/Category": "bucket_category",
    "Closure Date/Month": "closure_date_month",
    "Month": "month",
    "Bucket": "bucket",
    "Status": "status",
}

class InfraHygineCorrectionService:
    @staticmethod
    def _normalize_site_id(site_id: str):
        return normalize_site_id(site_id)

    @staticmethod
    def _build_payload(row=None, site_id: str = None, dg_deployment: str = None, bb_deployment: str = None, solar_deployment: str = None):
        return {
            "id": getattr(row, "id", 0),
            "site_id": getattr(row, "site_id", None) or site_id,
            "site_name": getattr(row, "site_name", None),
            "principal_owner": getattr(row, "principal_owner", None),
            "dg_non_dg": getattr(row, "dg_non_dg", None),
            "bz": getattr(row, "bz", None),
            "cluster": getattr(row, "cluster", None),
            "district": getattr(row, "district", None),
            "circle": getattr(row, "circle", None),
            "bucket_category": getattr(row, "bucket_category", None),
            "closure_date_month": getattr(row, "closure_date_month", None),
            "month": getattr(row, "month", None),
            "bucket": getattr(row, "bucket", None),
            "status": getattr(row, "status", None),
            "dg_deployment": dg_deployment,
            "bb_deployment": bb_deployment,
            "solar_deployment": solar_deployment,
        }

    @staticmethod
    def _lookup_dg_deployment(db: Session, normalized_site_id: str):
        if not normalized_site_id:
            return None
        row = find_best_site_match(db, DGDeployment, normalized_site_id, ("site_id", "site_id_a"))
        return row.final_remarks if row else None

    @staticmethod
    def _lookup_bb_deployment(db: Session, normalized_site_id: str):
        if not normalized_site_id:
            return None
        row = find_best_site_match(db, BBDeployment, normalized_site_id, ("site_id", "site_id_2"))
        return row.bb_status_final if row else None

    @staticmethod
    def _lookup_solar_deployment(db: Session, normalized_site_id: str):
        if not normalized_site_id:
            return None
        row = find_best_site_match(db, SolarDeployment, normalized_site_id, ("airtel_id", "airtel_id_2"))
        return row.solar_status if row else None

    @staticmethod
    def _build_deployment_maps(db: Session):
        dg_map = {}
        bb_map = {}
        solar_map = {}

        for row in db.query(DGDeployment.site_id, DGDeployment.site_id_a, DGDeployment.final_remarks).all():
            for key in (row.site_id, row.site_id_a):
                normalized = InfraHygineCorrectionService._normalize_site_id(key)
                if normalized and normalized not in dg_map:
                    dg_map[normalized] = row.final_remarks

        for row in db.query(BBDeployment.site_id, BBDeployment.site_id_2, BBDeployment.bb_status_final).all():
            for key in (row.site_id, row.site_id_2):
                normalized = InfraHygineCorrectionService._normalize_site_id(key)
                if normalized and normalized not in bb_map:
                    bb_map[normalized] = row.bb_status_final

        for row in db.query(SolarDeployment.airtel_id, SolarDeployment.airtel_id_2, SolarDeployment.solar_status).all():
            for key in (row.airtel_id, row.airtel_id_2):
                normalized = InfraHygineCorrectionService._normalize_site_id(key)
                if normalized and normalized not in solar_map:
                    solar_map[normalized] = row.solar_status

        return dg_map, bb_map, solar_map

    @staticmethod
    def get_records(db: Session):
        return db.query(InfraHygineCorrection).all()

    @staticmethod
    def get_records_payload(db: Session):
        rows = db.query(InfraHygineCorrection).all()
        dg_map, bb_map, solar_map = InfraHygineCorrectionService._build_deployment_maps(db)
        payloads = []
        for row in rows:
            normalized_site_id = InfraHygineCorrectionService._normalize_site_id(row.site_id)
            payloads.append(
                InfraHygineCorrectionService._build_payload(
                    row=row,
                    dg_deployment=dg_map.get(normalized_site_id),
                    bb_deployment=bb_map.get(normalized_site_id),
                    solar_deployment=solar_map.get(normalized_site_id),
                )
            )
        return payloads

    @staticmethod
    def get_record_by_site_id(db: Session, site_id: str):
        return find_best_site_match(db, InfraHygineCorrection, site_id, ("site_id",))

    @staticmethod
    def get_record_payload_by_site_id(db: Session, site_id: str):
        normalized_site_id = InfraHygineCorrectionService._normalize_site_id(site_id)
        if not normalized_site_id:
            return None

        row = find_best_site_match(db, InfraHygineCorrection, normalized_site_id, ("site_id",))
        dg_row = InfraHygineCorrectionService._lookup_dg_deployment(db, normalized_site_id)
        bb_row = InfraHygineCorrectionService._lookup_bb_deployment(db, normalized_site_id)
        solar_row = InfraHygineCorrectionService._lookup_solar_deployment(db, normalized_site_id)

        dg_deployment = dg_row if dg_row else None
        bb_deployment = bb_row if bb_row else None
        solar_deployment = solar_row if solar_row else None

        if not row and not any([dg_deployment, bb_deployment, solar_deployment]):
            return None

        return InfraHygineCorrectionService._build_payload(
            row=row,
            site_id=site_id,
            dg_deployment=dg_deployment,
            bb_deployment=bb_deployment,
            solar_deployment=solar_deployment,
        )

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
            deployment = InfraHygineCorrection(**record)
            db.add(deployment)
            imported.append(deployment)

        db.commit()
        for deployment in imported:
            db.refresh(deployment)
        return imported
