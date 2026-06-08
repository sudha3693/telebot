from pydantic import validator
from typing import Optional

from .base import FormattedSchema

class InfraHygineCorrectionBase(FormattedSchema):
    site_id: Optional[str] = None
    site_name: Optional[str] = None
    principal_owner: Optional[str] = None
    dg_non_dg: Optional[str] = None
    bz: Optional[str] = None
    cluster: Optional[str] = None
    district: Optional[str] = None
    circle: Optional[str] = None
    bucket_category: Optional[str] = None
    closure_date_month: Optional[str] = None
    month: Optional[str] = None
    bucket: Optional[str] = None
    status: Optional[str] = None
    dg_deployment: Optional[str] = None
    bb_deployment: Optional[str] = None
    solar_deployment: Optional[str] = None

    @validator("dg_deployment", "bb_deployment", "solar_deployment", pre=True, always=True)
    def _normalize_optional_text(cls, value):
        return "" if value is None else value

class InfraHygineCorrectionResponse(InfraHygineCorrectionBase):
    id: int

    class Config:
        from_attributes = True
