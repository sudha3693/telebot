from sqlalchemy import Column, Integer, String
from ..database import Base

class InfraHygineCorrection(Base):
    __tablename__ = "Infra Hygine Correction"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column("SITEID", String, index=True, nullable=True)
    site_name = Column("Site Name", String, nullable=True)
    principal_owner = Column("Site- Principal Owner", String, nullable=True)
    dg_non_dg = Column("DG/Non-DG", String, nullable=True)
    bz = Column("BZ", String, nullable=True)
    cluster = Column("Cluster", String, nullable=True)
    district = Column("District", String, nullable=True)
    circle = Column("Circle", String, nullable=True)
    bucket_category = Column("Bucket/Category", String, nullable=True)
    closure_date_month = Column("Closure Date/Month", String, nullable=True)
    month = Column("Month", String, nullable=True)
    bucket = Column("Bucket", String, nullable=True)
    status = Column("Status", String, nullable=True)
