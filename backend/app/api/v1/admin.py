from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.core.config import settings
from app.db import get_db
from app.models import CreditEvent, Report, StudentVerification, User
from app.schemas import AdminResolution, ReportOut, StudentVerificationOut

router = APIRouter()


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
        submitted_at=item.submitted_at,
    )


@router.get("/verifications", response_model=list[StudentVerificationOut])
def list_verifications(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    items = db.scalars(
        select(StudentVerification)
        .where(StudentVerification.status == "pending")
        .order_by(StudentVerification.submitted_at.asc())
    )
    return [verification_out(item) for item in items]


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
    application.reviewed_at = datetime.now(UTC).replace(tzinfo=None)
    application.user.verification_status = "verified"
    application.user.verification_method = "manual"
    delete_reviewed_evidence(application)
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
    application.reviewed_at = datetime.now(UTC).replace(tzinfo=None)
    application.user.verification_status = "rejected"
    application.user.verification_method = "manual"
    application.user.student_no = None
    application.user.student_no_hash = None
    application.user.college = None
    application.user.grade = None
    delete_reviewed_evidence(application)
    db.commit()
    db.refresh(application)
    return verification_out(application)


@router.get("/reports", response_model=list[ReportOut])
def list_reports(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return list(db.scalars(select(Report).order_by(Report.created_at.desc())))


@router.post("/reports/{report_id}/resolve", response_model=ReportOut)
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
    report.status = "resolved"
    report.resolution = payload.resolution
    report.handler_id = admin.id
    if payload.score_delta:
        target = db.get(User, report.target_id) if report.target_type == "user" else None
        if target:
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
    db.commit()
    db.refresh(report)
    return report
