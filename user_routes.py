from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..schemas.user import UserCreate, UserResponse
from ..services.user_service import UserService
from ..services.telegram_service import telegram_service
from ..models.user import User
from ..models.admin_log import AdminLog
from ..utils.auth import get_current_admin, get_current_super_admin

router = APIRouter(prefix="/api/users", tags=["users"])

@router.get("/", response_model=List[UserResponse])
def read_users(db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    return UserService.get_users(db)

@router.get("/status/{status}", response_model=List[UserResponse])
def read_users_by_status(status: str, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    return UserService.get_users_by_status(db, status)

@router.get("/role/{role}", response_model=List[UserResponse])
def read_users_by_role(role: str, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    return UserService.get_users_by_role(db, role)

@router.post("/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    db_user = UserService.get_user_by_telegram_id(db, user.telegram_id)
    if db_user:
        raise HTTPException(status_code=400, detail="Telegram ID already registered")
    return UserService.create_user(db, user)

@router.patch("/{user_id}/approve", response_model=UserResponse)
async def approve_user(user_id: int, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.role in {"admin", "super_admin"} and current_admin.role != "super_admin":
        raise HTTPException(status_code=403, detail="Cannot modify admin users")

    db_user = UserService.update_user_status(db, user_id, "active", approved_by=current_admin.id, last_action="approved")
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db.add(
        AdminLog(
            admin_user_id=current_admin.id,
            action="user_approved",
            target_type="user",
            target_id=str(db_user.id),
            details=f"telegram_id={db_user.telegram_id}",
        )
    )
    db.commit()
    
    # Notify user
    await telegram_service.send_message(db_user.telegram_id, "✅ Your request has been approved! You can now use the bot.")
    return db_user

@router.patch("/{user_id}/unapprove", response_model=UserResponse)
async def unapprove_user(user_id: int, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.role in {"admin", "super_admin"} and current_admin.role != "super_admin":
        raise HTTPException(status_code=403, detail="Cannot modify admin users")

    db_user = UserService.update_user_status(db, user_id, "pending", approved_by=current_admin.id, last_action="unapproved")
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db.add(
        AdminLog(
            admin_user_id=current_admin.id,
            action="user_unapproved",
            target_type="user",
            target_id=str(db_user.id),
            details=f"telegram_id={db_user.telegram_id}",
        )
    )
    db.commit()

    await telegram_service.send_message(db_user.telegram_id, "⏳ Your telecom access is set to pending review.")
    return db_user

@router.patch("/{user_id}/reject", response_model=UserResponse)
async def reject_user(user_id: int, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.role in {"admin", "super_admin"} and current_admin.role != "super_admin":
        raise HTTPException(status_code=403, detail="Cannot modify admin users")

    db_user = UserService.update_user_status(db, user_id, "rejected", approved_by=current_admin.id, last_action="rejected")
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db.add(
        AdminLog(
            admin_user_id=current_admin.id,
            action="user_rejected",
            target_type="user",
            target_id=str(db_user.id),
            details=f"telegram_id={db_user.telegram_id}",
        )
    )
    db.commit()
    
    # Notify user
    await telegram_service.send_message(db_user.telegram_id, "❌ Sorry, your request was denied by the administrator.")
    return db_user

@router.patch("/{user_id}/block", response_model=UserResponse)
async def block_user(user_id: int, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.role in {"admin", "super_admin"} and current_admin.role != "super_admin":
        raise HTTPException(status_code=403, detail="Cannot block admin users")

    db_user = UserService.update_user_status(db, user_id, "blocked", approved_by=current_admin.id, last_action="blocked")
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db.add(
        AdminLog(
            admin_user_id=current_admin.id,
            action="user_blocked",
            target_type="user",
            target_id=str(db_user.id),
            details=f"telegram_id={db_user.telegram_id}",
        )
    )
    db.commit()

    await telegram_service.send_message(db_user.telegram_id, "🚫 Your telecom access has been blocked by an administrator.")
    return db_user

@router.patch("/{user_id}/unblock", response_model=UserResponse)
async def unblock_user(user_id: int, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.role in {"admin", "super_admin"} and current_admin.role != "super_admin":
        raise HTTPException(status_code=403, detail="Cannot modify admin users")

    db_user = UserService.update_user_status(db, user_id, "active", approved_by=current_admin.id, last_action="unblocked")
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db.add(
        AdminLog(
            admin_user_id=current_admin.id,
            action="user_unblocked",
            target_type="user",
            target_id=str(db_user.id),
            details=f"telegram_id={db_user.telegram_id}",
        )
    )
    db.commit()

    await telegram_service.send_message(db_user.telegram_id, "🔓 Your telecom access has been restored.")
    return db_user

@router.patch("/{user_id}/reapprove", response_model=UserResponse)
async def reapprove_user(user_id: int, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.role in {"admin", "super_admin"} and current_admin.role != "super_admin":
        raise HTTPException(status_code=403, detail="Cannot modify admin users")

    db_user = UserService.update_user_status(db, user_id, "active", approved_by=current_admin.id, last_action="reapproved")
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db.add(
        AdminLog(
            admin_user_id=current_admin.id,
            action="user_reapproved",
            target_type="user",
            target_id=str(db_user.id),
            details=f"telegram_id={db_user.telegram_id}",
        )
    )
    db.commit()

    await telegram_service.send_message(db_user.telegram_id, "✅ Your telecom access has been re-approved.")
    return db_user

@router.patch("/{user_id}/unreject", response_model=UserResponse)
async def unreject_user(user_id: int, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.role in {"admin", "super_admin"} and current_admin.role != "super_admin":
        raise HTTPException(status_code=403, detail="Cannot modify admin users")

    db_user = UserService.update_user_status(db, user_id, "pending", approved_by=current_admin.id, last_action="unrejected")
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db.add(
        AdminLog(
            admin_user_id=current_admin.id,
            action="user_unrejected",
            target_type="user",
            target_id=str(db_user.id),
            details=f"telegram_id={db_user.telegram_id}",
        )
    )
    db.commit()

    await telegram_service.send_message(db_user.telegram_id, "⏳ Your telecom access is set to pending review.")
    return db_user

@router.patch("/{user_id}/make-admin", response_model=UserResponse)
def make_admin(user_id: int, db: Session = Depends(get_db), current_admin: User = Depends(get_current_super_admin)):
    db_user = UserService.update_user_role(db, user_id, "admin", approved_by=current_admin.id, last_action="make_admin")
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db.add(
        AdminLog(
            admin_user_id=current_admin.id,
            action="user_promoted_admin",
            target_type="user",
            target_id=str(db_user.id),
            details=f"telegram_id={db_user.telegram_id}",
        )
    )
    db.commit()
    return db_user

@router.patch("/{user_id}/remove-admin", response_model=UserResponse)
def remove_admin(user_id: int, db: Session = Depends(get_db), current_admin: User = Depends(get_current_super_admin)):
    db_user = UserService.update_user_role(db, user_id, "user", approved_by=current_admin.id, last_action="remove_admin")
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db.add(
        AdminLog(
            admin_user_id=current_admin.id,
            action="user_demoted_admin",
            target_type="user",
            target_id=str(db_user.id),
            details=f"telegram_id={db_user.telegram_id}",
        )
    )
    db.commit()
    return db_user

@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    success = UserService.delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}
