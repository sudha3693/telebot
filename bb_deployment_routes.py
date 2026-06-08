from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..schemas.bb_deployment import BBDeploymentResponse
from ..services.bb_deployment_service import BBDeploymentService
from ..utils.auth import get_current_admin

router = APIRouter(prefix="/api/bb-deployment", tags=["bb-deployment"])

@router.post("/upload", response_model=List[BBDeploymentResponse])
async def upload_bb_deployment(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Upload an Excel file with .xlsx or .xls extension")

    imported = BBDeploymentService.import_deployments_from_excel(db, file.file)
    return imported

@router.get("/", response_model=List[BBDeploymentResponse])
def list_bb_deployments(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    return BBDeploymentService.get_deployments(db)

@router.get("/search", response_model=BBDeploymentResponse)
def search_bb_deployment(
    site_id: str,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    deployment = BBDeploymentService.get_deployment_by_site_id(db, site_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="BB deployment row not found")
    return deployment
