from sqlalchemy import select

from app.core.config import settings
from app.db import SessionLocal
from app.models import Category, User
from app.core.security import hash_password


DEFAULT_CATEGORIES = [
    ("教材与学习资料", "resource"),
    ("生活用品", "resource"),
    ("数码设备", "resource"),
    ("技能辅导", "skill"),
    ("设计与媒体", "skill"),
    ("维修与技术", "skill"),
]


def seed_defaults() -> None:
    with SessionLocal() as db:
        if not db.scalar(select(Category).limit(1)):
            db.add_all([Category(name=name, listing_type=listing_type) for name, listing_type in DEFAULT_CATEGORIES])
        admin = db.scalar(select(User).where(User.role == "admin"))
        if admin and not admin.username:
            admin.username = settings.admin_username
        elif settings.admin_password and not admin:
            db.add(
                User(
                    username=settings.admin_username,
                    password_hash=hash_password(settings.admin_password),
                    name="平台管理员",
                    role="admin",
                    verification_status="verified",
                )
            )
        db.commit()
