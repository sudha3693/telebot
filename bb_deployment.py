from typing import Optional

from .base import FormattedSchema

class BBDeploymentBase(FormattedSchema):
    site_id: Optional[str] = None
    site_id_2: Optional[str] = None
    cluster: Optional[str] = None
    district: Optional[str] = None
    bz: Optional[str] = None
    bb_status_final: Optional[str] = None
    rfi_date: Optional[str] = None
    month: Optional[str] = None

class BBDeploymentResponse(BBDeploymentBase):
    id: int

    class Config:
        from_attributes = True
