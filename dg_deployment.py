from sqlalchemy import Column, Integer, String
from ..database import Base

class DGDeployment(Base):
    __tablename__ = "DG Deployment"

    id = Column(Integer, primary_key=True, index=True)
    sr_id = Column("Sr ID", Integer, index=True, nullable=True)
    site_id = Column("Site ID", String, index=True, nullable=True)
    site_id_a = Column("Site ID-A", String, nullable=True)
    site_type = Column("Site Type", String, nullable=True)
    airtel_site_name = Column("Airtel Site Name", String, nullable=True)
    eil_cluster = Column("EIL Cluster", String, nullable=True)
    airtel_zone = Column("Airtel Zone", String, nullable=True)
    state = Column("State", String, nullable=True)
    main_toco = Column("Main TOCO", String, nullable=True)
    toco_id = Column("TOCO ID", String, nullable=True)
    site_type_2 = Column("Site Type 2", String, nullable=True)
    dg_non_dg = Column("DG/Non DG", String, nullable=True)
    rfi_date = Column("RFI Date", String, nullable=True)
    rfi_month = Column("RFI Month", String, nullable=True)
    remarks = Column("Remarks", String, nullable=True)
    new_priority = Column("New Priority", String, nullable=True)
    final_remarks = Column("Final Remarks", String, nullable=True)
    toco_remarks = Column("Toco Remarks", String, nullable=True)
