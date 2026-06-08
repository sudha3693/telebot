from sqlalchemy import Column, Integer, String
from ..database import Base

class SolarDeployment(Base):
    __tablename__ = "Solar Deployment"

    id = Column(Integer, primary_key=True, index=True)
    airtel_id = Column("Airtel ID", String, index=True, nullable=True)
    airtel_id_2 = Column("Airtel ID.1", String, nullable=True)
    bz = Column("BZ", String, nullable=True)
    site_name = Column("Site Name", String, nullable=True)
    fse_area = Column("FSE AREA", String, nullable=True)
    dist = Column("Dist", String, nullable=True)
    state = Column("State", String, nullable=True)
    solar_status = Column("Solar Status", String, nullable=True)
    rfai_date = Column("RFAI Date", String, nullable=True)
    month = Column("Month", String, nullable=True)
