from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..schemas.infra_hygine_correction import InfraHygineCorrectionResponse
from ..services.infra_hygine_correction_service import InfraHygineCorrectionService
from ..utils.auth import get_current_admin

router = APIRouter(prefix="/api/infra-hygine-correction", tags=["infra-hygine-correction"])

@router.post("/upload", response_model=List[InfraHygineCorrectionResponse])
async def upload_infra_hygine_correction(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Upload an Excel file with .xlsx or .xls extension")

    imported = InfraHygineCorrectionService.import_records_from_excel(db, file.file)
    return imported

@router.get("/", response_model=List[InfraHygineCorrectionResponse])
def list_infra_hygine_corrections(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    return InfraHygineCorrectionService.get_records_payload(db)

@router.get("/search", response_model=InfraHygineCorrectionResponse)
def search_infra_hygine_correction(
    site_id: str,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    record = InfraHygineCorrectionService.get_record_payload_by_site_id(db, site_id)
    if not record:
        raise HTTPException(status_code=404, detail="Infra Hygine Correction row not found")
    return record
