import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    blind_index,
    create_access_token,
    encrypt_sensitive,
    get_current_user,
    hash_password,
    verification_code_hash,
    verify_password,
)
from app.db import get_db
from app.models import EmailCode, SmsCode, StudentVerification, User
from app.schemas import (
    DemoVerificationInput,
    EmailBindInput,
    EmailSendInput,
    EmailSendOut,
    LoginInput,
    SmsLoginInput,
    SmsSendInput,
    SmsSendOut,
    TokenOut,
    UserCreate,
    UserOut,
    VerificationChallengeOut,
)
from app.services.email import email_provider
from app.services.sms import sms_provider

router = APIRouter()


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def require_demo_features() -> None:
    if not settings.demo_features_enabled:
        raise HTTPException(status_code=403, detail="课程演示功能未启用")


def validate_image(content: bytes, content_type: str | None) -> str:
    extensions = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
    if content_type not in extensions:
        raise HTTPException(status_code=400, detail="认证材料只允许 JPEG、PNG 或 WebP 图片")
    valid = {
        "image/jpeg": content.startswith(b"\xff\xd8\xff"),
        "image/png": content.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP",
    }
    if not valid[content_type]:
        raise HTTPException(status_code=400, detail="认证材料内容与文件类型不匹配")
    return extensions[content_type]


@router.post("/sms/send", response_model=SmsSendOut)
def send_sms(payload: SmsSendInput, db: Session = Depends(get_db)):
    phone_hash = blind_index(payload.phone)
    existing_user = db.scalar(select(User).where(User.phone_hash == phone_hash))
    if payload.purpose == "register" and existing_user:
        raise HTTPException(status_code=409, detail="该手机号已注册，请使用手机号登录")
    if payload.purpose == "login" and not existing_user:
        raise HTTPException(status_code=404, detail="该手机号尚未注册")
    latest = db.scalar(
        select(SmsCode)
        .where(SmsCode.phone_hash == phone_hash, SmsCode.purpose == payload.purpose)
        .order_by(SmsCode.id.desc())
        .limit(1)
    )
    now = utc_now()
    if latest and latest.sent_at and (now - latest.sent_at).total_seconds() < settings.sms_send_interval_seconds:
        remaining = settings.sms_send_interval_seconds - int((now - latest.sent_at).total_seconds())
        raise HTTPException(status_code=429, detail=f"请在 {remaining} 秒后重试")
    code = f"{secrets.randbelow(1_000_000):06d}"
    sms_provider.send_verification_code(payload.phone, code)
    db.add(
        SmsCode(
            phone_hash=phone_hash,
            code_hash=verification_code_hash(payload.phone, code, payload.purpose),
            purpose=payload.purpose,
            sent_at=now,
            expires_at=now + timedelta(seconds=settings.sms_code_expire_seconds),
        )
    )
    db.commit()
    return SmsSendOut(
        message="验证码已发送",
        expires_in=settings.sms_code_expire_seconds,
        retry_after=settings.sms_send_interval_seconds,
        debug_code=code if settings.app_env != "production" else None,
    )


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    phone_hash = blind_index(payload.phone)
    if db.scalar(select(User).where(User.phone_hash == phone_hash)):
        raise HTTPException(status_code=409, detail="该手机号已注册")
    code_record = db.scalar(
        select(SmsCode)
        .where(
            SmsCode.phone_hash == phone_hash,
            SmsCode.purpose == "register",
            SmsCode.consumed_at.is_(None),
        )
        .order_by(SmsCode.id.desc())
        .limit(1)
    )
    now = utc_now()
    if not code_record or code_record.expires_at < now:
        raise HTTPException(status_code=400, detail="验证码不存在或已过期")
    if code_record.attempts >= 5:
        raise HTTPException(status_code=429, detail="验证码错误次数过多，请重新获取")
    if not secrets.compare_digest(code_record.code_hash, verification_code_hash(payload.phone, payload.sms_code, "register")):
        code_record.attempts += 1
        db.commit()
        raise HTTPException(status_code=400, detail="验证码错误")
    code_record.consumed_at = now
    user = User(
        phone_hash=phone_hash,
        phone_ciphertext=encrypt_sensitive(payload.phone),
        phone_last4=payload.phone[-4:],
        phone_verified_at=now,
        # Student accounts authenticate only with SMS. Keep an unusable random
        # hash because the legacy column remains non-null for administrator accounts.
        password_hash=hash_password(secrets.token_urlsafe(32)),
        name=payload.name,
        verification_status="unverified",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenOut(access_token=create_access_token(user.id, user.role), user=user)


@router.post("/login", response_model=TokenOut)
def login(payload: LoginInput, db: Session = Depends(get_db)):
    identifier = payload.identifier.strip().lower()
    user = db.scalar(select(User).where(User.username == identifier, User.role == "admin"))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="管理员账号或密码错误")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="账号已被禁用，请联系平台管理员")
    return TokenOut(access_token=create_access_token(user.id, user.role), user=user)


@router.post("/sms/login", response_model=TokenOut)
def login_with_sms(payload: SmsLoginInput, db: Session = Depends(get_db)):
    phone_hash = blind_index(payload.phone)
    user = db.scalar(select(User).where(User.phone_hash == phone_hash))
    if not user:
        raise HTTPException(status_code=401, detail="手机号或验证码错误")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="账号已被禁用，请联系平台管理员")
    code_record = db.scalar(
        select(SmsCode)
        .where(
            SmsCode.phone_hash == phone_hash,
            SmsCode.purpose == "login",
            SmsCode.consumed_at.is_(None),
        )
        .order_by(SmsCode.id.desc())
        .limit(1)
    )
    now = utc_now()
    if not code_record or code_record.expires_at < now:
        raise HTTPException(status_code=400, detail="验证码不存在或已过期")
    if code_record.attempts >= 5:
        raise HTTPException(status_code=429, detail="验证码错误次数过多，请重新获取")
    expected = verification_code_hash(payload.phone, payload.sms_code, "login")
    if not secrets.compare_digest(code_record.code_hash, expected):
        code_record.attempts += 1
        db.commit()
        raise HTTPException(status_code=400, detail="验证码错误")
    code_record.consumed_at = now
    db.commit()
    return TokenOut(access_token=create_access_token(user.id, user.role), user=user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/email/send", response_model=EmailSendOut)
def send_email_code(
    payload: EmailSendInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    email_hash = blind_index(payload.email)
    duplicate = db.scalar(select(User).where(User.email_hash == email_hash, User.id != user.id))
    if duplicate:
        raise HTTPException(status_code=409, detail="该邮箱已绑定其他账号")
    latest = db.scalar(
        select(EmailCode)
        .where(EmailCode.user_id == user.id, EmailCode.email_hash == email_hash)
        .order_by(EmailCode.id.desc())
        .limit(1)
    )
    now = utc_now()
    if latest and latest.sent_at and (now - latest.sent_at).total_seconds() < settings.email_send_interval_seconds:
        remaining = settings.email_send_interval_seconds - int((now - latest.sent_at).total_seconds())
        raise HTTPException(status_code=429, detail=f"请在 {remaining} 秒后重试")
    code = f"{secrets.randbelow(1_000_000):06d}"
    email_provider.send_verification_code(payload.email, code)
    db.add(
        EmailCode(
            user_id=user.id,
            email_hash=email_hash,
            code_hash=verification_code_hash(payload.email, code, "bind_email"),
            sent_at=now,
            expires_at=now + timedelta(seconds=settings.email_code_expire_seconds),
        )
    )
    db.commit()
    return EmailSendOut(
        message="邮箱验证码已发送",
        expires_in=settings.email_code_expire_seconds,
        retry_after=settings.email_send_interval_seconds,
        debug_code=code if settings.app_env != "production" and settings.email_provider == "console" else None,
    )


@router.post("/email/bind", response_model=UserOut)
def bind_email(
    payload: EmailBindInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    email_hash = blind_index(payload.email)
    duplicate = db.scalar(select(User).where(User.email_hash == email_hash, User.id != user.id))
    if duplicate:
        raise HTTPException(status_code=409, detail="该邮箱已绑定其他账号")
    code_record = db.scalar(
        select(EmailCode)
        .where(
            EmailCode.user_id == user.id,
            EmailCode.email_hash == email_hash,
            EmailCode.consumed_at.is_(None),
        )
        .order_by(EmailCode.id.desc())
        .limit(1)
    )
    now = utc_now()
    if not code_record or code_record.expires_at < now:
        raise HTTPException(status_code=400, detail="验证码不存在或已过期")
    if code_record.attempts >= 5:
        raise HTTPException(status_code=429, detail="验证码错误次数过多，请重新获取")
    expected = verification_code_hash(payload.email, payload.code, "bind_email")
    if not secrets.compare_digest(code_record.code_hash, expected):
        code_record.attempts += 1
        db.commit()
        raise HTTPException(status_code=400, detail="验证码错误")
    code_record.consumed_at = now
    user.email_hash = email_hash
    user.email_ciphertext = encrypt_sensitive(payload.email)
    user.email_verified_at = now
    db.commit()
    db.refresh(user)
    return user


@router.delete("/email", status_code=status.HTTP_204_NO_CONTENT)
def unbind_email(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.email_hash = None
    user.email_ciphertext = None
    user.email_verified_at = None
    db.commit()


@router.post("/verification/demo", response_model=UserOut)
def simulate_student_verification(
    payload: DemoVerificationInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_demo_features()
    if user.role != "student" or not user.phone_verified:
        raise HTTPException(status_code=403, detail="仅已验证手机号的学生账号可使用演示认证")
    if user.verification_status == "verified":
        raise HTTPException(status_code=409, detail="学生身份已经认证")
    pending = db.scalar(
        select(StudentVerification).where(
            StudentVerification.user_id == user.id,
            StudentVerification.status == "pending",
        )
    )
    if pending:
        raise HTTPException(status_code=409, detail="已有人工认证申请正在审核，不能切换为演示认证")
    normalized_student_no = "".join(payload.student_no.split()).upper()
    student_no_hash = blind_index(normalized_student_no)
    duplicate = db.scalar(select(User).where(User.student_no_hash == student_no_hash, User.id != user.id))
    if duplicate:
        raise HTTPException(status_code=409, detail="该学号已用于其他账号认证")
    now = utc_now()
    application = StudentVerification(
        user_id=user.id,
        challenge_code=f"DEMO-{secrets.token_hex(3).upper()}",
        status="approved",
        review_note="课程项目演示认证，未连接学校或学信网",
        expires_at=now,
        submitted_at=now,
        reviewed_at=now,
    )
    user.student_no = encrypt_sensitive(normalized_student_no)
    user.student_no_hash = student_no_hash
    user.college = payload.college.strip()
    user.grade = payload.grade.strip()
    user.verification_status = "verified"
    user.verification_method = "demo"
    db.add(application)
    db.commit()
    db.refresh(user)
    return user


@router.post("/verification/challenge", response_model=VerificationChallengeOut)
def create_verification_challenge(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user.phone_verified:
        raise HTTPException(status_code=403, detail="请先完成手机号验证")
    if user.verification_status == "verified":
        raise HTTPException(status_code=409, detail="学生身份已经认证")
    pending = db.scalar(
        select(StudentVerification).where(
            StudentVerification.user_id == user.id,
            StudentVerification.status == "pending",
        )
    )
    if pending:
        raise HTTPException(status_code=409, detail="认证申请正在审核中")
    now = utc_now()
    existing = db.scalar(
        select(StudentVerification)
        .where(
            StudentVerification.user_id == user.id,
            StudentVerification.status == "draft",
            StudentVerification.expires_at > now,
        )
        .order_by(StudentVerification.id.desc())
        .limit(1)
    )
    if existing:
        return existing
    application = StudentVerification(
        user_id=user.id,
        challenge_code=f"HNU-{secrets.token_hex(2).upper()}",
        status="draft",
        expires_at=now + timedelta(minutes=15),
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.post("/verification/submit")
async def submit_verification(
    challenge_id: int = Form(...),
    student_no: str = Form(..., min_length=6, max_length=40),
    college: str = Form(..., min_length=2, max_length=120),
    grade: str = Form(..., min_length=2, max_length=30),
    evidence: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    application = db.get(StudentVerification, challenge_id)
    now = utc_now()
    if not application or application.user_id != user.id:
        raise HTTPException(status_code=404, detail="认证挑战不存在")
    if application.status != "draft" or application.expires_at < now:
        raise HTTPException(status_code=400, detail="认证挑战已失效，请重新获取")
    normalized_student_no = "".join(student_no.split()).upper()
    student_no_hash = blind_index(normalized_student_no)
    duplicate = db.scalar(
        select(User).where(
            User.student_no_hash == student_no_hash,
            User.id != user.id,
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="该学号已用于其他账号认证")
    content = await evidence.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="认证材料不能超过 5 MB")
    extension = validate_image(content, evidence.content_type)
    storage_key = f"{uuid4().hex}{extension}"
    private_dir = Path(settings.private_upload_dir).resolve() / "verifications"
    private_dir.mkdir(parents=True, exist_ok=True)
    (private_dir / storage_key).write_bytes(content)
    application.evidence_storage_key = storage_key
    application.status = "pending"
    application.submitted_at = now
    user.student_no = encrypt_sensitive(normalized_student_no)
    user.student_no_hash = student_no_hash
    user.college = college
    user.grade = grade
    user.verification_status = "pending"
    user.verification_method = "manual"
    db.commit()
    return {"message": "认证申请已提交", "status": "pending"}
