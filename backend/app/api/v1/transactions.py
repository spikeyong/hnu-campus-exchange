import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_user
from app.db import get_db
from app.models import CreditEvent, Listing, Review, Transaction, TransactionMessage, User
from app.schemas import (
    MessageCreate,
    MessageOut,
    ReviewCreate,
    TransactionCreate,
    TransactionOut,
)

router = APIRouter()


def now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def ensure_participant(transaction: Transaction, user: User) -> None:
    if user.id not in (transaction.initiator_id, transaction.provider_id):
        raise HTTPException(status_code=403, detail="只有交易参与者可以访问此内容")


def transaction_out(item: Transaction) -> TransactionOut:
    snapshot = None
    if item.agreement_snapshot:
        try:
            snapshot = json.loads(item.agreement_snapshot)
        except json.JSONDecodeError:
            snapshot = None
    return TransactionOut(
        id=item.id,
        listing_id=item.listing_id,
        initiator_id=item.initiator_id,
        provider_id=item.provider_id,
        proposed_price=item.proposed_price,
        agreed_price=item.agreed_price,
        proposed_time=item.proposed_time,
        proposed_location=item.proposed_location,
        request_note=item.request_note,
        status=item.status,
        initiator_agreed_at=item.initiator_agreed_at,
        provider_agreed_at=item.provider_agreed_at,
        provider_completed_at=item.provider_completed_at,
        requester_completed_at=item.requester_completed_at,
        demo_payment_status=item.demo_payment_status,
        demo_paid_at=item.demo_paid_at,
        agreement_snapshot=snapshot,
        listing_title=item.listing.title if item.listing else None,
        initiator_name=item.initiator.name if item.initiator else None,
        provider_name=item.provider.name if item.provider else None,
        created_at=item.created_at,
    )


def record_completed_transaction(item: Transaction, db: Session) -> None:
    item.listing.status = "completed"
    for user_id in (item.initiator_id, item.provider_id):
        participant = db.get(User, user_id)
        participant.credit_score = min(200, participant.credit_score + 1)
        db.add(
            CreditEvent(
                user_id=user_id,
                transaction_id=item.id,
                event_type="transaction_completed",
                score_delta=1,
                reason="双方确认完成交易",
            )
        )


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(payload: TransactionCreate, listing_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    listing = db.get(Listing, listing_id)
    if not listing or listing.status != "published":
        raise HTTPException(status_code=404, detail="当前发布信息不可交易")
    if listing.owner_id == user.id:
        raise HTTPException(status_code=400, detail="不能向自己的发布发起请求")
    if user.role != "student" or user.verification_status != "verified":
        raise HTTPException(status_code=403, detail="完成学生认证后才能发起交易")
    existing = db.scalar(
        select(Transaction).where(
            Transaction.listing_id == listing_id,
            Transaction.initiator_id == user.id,
            Transaction.status.in_(("pending_provider", "pending_initiator", "agreed", "in_progress", "provider_confirmed", "requester_confirmed")),
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="你已经有一笔进行中的请求")
    item = Transaction(
        listing_id=listing.id,
        initiator_id=user.id,
        provider_id=listing.owner_id,
        **payload.model_dump(),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return transaction_out(item)


@router.get("", response_model=list[TransactionOut])
def list_transactions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.scalars(
        select(Transaction)
        .where((Transaction.initiator_id == user.id) | (Transaction.provider_id == user.id))
        .order_by(Transaction.created_at.desc())
    )
    return [transaction_out(item) for item in items]


@router.get("/{transaction_id:int}", response_model=TransactionOut)
def get_transaction(transaction_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.get(Transaction, transaction_id)
    if not item:
        raise HTTPException(status_code=404, detail="交易不存在")
    ensure_participant(item, user)
    return transaction_out(item)


@router.post("/{transaction_id:int}/accept", response_model=TransactionOut)
def accept_transaction(transaction_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.get(Transaction, transaction_id)
    if not item:
        raise HTTPException(status_code=404, detail="交易不存在")
    if item.provider_id != user.id:
        raise HTTPException(status_code=403, detail="只有发布者可以接受请求")
    if item.status != "pending_provider":
        raise HTTPException(status_code=400, detail="当前状态不能接受请求")
    item.provider_agreed_at = now()
    item.status = "pending_initiator"
    db.commit()
    db.refresh(item)
    return transaction_out(item)


@router.post("/{transaction_id:int}/reject", response_model=TransactionOut)
def reject_transaction(transaction_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.get(Transaction, transaction_id)
    if not item:
        raise HTTPException(status_code=404, detail="交易不存在")
    if item.provider_id != user.id:
        raise HTTPException(status_code=403, detail="只有发布者可以拒绝请求")
    if item.status != "pending_provider":
        raise HTTPException(status_code=400, detail="当前状态不能拒绝请求")
    item.status = "rejected"
    db.commit()
    db.refresh(item)
    return transaction_out(item)


@router.post("/{transaction_id:int}/agree", response_model=TransactionOut)
def agree_transaction(transaction_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.get(Transaction, transaction_id)
    if not item:
        raise HTTPException(status_code=404, detail="交易不存在")
    if item.initiator_id != user.id:
        raise HTTPException(status_code=403, detail="当前流程等待发起者确认")
    if item.status != "pending_initiator":
        raise HTTPException(status_code=400, detail="当前状态不能确认协议")
    if item.listing.status != "published":
        raise HTTPException(status_code=409, detail="该发布已与其他请求达成协议")
    item.initiator_agreed_at = now()
    item.agreed_price = item.proposed_price
    item.agreement_snapshot = json.dumps(
        {
            "listing_title": item.listing.title,
            "price": str(item.proposed_price),
            "price_unit": item.listing.price_unit,
            "time": item.proposed_time,
            "location": item.proposed_location,
            "note": item.request_note,
        },
        ensure_ascii=False,
    )
    item.status = "agreed"
    item.listing.status = "reserved"
    competing_items = db.scalars(
        select(Transaction).where(
            Transaction.listing_id == item.listing_id,
            Transaction.id != item.id,
            Transaction.status.in_(("pending_provider", "pending_initiator")),
        )
    )
    for competing_item in competing_items:
        competing_item.status = "rejected"
    db.commit()
    db.refresh(item)
    return transaction_out(item)


@router.post("/{transaction_id:int}/cancel", response_model=TransactionOut)
def cancel_transaction(
    transaction_id: int,
    reason: str = Query(min_length=2, max_length=255),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.get(Transaction, transaction_id)
    if not item:
        raise HTTPException(status_code=404, detail="交易不存在")
    ensure_participant(item, user)
    if item.status in ("pending_provider", "pending_initiator") and item.initiator_id != user.id:
        raise HTTPException(status_code=403, detail="协议达成前只有发起者可以取消请求")
    if item.status not in ("pending_provider", "pending_initiator", "agreed"):
        raise HTTPException(status_code=400, detail="当前状态不能取消")
    previous_status = item.status
    item.status = "cancelled"
    item.cancel_reason = reason
    if previous_status == "agreed":
        item.listing.status = "published"
    db.commit()
    db.refresh(item)
    return transaction_out(item)


@router.post("/{transaction_id:int}/provider-complete", response_model=TransactionOut)
def provider_complete(transaction_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.get(Transaction, transaction_id)
    if not item:
        raise HTTPException(status_code=404, detail="交易不存在")
    if item.provider_id != user.id:
        raise HTTPException(status_code=403, detail="只有发布者可以确认交付")
    if item.status not in ("agreed", "in_progress", "requester_confirmed"):
        raise HTTPException(status_code=400, detail="当前状态不能确认交付")
    item.provider_completed_at = now()
    item.status = "completed" if item.requester_completed_at else "provider_confirmed"
    if item.status == "completed":
        record_completed_transaction(item, db)
    db.commit()
    db.refresh(item)
    return transaction_out(item)


@router.post("/{transaction_id:int}/requester-complete", response_model=TransactionOut)
def requester_complete(transaction_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.get(Transaction, transaction_id)
    if not item:
        raise HTTPException(status_code=404, detail="交易不存在")
    if item.initiator_id != user.id:
        raise HTTPException(status_code=403, detail="只有发起者可以确认收到")
    if item.status not in ("agreed", "provider_confirmed"):
        raise HTTPException(status_code=400, detail="当前状态不能确认收到")
    item.requester_completed_at = now()
    item.status = "completed" if item.provider_completed_at else "requester_confirmed"
    if item.status == "completed":
        record_completed_transaction(item, db)
    db.commit()
    db.refresh(item)
    return transaction_out(item)


@router.post("/{transaction_id:int}/simulate-payment", response_model=TransactionOut)
def simulate_payment(transaction_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not settings.demo_features_enabled:
        raise HTTPException(status_code=403, detail="课程演示功能未启用")
    item = db.get(Transaction, transaction_id)
    if not item:
        raise HTTPException(status_code=404, detail="交易不存在")
    if item.initiator_id != user.id:
        raise HTTPException(status_code=403, detail="只有交易发起者可以记录模拟付款")
    if item.status not in ("agreed", "provider_confirmed", "requester_confirmed"):
        raise HTTPException(status_code=400, detail="协议达成后才能模拟付款")
    amount = item.agreed_price if item.agreed_price is not None else item.proposed_price
    if amount <= 0:
        raise HTTPException(status_code=400, detail="免费交易无需模拟付款")
    if item.demo_payment_status == "simulated_paid":
        raise HTTPException(status_code=409, detail="已经记录过模拟付款")
    item.demo_payment_status = "simulated_paid"
    item.demo_paid_at = now()
    db.commit()
    db.refresh(item)
    return transaction_out(item)


@router.get("/{transaction_id:int}/messages", response_model=list[MessageOut])
def list_messages(
    transaction_id: int,
    after_id: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.get(Transaction, transaction_id)
    if not item:
        raise HTTPException(status_code=404, detail="交易不存在")
    ensure_participant(item, user)
    messages = db.scalars(
        select(TransactionMessage)
        .where(TransactionMessage.transaction_id == transaction_id, TransactionMessage.id > after_id)
        .order_by(TransactionMessage.id.asc())
        .limit(100)
    )
    return [
        MessageOut(
            id=message.id,
            transaction_id=message.transaction_id,
            sender_id=message.sender_id,
            sender_name=db.get(User, message.sender_id).name,
            content=message.content,
            created_at=message.created_at,
        )
        for message in messages
    ]


@router.post("/{transaction_id:int}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def send_message(transaction_id: int, payload: MessageCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.get(Transaction, transaction_id)
    if not item:
        raise HTTPException(status_code=404, detail="交易不存在")
    ensure_participant(item, user)
    if item.status in ("completed", "cancelled", "rejected"):
        raise HTTPException(status_code=400, detail="当前交易已结束，不能发送消息")
    message = TransactionMessage(transaction_id=transaction_id, sender_id=user.id, content=payload.content.strip())
    db.add(message)
    db.commit()
    db.refresh(message)
    return MessageOut(
        id=message.id,
        transaction_id=message.transaction_id,
        sender_id=message.sender_id,
        sender_name=user.name,
        content=message.content,
        created_at=message.created_at,
    )


@router.post("/{transaction_id:int}/reviews", status_code=status.HTTP_201_CREATED)
def create_review(transaction_id: int, payload: ReviewCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.get(Transaction, transaction_id)
    if not item:
        raise HTTPException(status_code=404, detail="交易不存在")
    ensure_participant(item, user)
    if item.status != "completed":
        raise HTTPException(status_code=400, detail="交易完成后才能评价")
    reviewee_id = item.provider_id if user.id == item.initiator_id else item.initiator_id
    if db.scalar(select(Review).where(Review.transaction_id == transaction_id, Review.reviewer_id == user.id)):
        raise HTTPException(status_code=409, detail="你已经评价过这笔交易")
    db.add(Review(transaction_id=transaction_id, reviewer_id=user.id, reviewee_id=reviewee_id, **payload.model_dump()))
    db.commit()
    return {"message": "评价已提交"}
