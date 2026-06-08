from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..schemas.dg_deployment import DGDeploymentResponse
from ..services.dg_deployment_service import DGDeploymentService
from ..utils.auth import get_current_admin

router = APIRouter(prefix="/api/dg-deployment", tags=["dg-deployment"])

@router.post("/upload", response_model=List[DGDeploymentResponse])
async def upload_dg_deployment(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Upload an Excel file with .xlsx or .xls extension")

    imported = DGDeploymentService.import_deployments_from_excel(db, file.file)
    return imported

@router.get("/", response_model=List[DGDeploymentResponse])
def list_dg_deployments(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    return DGDeploymentService.get_deployments(db)

@router.get("/{sr_id}", response_model=DGDeploymentResponse)
def get_dg_deployment(
    sr_id: int,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    deployment = DGDeploymentService.get_deployment_by_sr_id(db, sr_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="DG deployment row not found")
    return deployment

@router.get("/search", response_model=DGDeploymentResponse)
def search_dg_deployment(
    site_id: str,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    deployment = DGDeploymentService.get_deployment_by_site_id(db, site_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="DG deployment row not found")
    return deployment
