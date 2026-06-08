from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..schemas.infra_climate_proofing import InfraClimateProofingResponse
from ..services.infra_climate_proofing_service import InfraClimateProofingService
from ..utils.auth import get_current_admin

router = APIRouter(prefix="/api/infra-climate-proofing", tags=["infra-climate-proofing"])

@router.post("/upload", response_model=List[InfraClimateProofingResponse])
async def upload_infra_climate_proofing(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Upload an Excel file with .xlsx or .xls extension")

    imported = InfraClimateProofingService.import_records_from_excel(db, file.file)
    return imported

@router.get("/", response_model=List[InfraClimateProofingResponse])
def list_infra_climate_proofings(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    return InfraClimateProofingService.get_records(db)

@router.get("/search", response_model=InfraClimateProofingResponse)
def search_infra_climate_proofing(
    site_id: str,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    record = InfraClimateProofingService.get_record_by_site_id(db, site_id)
    if not record:
        raise HTTPException(status_code=404, detail="Infra Climate Proofing row not found")
    return record
