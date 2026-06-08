from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..schemas.solar_deployment import SolarDeploymentResponse
from ..services.solar_deployment_service import SolarDeploymentService
from ..utils.auth import get_current_admin

router = APIRouter(prefix="/api/solar-deployment", tags=["solar-deployment"])

@router.post("/upload", response_model=List[SolarDeploymentResponse])
async def upload_solar_deployment(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Upload an Excel file with .xlsx or .xls extension")

    imported = SolarDeploymentService.import_deployments_from_excel(db, file.file)
    return imported

@router.get("/", response_model=List[SolarDeploymentResponse])
def list_solar_deployments(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    return SolarDeploymentService.get_deployments(db)

@router.get("/search", response_model=SolarDeploymentResponse)
def search_solar_deployment(
    airtel_id: str,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    deployment = SolarDeploymentService.get_deployment_by_airtel_id(db, airtel_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Solar deployment row not found")
    return deployment
