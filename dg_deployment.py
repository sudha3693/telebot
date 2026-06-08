from typing import Optional

from .base import FormattedSchema

class DGDeploymentBase(FormattedSchema):
    sr_id: Optional[int] = None
    site_id: Optional[str] = None
    site_id_a: Optional[str] = None
    site_type: Optional[str] = None
    airtel_site_name: Optional[str] = None
    eil_cluster: Optional[str] = None
    airtel_zone: Optional[str] = None
    state: Optional[str] = None
    main_toco: Optional[str] = None
    toco_id: Optional[str] = None
    site_type_2: Optional[str] = None
    dg_non_dg: Optional[str] = None
    rfi_date: Optional[str] = None
    rfi_month: Optional[str] = None
    remarks: Optional[str] = None
    new_priority: Optional[str] = None
    final_remarks: Optional[str] = None
    toco_remarks: Optional[str] = None

class DGDeploymentResponse(DGDeploymentBase):
    id: int

    class Config:
        from_attributes = True
