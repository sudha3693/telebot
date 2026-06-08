from typing import Optional

from .base import FormattedSchema

class NWATrendBase(FormattedSchema):
    site_id: Optional[str] = None
    cluster: Optional[str] = None
    site_principal_owner: Optional[str] = None
    dg_non_dg: Optional[str] = None
    uls: Optional[str] = None
    current_site_status: Optional[str] = None
    owner_issue_sites: Optional[str] = None
    district: Optional[str] = None
    circle: Optional[str] = None
    bz: Optional[str] = None
    cem: Optional[str] = None
    avl_tech: Optional[str] = None
    cmo: Optional[str] = None
    fifth_nov_incidence: Optional[str] = None
    mtd_incidence: Optional[str] = None
    nov_22: Optional[str] = None
    dec_22: Optional[str] = None
    jan_23: Optional[str] = None
    feb_23: Optional[str] = None
    mar_23: Optional[str] = None
    apr_23: Optional[str] = None
    may_23: Optional[str] = None
    jun_23: Optional[str] = None
    jul_23: Optional[str] = None
    aug_23: Optional[str] = None
    sep_23: Optional[str] = None
    oct_23: Optional[str] = None
    nov_23: Optional[str] = None
    dec_23: Optional[str] = None
    jan_24: Optional[str] = None
    feb_24: Optional[str] = None
    mar_24: Optional[str] = None
    apr_24: Optional[str] = None
    may_24: Optional[str] = None
    jun_24: Optional[str] = None
    jul_24: Optional[str] = None
    aug_24: Optional[str] = None
    sep_24: Optional[str] = None
    oct_24: Optional[str] = None
    nov_24: Optional[str] = None
    dec_24: Optional[str] = None
    jan_25: Optional[str] = None
    feb_25: Optional[str] = None
    mar_25: Optional[str] = None
    apr_25: Optional[str] = None
    may_25: Optional[str] = None
    jun_25: Optional[str] = None
    jul_25: Optional[str] = None
    aug_25: Optional[str] = None
    sep_25: Optional[str] = None
    oct_25: Optional[str] = None
    nov_25: Optional[str] = None
    dec_25: Optional[str] = None
    jan_26: Optional[str] = None
    feb_26: Optional[str] = None
    mar_26: Optional[str] = None
    apr_26: Optional[str] = None
    may_26: Optional[str] = None
    jun_26: Optional[str] = None
    jul_26: Optional[str] = None
    aug_26: Optional[str] = None
    sep_26: Optional[str] = None
    oct_26: Optional[str] = None
    nov_26: Optional[str] = None
    dec_26: Optional[str] = None

class NWATrendResponse(NWATrendBase):
    id: int

    class Config:
        from_attributes = True
