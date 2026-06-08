from sqlalchemy import Column, Integer, String
from ..database import Base

class InfraClimateProofing(Base):
    __tablename__ = "Infra Climate Proofing"

    id = Column(Integer, primary_key=True, index=True)
    circle = Column("Circle", String, nullable=True)
    site_id = Column("Siteid", String, index=True, nullable=True)
    uni = Column("Uni", String, nullable=True)
    toco = Column("Toco", String, nullable=True)
    toco_id = Column("Toco-ID", String, nullable=True)
    cluster = Column("Cluster", String, nullable=True)
    district = Column("District", String, nullable=True)
    bz = Column("BZ", String, nullable=True)
    activity = Column("Activity", String, nullable=True)
    final_status = Column("Final Status", String, nullable=True)
    remarks = Column("Remarks", String, nullable=True)
