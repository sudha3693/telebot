from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..schemas.day_wise import DayWiseDetailResponse, DayWiseResponse
from ..services.day_wise_service import DayWiseService
from ..utils.auth import get_current_admin

router = APIRouter(prefix="/api/daywise", tags=["day-wise"])

@router.post("/upload", response_model=List[DayWiseResponse])
async def upload_daywise(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Upload an Excel file with .xlsx or .xls extension")

    try:
        imported = DayWiseService.import_daywise_from_excel(db, file.file)
        return imported
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to import 4G Day Wise file: {exc}") from exc

@router.get("/", response_model=List[DayWiseResponse])
def list_daywise_rows(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    return DayWiseService.get_daywise_rows(db)

@router.get("/search", response_model=DayWiseResponse)
def search_daywise(
    site_id: str,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    row = DayWiseService.get_daywise_by_site_id(db, site_id)
    if not row:
        raise HTTPException(status_code=404, detail="Day-wise row not found")
    return row

@router.get("/search/detail", response_model=DayWiseDetailResponse)
def search_daywise_detail(
    site_id: str,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    payload = DayWiseService.get_daywise_payload_by_site_id(db, site_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Day-wise row not found")
    return payload
