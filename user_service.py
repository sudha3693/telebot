from sqlalchemy.orm import Session
from ..models.user import User
from ..schemas.user import UserCreate

class UserService:
    @staticmethod
    def get_users(db: Session):
        return db.query(User).filter(User.role == "user").all()

    @staticmethod
    def get_users_by_status(db: Session, status: str):
        return db.query(User).filter(User.role == "user", User.status == status).all()

    @staticmethod
    def get_users_by_role(db: Session, role: str):
        return db.query(User).filter(User.role == role).all()

    @staticmethod
    def get_user_by_telegram_id(db: Session, telegram_id: str):
        return db.query(User).filter(User.telegram_id == str(telegram_id)).first()

    @staticmethod
    def create_user(db: Session, user: UserCreate):
        db_user = User(**user.dict())
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def update_user_status(db: Session, user_id: int, status: str, approved_by: int = None, last_action: str = None):
        db_user = db.query(User).filter(User.id == user_id).first()
        if db_user:
            db_user.status = status
            if approved_by is not None:
                db_user.approved_by = approved_by
            if last_action:
                db_user.last_action = last_action
            db.commit()
            db.refresh(db_user)
            return db_user
        return None

    @staticmethod
    def update_user_role(db: Session, user_id: int, role: str, approved_by: int = None, last_action: str = None):
        db_user = db.query(User).filter(User.id == user_id).first()
        if db_user:
            db_user.role = role
            db_user.is_admin = role in {"admin", "super_admin"}
            if approved_by is not None:
                db_user.approved_by = approved_by
            if last_action:
                db_user.last_action = last_action
            db.commit()
            db.refresh(db_user)
            return db_user
        return None

    @staticmethod
    def delete_user(db: Session, user_id: int):
        db_user = db.query(User).filter(User.id == user_id).first()
        if db_user:
            db.delete(db_user)
            db.commit()
            return True
        return False

    @staticmethod
    def get_status(db: Session, telegram_id: str):
        user = db.query(User).filter(User.telegram_id == str(telegram_id)).first()
        return user.status if user else None
