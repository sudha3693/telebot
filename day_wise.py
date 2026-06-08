from pydantic import BaseModel
from typing import List, Optional

from .base import FormattedSchema

class DayWiseBase(FormattedSchema):
    site_id: Optional[str] = None
    cluster: Optional[str] = None
    current_site_status: Optional[str] = None
    owner_issue_sites: Optional[str] = None
    five_g_available: Optional[str] = None
    district: Optional[str] = None
    town: Optional[str] = None
    top_8_towns: Optional[str] = None
    circle: Optional[str] = None
    bz: Optional[str] = None

    d2_feb: Optional[str] = None
    d3_feb: Optional[str] = None
    d4_feb: Optional[str] = None
    d5_feb: Optional[str] = None
    d6_feb: Optional[str] = None
    d7_feb: Optional[str] = None
    d8_feb: Optional[str] = None
    d9_feb: Optional[str] = None
    d10_feb: Optional[str] = None
    d11_feb: Optional[str] = None
    d12_feb: Optional[str] = None
    d13_feb: Optional[str] = None
    d14_feb: Optional[str] = None
    d15_feb: Optional[str] = None
    d16_feb: Optional[str] = None
    d17_feb: Optional[str] = None
    d18_feb: Optional[str] = None
    d19_feb: Optional[str] = None
    d20_feb: Optional[str] = None
    d21_feb: Optional[str] = None
    d22_feb: Optional[str] = None
    d23_feb: Optional[str] = None
    d24_feb: Optional[str] = None
    d25_feb: Optional[str] = None
    d26_feb: Optional[str] = None
    d27_feb: Optional[str] = None
    d28_feb: Optional[str] = None
    d1_mar: Optional[str] = None
    d2_mar: Optional[str] = None
    d3_mar: Optional[str] = None
    d4_mar: Optional[str] = None
    d5_mar: Optional[str] = None
    d6_mar: Optional[str] = None
    d7_mar: Optional[str] = None
    d8_mar: Optional[str] = None
    d9_mar: Optional[str] = None
    d10_mar: Optional[str] = None
    d11_mar: Optional[str] = None
    d12_mar: Optional[str] = None
    d13_mar: Optional[str] = None
    d14_mar: Optional[str] = None
    d15_mar: Optional[str] = None
    d16_mar: Optional[str] = None
    d17_mar: Optional[str] = None
    d18_mar: Optional[str] = None
    d19_mar: Optional[str] = None
    d20_mar: Optional[str] = None
    d21_mar: Optional[str] = None
    d22_mar: Optional[str] = None
    d23_mar: Optional[str] = None
    d24_mar: Optional[str] = None
    d25_mar: Optional[str] = None
    d26_mar: Optional[str] = None
    d27_mar: Optional[str] = None
    d28_mar: Optional[str] = None
    d29_mar: Optional[str] = None
    d30_mar: Optional[str] = None
    d31_mar: Optional[str] = None

class DayWiseResponse(DayWiseBase):
    id: int

    class Config:
        from_attributes = True

class DayWiseTrendPoint(FormattedSchema):
    label: str
    attribute: str
    value: Optional[str] = None

class DayWiseDetailResponse(DayWiseResponse):
    trend_points: List[DayWiseTrendPoint] = []
    trend_column_labels: List[str] = []
