from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str | None] = mapped_column(String(80), unique=True, index=True, nullable=True)
    phone_hash: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    phone_ciphertext: Mapped[str | None] = mapped_column(String(512), nullable=True)
    phone_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    phone_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    email_hash: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    email_ciphertext: Mapped[str | None] = mapped_column(String(512), nullable=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(80))
    student_no: Mapped[str | None] = mapped_column(String(512), nullable=True)
    student_no_hash: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    college: Mapped[str | None] = mapped_column(String(120), nullable=True)
    grade: Mapped[str | None] = mapped_column(String(30), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="student")
    verification_status: Mapped[str] = mapped_column(String(20), default="unverified")
    verification_method: Mapped[str] = mapped_column(String(20), default="none")
    credit_score: Mapped[int] = mapped_column(Integer, default=100)
    status: Mapped[str] = mapped_column(String(20), default="active")
    status_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    listings: Mapped[list["Listing"]] = relationship(back_populates="owner", foreign_keys="Listing.owner_id")

    @property
    def student_no_masked(self) -> str | None:
        from app.core.security import decrypt_sensitive

        student_no = decrypt_sensitive(self.student_no)
        if not student_no:
            return None
        return f"{'*' * max(0, len(student_no) - 4)}{student_no[-4:]}"

    @property
    def account_masked(self) -> str:
        if self.phone_last4:
            return f"*******{self.phone_last4}"
        return self.username or "未设置账号"

    @property
    def phone_verified(self) -> bool:
        return self.phone_verified_at is not None

    @property
    def email_verified(self) -> bool:
        return self.email_verified_at is not None

    @property
    def email_masked(self) -> str | None:
        from app.core.security import decrypt_sensitive

        email = decrypt_sensitive(self.email_ciphertext)
        if not email or "@" not in email:
            return None
        local, domain = email.split("@", 1)
        visible = local[0] if len(local) <= 2 else f"{local[0]}***{local[-1]}"
        return f"{visible}***@{domain}" if len(local) <= 2 else f"{visible}@{domain}"

    @property
    def demo_features_enabled(self) -> bool:
        from app.core.config import settings

        return settings.demo_features_enabled


class SmsCode(Base):
    __tablename__ = "sms_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone_hash: Mapped[str] = mapped_column(String(64), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    purpose: Mapped[str] = mapped_column(String(30), default="register")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    sent_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class EmailCode(Base):
    __tablename__ = "email_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    email_hash: Mapped[str] = mapped_column(String(64), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    sent_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class StudentVerification(Base):
    __tablename__ = "student_verifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    challenge_code: Mapped[str] = mapped_column(String(20))
    evidence_storage_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    review_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship(foreign_keys=[user_id])
    reviewer: Mapped[User | None] = relationship(foreign_keys=[reviewer_id])


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    listing_type: Mapped[str] = mapped_column(String(20), default="both")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    type: Mapped[str] = mapped_column(String(20), index=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    price_unit: Mapped[str] = mapped_column(String(20), default="元")
    location: Mapped[str | None] = mapped_column(String(160), nullable=True)
    service_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    available_time: Mapped[str | None] = mapped_column(String(160), nullable=True)
    condition_level: Mapped[str | None] = mapped_column(String(40), nullable=True)
    expected_exchange: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="published", index=True)
    status_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    featured_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    featured_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    featured_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    moderated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    owner: Mapped[User] = relationship(back_populates="listings", foreign_keys=[owner_id])
    category: Mapped[Category] = relationship()
    images: Mapped[list["ListingImage"]] = relationship(back_populates="listing", cascade="all, delete-orphan", order_by="ListingImage.sort_order")


class ListingImage(Base):
    __tablename__ = "listing_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), index=True)
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    listing: Mapped[Listing] = relationship(back_populates="images")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), index=True)
    initiator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    proposed_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    agreed_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    proposed_time: Mapped[str | None] = mapped_column(String(120), nullable=True)
    proposed_location: Mapped[str | None] = mapped_column(String(160), nullable=True)
    request_note: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="pending_provider", index=True)
    initiator_agreed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    provider_agreed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    provider_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    requester_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    demo_payment_status: Mapped[str] = mapped_column(String(20), default="unpaid")
    demo_paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    agreement_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    listing: Mapped[Listing] = relationship()
    initiator: Mapped[User] = relationship(foreign_keys=[initiator_id])
    provider: Mapped[User] = relationship(foreign_keys=[provider_id])


class TransactionMessage(Base):
    __tablename__ = "transaction_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("transaction_id", "reviewer_id", name="uq_review_once"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), index=True)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reviewee_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    rating: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "listing_id", name="uq_favorite_once"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), index=True)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    target_type: Mapped[str] = mapped_column(String(30))
    target_id: Mapped[int] = mapped_column(Integer)
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)
    reason: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    handler_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    handled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CreditEvent(Base):
    __tablename__ = "credit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(40))
    score_delta: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(255))
    operator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AdminActionLog(Base):
    __tablename__ = "admin_action_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    admin_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(50), index=True)
    target_type: Mapped[str] = mapped_column(String(30), index=True)
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    summary: Mapped[str] = mapped_column(String(500))
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    admin: Mapped[User] = relationship(foreign_keys=[admin_id])
