from pydantic import validator
from typing import Optional

from .base import FormattedSchema

class SiteListBase(FormattedSchema):
    sr_id: Optional[int] = None
    site_id: Optional[str] = None
    tech_id: Optional[str] = None
    airtel_site_name: Optional[str] = None
    airtel_zone: Optional[str] = None
    dist: Optional[str] = None
    airtel_zone_2: Optional[str] = None
    state: Optional[str] = None
    main_toco: Optional[str] = None
    pay_load_4g: Optional[str] = None
    toco_id: Optional[str] = None
    toco_site_name: Optional[str] = None
    toco_zone: Optional[str] = None
    site_type: Optional[str] = None
    no_of_link: Optional[str] = None
    tech: Optional[str] = None
    dg_non_dg: Optional[str] = None
    non_dg_type: Optional[str] = None
    eb_non_eb: Optional[str] = None
    eb_status: Optional[str] = None
    solar_non_solar: Optional[str] = None
    rfs_date: Optional[str] = None
    dependency: Optional[str] = None
    ms_avg_churn: Optional[str] = None
    opex_cost: Optional[str] = None
    ubr_ftth: Optional[str] = None
    district: Optional[str] = None
    district_2: Optional[str] = None
    lt_ht: Optional[str] = None
    pay_load_5g: Optional[str] = None
    available_5g: Optional[str] = None
    enode_b: Optional[str] = None
    site_id_2: Optional[str] = None

    @validator("site_type", "no_of_link", "dependency", pre=True, always=True)
    def _normalize_optional_text(cls, value):
        return "" if value is None else value

class SiteListResponse(SiteListBase):
    id: int

    class Config:
        from_attributes = True
