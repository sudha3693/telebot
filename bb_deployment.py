from sqlalchemy import Column, Integer, String
from ..database import Base

class BBDeployment(Base):
    __tablename__ = "BB Deployment"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column("SITE ID", String, index=True, nullable=True)
    site_id_2 = Column("SITE ID.1", String, nullable=True)
    cluster = Column("Cluster", String, nullable=True)
    district = Column("District", String, nullable=True)
    bz = Column("BZ", String, nullable=True)
    bb_status_final = Column("BB Status Final", String, nullable=True)
    rfi_date = Column("RFI Date", String, nullable=True)
    month = Column("Month", String, nullable=True)
