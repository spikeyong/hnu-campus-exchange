from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.v1.listings import listing_out
from app.core.config import settings
from app.core.security import require_admin
from app.db import get_db
from app.models import (
    AdminActionLog,
    Category,
    CreditEvent,
    Listing,
    Report,
    StudentVerification,
    Transaction,
    TransactionMessage,
    User,
)
from app.schemas import (
    AdminActionLogOut,
    AdminCategoryInput,
    AdminCategoryOut,
    AdminCategoryUpdate,
    AdminFeatureInput,
    AdminListingOut,
    AdminListingPage,
    AdminListingStatusInput,
    AdminLogPage,
    AdminReportDetailOut,
    AdminReportMessageOut,
    AdminReportOut,
    AdminResolution,
    AdminStatsOut,
    AdminUserDetailOut,
    AdminUserDisableInput,
    AdminUserEnableInput,
    AdminUserOut,
    AdminUserPage,
    StudentVerificationOut,
)

router = APIRouter()


def now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def count_rows(db: Session, model, *conditions) -> int:
    return int(db.scalar(select(func.count()).select_from(model).where(*conditions)) or 0)


def write_log(
    db: Session,
    admin: User,
    action: str,
    target_type: str,
    target_id: int | None,
    summary: str,
    detail: str | None = None,
) -> None:
    db.add(
        AdminActionLog(
            admin_id=admin.id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            summary=summary,
            detail=detail,
        )
    )


def delete_reviewed_evidence(application: StudentVerification) -> None:
    if not application.evidence_storage_key:
        return
    target = Path(settings.private_upload_dir).resolve() / "verifications" / application.evidence_storage_key
    target.unlink(missing_ok=True)
    application.evidence_storage_key = None


def verification_out(item: StudentVerification) -> StudentVerificationOut:
    return StudentVerificationOut(
        id=item.id,
        user_id=item.user_id,
        user_name=item.user.name,
        phone_masked=item.user.account_masked,
        student_no_masked=item.user.student_no_masked,
        college=item.user.college,
        grade=item.user.grade,
        challenge_code=item.challenge_code,
        status=item.status,
        evidence_url=f"/api/v1/admin/verifications/{item.id}/evidence" if item.evidence_storage_key else None,
        review_note=item.review_note,
        reviewer_name=item.reviewer.name if item.reviewer else None,
        reviewed_at=item.reviewed_at,
        submitted_at=item.submitted_at,
    )


def admin_listing_out(item: Listing, db: Session) -> AdminListingOut:
    base = listing_out(item)
    report_count = count_rows(
        db,
        Report,
        Report.target_type == "listing",
        Report.target_id == item.id,
    )
    return AdminListingOut(
        **base.model_dump(),
        status_reason=item.status_reason,
        featured_reason=item.featured_reason,
        owner_status=item.owner.status if item.owner else None,
        owner_verification_status=item.owner.verification_status if item.owner else None,
        report_count=report_count,
    )


def admin_user_out(item: User, db: Session) -> AdminUserOut:
    listing_count = count_rows(db, Listing, Listing.owner_id == item.id, Listing.status != "deleted")
    completed_transactions = count_rows(
        db,
        Transaction,
        or_(Transaction.initiator_id == item.id, Transaction.provider_id == item.id),
        Transaction.status == "completed",
    )
    return AdminUserOut(
        id=item.id,
        name=item.name,
        account_masked=item.account_masked,
        phone_verified=item.phone_verified,
        email_masked=item.email_masked,
        role=item.role,
        verification_status=item.verification_status,
        verification_method=item.verification_method,
        credit_score=item.credit_score,
        status=item.status,
        status_reason=item.status_reason,
        created_at=item.created_at,
        listing_count=listing_count,
        completed_transactions=completed_transactions,
    )


def report_target_info(report: Report, db: Session) -> tuple[str | None, int | None, str | None]:
    target_label: str | None = None
    target_user_id: int | None = None
    transaction_title: str | None = None

    if report.target_type == "listing":
        listing = db.get(Listing, report.target_id)
        if listing:
            target_label = listing.title
            target_user_id = listing.owner_id
    elif report.target_type == "user":
        target = db.get(User, report.target_id)
        if target:
            target_label = target.name
            target_user_id = target.id
    elif report.target_type == "transaction":
        transaction = db.get(Transaction, report.target_id)
        if transaction:
            target_label = f"交易 #{transaction.id}"
            transaction_title = transaction.listing.title if transaction.listing else None

    if report.transaction_id:
        transaction = db.get(Transaction, report.transaction_id)
        if transaction and transaction.listing:
            transaction_title = transaction.listing.title

    return target_label, target_user_id, transaction_title


def admin_report_out(report: Report, db: Session) -> AdminReportOut:
    reporter = db.get(User, report.reporter_id)
    handler = db.get(User, report.handler_id) if report.handler_id else None
    target_label, target_user_id, transaction_title = report_target_info(report, db)
    return AdminReportOut(
        id=report.id,
        reporter_id=report.reporter_id,
        reporter_name=reporter.name if reporter else None,
        target_type=report.target_type,
        target_id=report.target_id,
        target_label=target_label,
        target_user_id=target_user_id,
        transaction_id=report.transaction_id,
        transaction_title=transaction_title,
        reason=report.reason,
        description=report.description,
        status=report.status,
        resolution=report.resolution,
        handler_name=handler.name if handler else None,
        handled_at=report.handled_at,
        created_at=report.created_at,
    )


def admin_category_out(item: Category, db: Session) -> AdminCategoryOut:
    return AdminCategoryOut(
        id=item.id,
        name=item.name,
        listing_type=item.listing_type,
        is_active=item.is_active,
        sort_order=item.sort_order,
        listing_count=count_rows(db, Listing, Listing.category_id == item.id, Listing.status != "deleted"),
    )


@router.get("/stats", response_model=AdminStatsOut)
def admin_stats(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    since = now_utc() - timedelta(days=7)
    active_statuses = ("pending_provider", "pending_initiator", "agreed", "provider_confirmed", "requester_confirmed")
    return AdminStatsOut(
        pending_verifications=count_rows(db, StudentVerification, StudentVerification.status == "pending"),
        pending_reports=count_rows(db, Report, Report.status == "pending"),
        users_total=count_rows(db, User),
        users_verified=count_rows(
            db, User, User.role == "student", User.verification_status == "verified"
        ),
        users_disabled=count_rows(db, User, User.status != "active"),
        listings_published=count_rows(db, Listing, Listing.status == "published"),
        listings_offline=count_rows(db, Listing, Listing.status == "offline"),
        listings_featured=count_rows(db, Listing, Listing.is_featured.is_(True)),
        transactions_active=count_rows(db, Transaction, Transaction.status.in_(active_statuses)),
        transactions_completed=count_rows(db, Transaction, Transaction.status == "completed"),
        new_users_7d=count_rows(db, User, User.created_at >= since),
        new_listings_7d=count_rows(db, Listing, Listing.created_at >= since, Listing.status != "deleted"),
    )


@router.get("/verifications", response_model=list[StudentVerificationOut])
def list_verifications(
    status: str = Query(default="pending", pattern="^(pending|approved|rejected|all)$"),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    stmt = select(StudentVerification).options(selectinload(StudentVerification.user), selectinload(StudentVerification.reviewer))
    if status != "all":
        stmt = stmt.where(StudentVerification.status == status)
    if status == "pending":
        stmt = stmt.order_by(StudentVerification.submitted_at.asc())
    else:
        stmt = stmt.order_by(StudentVerification.submitted_at.desc())
    return [verification_out(item) for item in db.scalars(stmt)]


@router.get("/verifications/{verification_id}/evidence")
def verification_evidence(verification_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    application = db.get(StudentVerification, verification_id)
    if not application or not application.evidence_storage_key:
        raise HTTPException(status_code=404, detail="认证材料不存在")
    target = Path(settings.private_upload_dir).resolve() / "verifications" / application.evidence_storage_key
    if not target.is_file():
        raise HTTPException(status_code=404, detail="认证材料文件不存在")
    return FileResponse(target)


@router.post("/verifications/{verification_id}/approve", response_model=StudentVerificationOut)
def approve_verification(
    verification_id: int,
    review_note: str = Query(default="材料核验通过", max_length=500),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    application = db.get(StudentVerification, verification_id)
    if not application:
        raise HTTPException(status_code=404, detail="认证申请不存在")
    if application.status != "pending":
        raise HTTPException(status_code=409, detail="该认证申请已经处理")
    application.status = "approved"
    application.review_note = review_note
    application.reviewer_id = admin.id
    application.reviewed_at = now_utc()
    application.user.verification_status = "verified"
    application.user.verification_method = "manual"
    delete_reviewed_evidence(application)
    write_log(
        db,
        admin,
        "verification_approve",
        "verification",
        application.id,
        f"通过 {application.user.name} 的学生认证",
        review_note,
    )
    db.commit()
    db.refresh(application)
    return verification_out(application)


@router.post("/verifications/{verification_id}/reject", response_model=StudentVerificationOut)
def reject_verification(
    verification_id: int,
    review_note: str = Query(default="材料无法证明在校学生身份", max_length=500),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    application = db.get(StudentVerification, verification_id)
    if not application:
        raise HTTPException(status_code=404, detail="认证申请不存在")
    if application.status != "pending":
        raise HTTPException(status_code=409, detail="该认证申请已经处理")
    application.status = "rejected"
    application.review_note = review_note
    application.reviewer_id = admin.id
    application.reviewed_at = now_utc()
    application.user.verification_status = "rejected"
    application.user.verification_method = "manual"
    application.user.student_no = None
    application.user.student_no_hash = None
    application.user.college = None
    application.user.grade = None
    delete_reviewed_evidence(application)
    write_log(
        db,
        admin,
        "verification_reject",
        "verification",
        application.id,
        f"驳回 {application.user.name} 的学生认证",
        review_note,
    )
    db.commit()
    db.refresh(application)
    return verification_out(application)


@router.get("/listings", response_model=AdminListingPage)
def admin_listings(
    keyword: str | None = None,
    status: str = Query(default="all", pattern="^(all|published|offline|deleted|reserved|completed)$"),
    listing_type: str | None = Query(default=None, alias="type", pattern="^(resource|skill)$"),
    category_id: int | None = None,
    featured: bool | None = None,
    owner_id: int | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    stmt = select(Listing).options(
        selectinload(Listing.owner),
        selectinload(Listing.category),
        selectinload(Listing.images),
    )
    if keyword:
        like = f"%{keyword.strip()}%"
        stmt = stmt.where(or_(Listing.title.ilike(like), Listing.description.ilike(like)))
    if status == "all":
        stmt = stmt.where(Listing.status != "deleted")
    else:
        stmt = stmt.where(Listing.status == status)
    if listing_type:
        stmt = stmt.where(Listing.type == listing_type)
    if category_id:
        stmt = stmt.where(Listing.category_id == category_id)
    if featured is not None:
        stmt = stmt.where(Listing.is_featured.is_(featured))
    if owner_id:
        stmt = stmt.where(Listing.owner_id == owner_id)
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    items = list(
        db.scalars(
            stmt.order_by(Listing.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
    )
    return AdminListingPage(
        items=[admin_listing_out(item, db) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/listings/{listing_id}", response_model=AdminListingOut)
def admin_listing_detail(listing_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.get(Listing, listing_id)
    if not item:
        raise HTTPException(status_code=404, detail="发布信息不存在")
    return admin_listing_out(item, db)


@router.post("/listings/{listing_id}/status", response_model=AdminListingOut)
def admin_listing_status(
    listing_id: int,
    payload: AdminListingStatusInput,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    item = db.get(Listing, listing_id)
    if not item:
        raise HTTPException(status_code=404, detail="发布信息不存在")
    if item.status == "deleted":
        raise HTTPException(status_code=400, detail="已删除的发布不能恢复")
    if item.status == payload.status:
        raise HTTPException(status_code=409, detail="发布已经是该状态")

    if payload.status == "offline":
        if item.status not in ("published",):
            raise HTTPException(status_code=409, detail="交易中或已完成的发布不能直接下架，请先处理关联交易")
        item.status = "offline"
        item.is_featured = False
        item.featured_at = None
        item.featured_by = None
        item.featured_reason = None
        action = "listing_offline"
        summary = f"下架帖子《{item.title}》"
    else:
        if item.status != "offline":
            raise HTTPException(status_code=409, detail="只有已下架帖子可以恢复")
        item.status = "published"
        action = "listing_restore"
        summary = f"恢复帖子《{item.title}》"

    item.status_reason = payload.reason
    item.moderated_at = now_utc()
    item.moderated_by = admin.id
    write_log(db, admin, action, "listing", item.id, summary, payload.reason)
    db.commit()
    db.refresh(item)
    return admin_listing_out(item, db)


@router.post("/listings/{listing_id}/feature", response_model=AdminListingOut)
def feature_listing(
    listing_id: int,
    payload: AdminFeatureInput,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    item = db.get(Listing, listing_id)
    if not item:
        raise HTTPException(status_code=404, detail="发布信息不存在")
    if item.status != "published":
        raise HTTPException(status_code=409, detail="只有公开中的帖子可以加精")
    if item.is_featured:
        raise HTTPException(status_code=409, detail="该帖子已经是精华帖")
    item.is_featured = True
    item.featured_at = now_utc()
    item.featured_by = admin.id
    item.featured_reason = payload.reason
    write_log(db, admin, "listing_feature", "listing", item.id, f"加精帖子《{item.title}》", payload.reason)
    db.commit()
    db.refresh(item)
    return admin_listing_out(item, db)


@router.delete("/listings/{listing_id}/feature", response_model=AdminListingOut)
def unfeature_listing(listing_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.get(Listing, listing_id)
    if not item:
        raise HTTPException(status_code=404, detail="发布信息不存在")
    if not item.is_featured:
        raise HTTPException(status_code=409, detail="该帖子不是精华帖")
    item.is_featured = False
    item.featured_at = None
    item.featured_by = None
    item.featured_reason = None
    write_log(db, admin, "listing_unfeature", "listing", item.id, f"取消精华《{item.title}》")
    db.commit()
    db.refresh(item)
    return admin_listing_out(item, db)


@router.get("/reports", response_model=list[AdminReportOut])
def list_reports(
    status: str = Query(default="all", pattern="^(all|pending|resolved)$"),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    stmt = select(Report).order_by(Report.created_at.desc())
    if status != "all":
        stmt = stmt.where(Report.status == status)
    return [admin_report_out(item, db) for item in db.scalars(stmt)]


@router.get("/reports/{report_id}", response_model=AdminReportDetailOut)
def report_detail(report_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="举报不存在")
    base = admin_report_out(report, db).model_dump()
    transaction_id = report.transaction_id or (report.target_id if report.target_type == "transaction" else None)
    transaction = db.get(Transaction, transaction_id) if transaction_id else None
    messages: list[AdminReportMessageOut] = []
    if transaction:
        for message in db.scalars(
            select(TransactionMessage)
            .where(TransactionMessage.transaction_id == transaction.id)
            .order_by(TransactionMessage.created_at.asc())
        ):
            sender = db.get(User, message.sender_id)
            messages.append(
                AdminReportMessageOut(
                    id=message.id,
                    sender_name=sender.name if sender else "已注销用户",
                    content=message.content,
                    created_at=message.created_at,
                )
            )
    base["transaction_id"] = transaction.id if transaction else report.transaction_id
    return AdminReportDetailOut(
        **base,
        transaction_status=transaction.status if transaction else None,
        transaction_price=transaction.proposed_price if transaction else None,
        transaction_time=transaction.proposed_time if transaction else None,
        transaction_location=transaction.proposed_location if transaction else None,
        messages=messages,
    )


@router.post("/reports/{report_id}/resolve", response_model=AdminReportOut)
def resolve_report(
    report_id: int,
    payload: AdminResolution,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="举报不存在")
    if report.status == "resolved":
        raise HTTPException(status_code=409, detail="该举报已经处理")

    target_user_id = payload.score_user_id
    if payload.score_delta:
        if not target_user_id and report.target_type == "user":
            target_user_id = report.target_id
        if not target_user_id:
            raise HTTPException(status_code=400, detail="调整信用分时必须指定目标用户")
        target = db.get(User, target_user_id)
        if not target:
            raise HTTPException(status_code=404, detail="信用调整目标用户不存在")
        target.credit_score = max(0, min(200, target.credit_score + payload.score_delta))
        db.add(
            CreditEvent(
                user_id=target.id,
                event_type="admin_adjustment",
                score_delta=payload.score_delta,
                reason=payload.resolution,
                operator_id=admin.id,
            )
        )

    report.status = "resolved"
    report.resolution = payload.resolution
    report.handler_id = admin.id
    report.handled_at = now_utc()
    write_log(
        db,
        admin,
        "report_resolve",
        "report",
        report.id,
        f"处理举报 #{report.id}（{report.target_type} #{report.target_id}）",
        payload.resolution,
    )
    db.commit()
    db.refresh(report)
    return admin_report_out(report, db)


@router.get("/users", response_model=AdminUserPage)
def admin_users(
    q: str | None = None,
    status: str = Query(default="all", pattern="^(all|active|disabled)$"),
    verification_status: str = Query(default="all", pattern="^(all|unverified|pending|verified|rejected)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    stmt = select(User)
    if q:
        term = q.strip()
        conditions = [User.name.ilike(f"%{term}%"), User.username.ilike(f"%{term}%")]
        if term.isdigit():
            conditions.append(User.id == int(term))
        stmt = stmt.where(or_(*conditions))
    if status != "all":
        stmt = stmt.where(User.status == status)
    if verification_status != "all":
        stmt = stmt.where(User.verification_status == verification_status)
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    items = list(
        db.scalars(stmt.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size))
    )
    return AdminUserPage(
        items=[admin_user_out(item, db) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/users/{user_id}", response_model=AdminUserDetailOut)
def admin_user_detail(user_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    listings = list(
        db.scalars(
            select(Listing)
            .options(selectinload(Listing.owner), selectinload(Listing.category), selectinload(Listing.images))
            .where(Listing.owner_id == user.id)
            .order_by(Listing.created_at.desc())
            .limit(10)
        )
    )
    credit_events = list(
        db.scalars(
            select(CreditEvent)
            .where(CreditEvent.user_id == user.id)
            .order_by(CreditEvent.created_at.desc())
            .limit(20)
        )
    )
    return AdminUserDetailOut(
        **admin_user_out(user, db).model_dump(),
        reports_filed=count_rows(db, Report, Report.reporter_id == user.id),
        reports_against=count_rows(db, Report, Report.target_type == "user", Report.target_id == user.id),
        transactions_total=count_rows(
            db,
            Transaction,
            or_(Transaction.initiator_id == user.id, Transaction.provider_id == user.id),
        ),
        listings=[listing_out(item) for item in listings],
        credit_events=credit_events,
    )


@router.post("/users/{user_id}/disable", response_model=AdminUserOut)
def disable_user(
    user_id: int,
    payload: AdminUserDisableInput,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="不能禁用当前管理员账号")
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="不能在这里禁用管理员账号")
    if user.status == "disabled":
        raise HTTPException(status_code=409, detail="该用户已经被禁用")

    user.status = "disabled"
    user.status_reason = payload.reason
    user.status_updated_at = now_utc()
    offline_count = 0
    if payload.offline_listings:
        for listing in db.scalars(select(Listing).where(Listing.owner_id == user.id, Listing.status == "published")):
            listing.status = "offline"
            listing.status_reason = "发布者账号被禁用"
            listing.is_featured = False
            listing.featured_at = None
            listing.featured_by = None
            listing.featured_reason = None
            listing.moderated_at = now_utc()
            listing.moderated_by = admin.id
            offline_count += 1
    write_log(
        db,
        admin,
        "user_disable",
        "user",
        user.id,
        f"禁用用户 {user.name}" + (f"，同时下架 {offline_count} 条发布" if offline_count else ""),
        payload.reason,
    )
    db.commit()
    db.refresh(user)
    return admin_user_out(user, db)


@router.post("/users/{user_id}/enable", response_model=AdminUserOut)
def enable_user(
    user_id: int,
    payload: AdminUserEnableInput,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.status == "active":
        raise HTTPException(status_code=409, detail="该用户已经是正常状态")
    user.status = "active"
    user.status_reason = payload.reason
    user.status_updated_at = now_utc()
    write_log(db, admin, "user_enable", "user", user.id, f"恢复用户 {user.name}", payload.reason)
    db.commit()
    db.refresh(user)
    return admin_user_out(user, db)


@router.get("/categories", response_model=list[AdminCategoryOut])
def admin_categories(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    items = db.scalars(select(Category).order_by(Category.sort_order, Category.id))
    return [admin_category_out(item, db) for item in items]


@router.post("/categories", response_model=AdminCategoryOut)
def create_category(
    payload: AdminCategoryInput,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    duplicate = db.scalar(select(Category).where(func.lower(Category.name) == payload.name.strip().lower()))
    if duplicate:
        raise HTTPException(status_code=409, detail="分类名称已存在")
    item = Category(
        name=payload.name.strip(),
        listing_type=payload.listing_type,
        is_active=payload.is_active,
        sort_order=payload.sort_order,
    )
    db.add(item)
    db.flush()
    write_log(db, admin, "category_create", "category", item.id, f"新增分类「{item.name}」")
    db.commit()
    db.refresh(item)
    return admin_category_out(item, db)


@router.patch("/categories/{category_id}", response_model=AdminCategoryOut)
def update_category(
    category_id: int,
    payload: AdminCategoryUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    item = db.get(Category, category_id)
    if not item:
        raise HTTPException(status_code=404, detail="分类不存在")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="没有需要修改的内容")
    if "name" in changes:
        name = changes["name"].strip()
        duplicate = db.scalar(
            select(Category).where(func.lower(Category.name) == name.lower(), Category.id != item.id)
        )
        if duplicate:
            raise HTTPException(status_code=409, detail="分类名称已存在")
        changes["name"] = name
    if "listing_type" in changes and changes["listing_type"] != item.listing_type:
        if count_rows(db, Listing, Listing.category_id == item.id, Listing.status != "deleted"):
            raise HTTPException(status_code=409, detail="分类下已有帖子，不能修改适用类型")
    for key, value in changes.items():
        setattr(item, key, value)
    write_log(
        db,
        admin,
        "category_update",
        "category",
        item.id,
        f"更新分类「{item.name}」",
        ", ".join(f"{key}={value}" for key, value in changes.items()),
    )
    db.commit()
    db.refresh(item)
    return admin_category_out(item, db)


@router.get("/logs", response_model=AdminLogPage)
def admin_logs(
    action: str | None = None,
    target_type: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    stmt = select(AdminActionLog).options(selectinload(AdminActionLog.admin))
    if action:
        stmt = stmt.where(AdminActionLog.action == action)
    if target_type:
        stmt = stmt.where(AdminActionLog.target_type == target_type)
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    items = list(
        db.scalars(
            stmt.order_by(AdminActionLog.created_at.desc(), AdminActionLog.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return AdminLogPage(
        items=[
            AdminActionLogOut(
                id=item.id,
                admin_name=item.admin.name if item.admin else "已注销管理员",
                action=item.action,
                target_type=item.target_type,
                target_id=item.target_id,
                summary=item.summary,
                created_at=item.created_at,
            )
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
