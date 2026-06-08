from typing import Optional

from .base import FormattedSchema

class InfraClimateProofingBase(FormattedSchema):
    circle: Optional[str] = None
    site_id: Optional[str] = None
    uni: Optional[str] = None
    toco: Optional[str] = None
    toco_id: Optional[str] = None
    cluster: Optional[str] = None
    district: Optional[str] = None
    bz: Optional[str] = None
    activity: Optional[str] = None
    final_status: Optional[str] = None
    remarks: Optional[str] = None

class InfraClimateProofingResponse(InfraClimateProofingBase):
    id: int

    class Config:
        from_attributes = True
