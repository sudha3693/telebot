from datetime import datetime
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.access_request import AccessRequest
from ..models.admin_log import AdminLog
from ..models.upload_log import UploadLog
from ..models.user import User
from ..models.site_list import SiteList1
from ..models.nwa_trend import NWATrend
from ..models.infra_climate_proofing import InfraClimateProofing
from ..services.day_wise_service import DayWiseService
from ..services.nwa_trend_service import NWATrendService
from ..services.upload_intelligence_service import UploadIntelligenceService
from ..services.user_service import UserService
from ..utils.auth import get_current_admin

router = APIRouter(prefix="/api/v2", tags=["v2"])


@router.get("/dashboard/stats")
def dashboard_stats(db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    total_users = db.query(User).filter(User.role == "user").count()
    pending = db.query(User).filter(User.role == "user", User.status == "pending").count()
    active = db.query(User).filter(User.role == "user", User.status == "active").count()
    rejected = db.query(User).filter(User.role == "user", User.status == "rejected").count()
    blocked = db.query(User).filter(User.role == "user", User.status == "blocked").count()
    admin_users = db.query(User).filter(User.role == "admin").count()
    super_admin_users = db.query(User).filter(User.role == "super_admin").count()

    search_logs = db.query(AdminLog).filter(AdminLog.action == "site_search")
    total_searches = search_logs.count()
    top_sites = (
        db.query(AdminLog.target_id, func.count(AdminLog.id).label("total"))
        .filter(AdminLog.action == "site_search", AdminLog.target_type == "site")
        .group_by(AdminLog.target_id)
        .order_by(desc("total"))
        .limit(8)
        .all()
    )

    tech_distribution = (
        db.query(SiteList1.tech, func.count(SiteList1.id).label("total"))
        .group_by(SiteList1.tech)
        .order_by(desc("total"))
        .limit(8)
        .all()
    )

    climate_distribution = (
        db.query(InfraClimateProofing.final_status, func.count(InfraClimateProofing.id).label("total"))
        .group_by(InfraClimateProofing.final_status)
        .order_by(desc("total"))
        .limit(8)
        .all()
    )

    status_distribution = (
        db.query(NWATrend.current_site_status, func.count(NWATrend.id).label("total"))
        .group_by(NWATrend.current_site_status)
        .order_by(desc("total"))
        .limit(6)
        .all()
    )

    last_uploads = db.query(UploadLog).order_by(desc(UploadLog.created_at)).limit(8).all()
    access_requests = db.query(AccessRequest).order_by(desc(AccessRequest.requested_at)).limit(8).all()
    audit_logs = db.query(AdminLog).order_by(desc(AdminLog.created_at)).limit(12).all()

    pending_requests = db.query(AccessRequest).filter(AccessRequest.status == "pending").count()

    total_sites = db.query(SiteList1).count()

    return {
        "viewer": {
            "id": current_admin.id,
            "role": current_admin.role,
            "status": current_admin.status,
            "username": current_admin.username,
        },
        "totals": {
            "users": total_users,
            "pending": pending,
            "active": active,
            "rejected": rejected,
            "blocked": blocked,
            "admins": admin_users,
            "super_admins": super_admin_users,
            "sites": total_sites,
            "searches": total_searches,
            "pending_requests": pending_requests,
        },
        "top_sites": [
            {"site_id": row[0], "total": row[1]} for row in top_sites
        ],
        "tech_distribution": [
            {"label": row[0] or "Unknown", "total": row[1]} for row in tech_distribution
        ],
        "climate_distribution": [
            {"label": row[0] or "Unknown", "total": row[1]} for row in climate_distribution
        ],
        "kpi_summary": [
            {"label": row[0] or "Unknown", "total": row[1]} for row in status_distribution
        ],
        "recent_uploads": [
            {
                "id": row.id,
                "dataset": row.module_name,
                "file_name": row.file_name,
                "status": row.status,
                "inserted_rows": row.inserted_rows,
                "skipped_rows": row.skipped_rows,
                "created_at": row.created_at,
            }
            for row in last_uploads
        ],
        "recent_access_requests": [
            {
                "id": row.id,
                "telegram_id": row.telegram_id,
                "username": row.username,
                "full_name": row.full_name,
                "status": row.status,
                "requested_at": row.requested_at,
            }
            for row in access_requests
        ],
        "audit_logs": [
            {
                "id": row.id,
                "action": row.action,
                "target_type": row.target_type,
                "target_id": row.target_id,
                "details": row.details,
                "created_at": row.created_at,
            }
            for row in audit_logs
        ],
    }


@router.get("/access-requests")
def list_access_requests(
    status: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    query = db.query(AccessRequest)
    if status:
        query = query.filter(AccessRequest.status == status)
    rows = query.order_by(desc(AccessRequest.requested_at)).all()
    return rows


@router.patch("/access-requests/{request_id}")
def review_access_request(
    request_id: int,
    decision: str = Query(..., pattern="^(approve|reject|block)$"),
    note: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    req = db.query(AccessRequest).filter(AccessRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Access request not found")

    user = UserService.get_user_by_telegram_id(db, req.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="Linked user not found")

    status_map = {"approve": "active", "reject": "rejected", "block": "blocked"}
    user.status = status_map[decision]
    user.approved_by = current_admin.id
    user.last_action = decision
    req.status = status_map[decision]
    req.review_note = note
    req.reviewed_at = datetime.utcnow()
    req.reviewed_by = current_admin.id

    db.add(
        AdminLog(
            admin_user_id=current_admin.id,
            action=f"access_{decision}",
            target_type="access_request",
            target_id=str(request_id),
            details=f"Decision={decision}; telegram_id={req.telegram_id}",
        )
    )

    db.commit()
    db.refresh(req)
    return {"message": "Access request updated", "request": req}


@router.get("/search")
def global_search(
    q: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    sort_by: str = Query(default="id", pattern="^(id|username|telegram_id|status)$"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    query = db.query(User).filter(User.role == "user")

    if q:
        q_like = f"%{q.strip()}%"
        query = query.filter(
            (User.username.ilike(q_like))
            | (User.telegram_id.ilike(q_like))
            | (User.full_name.ilike(q_like))
        )

    if status:
        query = query.filter(User.status == status)

    sort_column = getattr(User, sort_by, User.id)
    query = query.order_by(sort_column.asc() if order == "asc" else sort_column.desc())

    users = query.limit(200).all()
    return users


@router.post("/uploads/preview")
async def upload_preview(
    dataset: str = Query(..., pattern="^(daywise|nwa)$"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    preview = UploadIntelligenceService.parse_workbook(content, dataset=dataset, preview_rows=10)
    return preview


@router.post("/uploads/import")
async def import_dataset(
    dataset: str = Query(..., pattern="^(daywise|nwa)$"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    file_like = BytesIO(content)
    preview = UploadIntelligenceService.parse_workbook(content, dataset=dataset, preview_rows=3)

    try:
        if dataset == "daywise":
            UploadIntelligenceService.validate_required_headers(preview, ["site_id"])
            imported = DayWiseService.import_daywise_from_excel(db, file_like)
        else:
            UploadIntelligenceService.validate_required_headers(preview, ["site_id"])
            imported = NWATrendService.import_trends_from_excel(db, file_like)

        inserted_rows = len(imported)
        total_rows = int(preview.get("total_rows", inserted_rows))
        skipped_rows = max(total_rows - inserted_rows, 0)

        db.add(
            UploadLog(
                file_name=file.filename or "uploaded.xlsx",
                module_name=dataset,
                status="success",
                total_rows=total_rows,
                inserted_rows=inserted_rows,
                skipped_rows=skipped_rows,
                created_by=current_admin.id,
            )
        )
        db.add(
            AdminLog(
                admin_user_id=current_admin.id,
                action="upload_import",
                target_type="dataset",
                target_id=dataset,
                details=f"file={file.filename}; inserted={inserted_rows}; skipped={skipped_rows}",
            )
        )
        db.commit()

        return {
            "message": "Import completed",
            "dataset": dataset,
            "inserted_rows": inserted_rows,
            "skipped_rows": skipped_rows,
            "total_rows": total_rows,
        }
    except Exception as exc:
        db.rollback()
        db.add(
            UploadLog(
                file_name=file.filename or "uploaded.xlsx",
                module_name=dataset,
                status="failed",
                total_rows=int(preview.get("total_rows", 0)),
                inserted_rows=0,
                skipped_rows=0,
                error_details=str(exc),
                created_by=current_admin.id,
            )
        )
        db.commit()
        raise HTTPException(status_code=400, detail=f"Import failed: {exc}") from exc


@router.get("/uploads/logs")
def upload_logs(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    rows = db.query(UploadLog).order_by(desc(UploadLog.created_at)).limit(limit).all()
    return rows


@router.get("/activity/logs")
def activity_logs(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    rows = db.query(AdminLog).order_by(desc(AdminLog.created_at)).limit(limit).all()
    return rows