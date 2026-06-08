from typing import Optional

from .base import FormattedSchema

class SolarDeploymentBase(FormattedSchema):
    airtel_id: Optional[str] = None
    airtel_id_2: Optional[str] = None
    bz: Optional[str] = None
    site_name: Optional[str] = None
    fse_area: Optional[str] = None
    dist: Optional[str] = None
    state: Optional[str] = None
    solar_status: Optional[str] = None
    rfai_date: Optional[str] = None
    month: Optional[str] = None

class SolarDeploymentResponse(SolarDeploymentBase):
    id: int

    class Config:
        from_attributes = True
