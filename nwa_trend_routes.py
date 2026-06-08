from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..schemas.nwa_trend import NWATrendResponse
from ..services.nwa_trend_service import NWATrendService
from ..utils.auth import get_current_admin

router = APIRouter(prefix="/api/nwa-trends", tags=["nwa-trend"])

@router.post("/upload", response_model=List[NWATrendResponse])
async def upload_nwa_trend(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Upload an Excel file with .xlsx or .xls extension")

    try:
        imported = NWATrendService.import_trends_from_excel(db, file.file)
        return imported
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to import 4G NWA Trend file: {exc}") from exc

@router.get("/", response_model=List[NWATrendResponse])
def list_nwa_trends(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    return NWATrendService.get_trends(db)

@router.get("/search", response_model=NWATrendResponse)
def search_nwa_trend(
    site_id: str,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    trend = NWATrendService.get_trend_by_site_id(db, site_id)
    if not trend:
        raise HTTPException(status_code=404, detail="Trend row not found")
    return trend
