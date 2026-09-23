from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db import get_db
from app.models import CreditEvent, Listing, Report, Transaction, User
from app.schemas import CreditEventOut, ReportCreate, ReportOut

router = APIRouter()


@router.post("/reports", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def create_report(payload: ReportCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.target_type == "user" and not db.get(User, payload.target_id):
        raise HTTPException(status_code=404, detail="被举报用户不存在")
    if payload.target_type == "listing" and not db.get(Listing, payload.target_id):
        raise HTTPException(status_code=404, detail="被举报内容不存在")
    if payload.transaction_id:
        transaction = db.get(Transaction, payload.transaction_id)
        if not transaction:
            raise HTTPException(status_code=404, detail="关联交易不存在")
        if user.id not in (transaction.initiator_id, transaction.provider_id):
            raise HTTPException(status_code=403, detail="只有交易参与者可以举报该交易")
    report = Report(reporter_id=user.id, **payload.model_dump())
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get("/credit/me", response_model=list[CreditEventOut])
def my_credit_events(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(db.scalars(select(CreditEvent).where(CreditEvent.user_id == user.id).order_by(CreditEvent.created_at.desc())))
