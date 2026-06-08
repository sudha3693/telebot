from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..schemas.site_list import SiteListResponse
from ..services.site_service import SiteService
from ..utils.site_search import normalize_site_id
from ..utils.auth import get_current_admin

router = APIRouter(prefix="/api/sites", tags=["site-list"])

@router.post("/upload", response_model=List[SiteListResponse])
async def upload_site_list(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Upload an Excel file with .xlsx or .xls extension")

    imported = SiteService.import_sites_from_excel(db, file.file)
    return imported

@router.get("/", response_model=List[SiteListResponse])
def list_site_rows(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    return SiteService.get_sites(db)

@router.get("/search", response_model=Optional[SiteListResponse])
def search_site(
    site_id: str,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    if not normalize_site_id(site_id):
        raise HTTPException(status_code=400, detail="Provide a non-empty site search query")

    site = SiteService.get_site_by_site_id(db, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site row not found")
    return site

@router.get("/search-options", response_model=List[SiteListResponse])
def search_site_options(
    site_id: str,
    limit: int = Query(default=10, ge=1, le=25),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    if not normalize_site_id(site_id):
        raise HTTPException(status_code=400, detail="Provide a non-empty site search query")
    return SiteService.search_sites_by_site_id(db, site_id, limit=limit)

@router.get("/{sr_id}", response_model=SiteListResponse)
def get_site_row(
    sr_id: int,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    site = SiteService.get_site_by_sr_id(db, sr_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site row not found")
    return site
