from datetime import datetime
from decimal import Decimal
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")


def normalized_email(value: str) -> str:
    email = value.strip().lower()
    if len(email) > 255 or not EMAIL_PATTERN.fullmatch(email):
        raise ValueError("请输入有效的邮箱地址")
    return email


class UserCreate(BaseModel):
    phone: str = Field(pattern=r"^1[3-9]\d{9}$")
    sms_code: str = Field(pattern=r"^\d{6}$")
    name: str = Field(min_length=2, max_length=80)

class LoginInput(BaseModel):
    identifier: str = Field(min_length=5, max_length=255)
    password: str


class SmsLoginInput(BaseModel):
    phone: str = Field(pattern=r"^1[3-9]\d{9}$")
    sms_code: str = Field(pattern=r"^\d{6}$")


class SmsSendInput(BaseModel):
    phone: str = Field(pattern=r"^1[3-9]\d{9}$")
    purpose: str = Field(default="register", pattern="^(register|login)$")


class SmsSendOut(BaseModel):
    message: str
    expires_in: int
    retry_after: int
    debug_code: str | None = None


class EmailSendInput(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalized_email(value)


class EmailBindInput(EmailSendInput):
    code: str = Field(pattern=r"^\d{6}$")


class EmailSendOut(BaseModel):
    message: str
    expires_in: int
    retry_after: int
    debug_code: str | None = None


class DemoVerificationInput(BaseModel):
    student_no: str = Field(min_length=6, max_length=40)
    college: str = Field(min_length=2, max_length=120)
    grade: str = Field(min_length=2, max_length=30)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_masked: str
    phone_verified: bool
    email_masked: str | None
    email_verified: bool
    name: str
    student_no_masked: str | None
    college: str | None
    grade: str | None
    role: str
    verification_status: str
    verification_method: str
    credit_score: int
    demo_features_enabled: bool


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class VerificationChallengeOut(BaseModel):
    id: int
    challenge_code: str
    expires_at: datetime


class StudentVerificationOut(BaseModel):
    id: int
    user_id: int
    user_name: str
    phone_masked: str
    student_no_masked: str | None
    college: str | None
    grade: str | None
    challenge_code: str
    status: str
    evidence_url: str | None
    review_note: str | None
    reviewer_name: str | None = None
    reviewed_at: datetime | None = None
    submitted_at: datetime | None


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    listing_type: str
    is_active: bool = True
    sort_order: int = 0


class ListingCreate(BaseModel):
    type: str = Field(pattern="^(resource|skill)$")
    category_id: int
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=5, max_length=4000)
    price: Decimal = Field(ge=0, le=1000000)
    price_unit: str = Field(default="元", max_length=20)
    location: str | None = Field(default=None, max_length=160)
    service_mode: str | None = Field(default=None, pattern="^(online|offline|both)$")
    available_time: str | None = Field(default=None, max_length=160)
    condition_level: str | None = Field(default=None, max_length=40)
    expected_exchange: str | None = Field(default=None, max_length=200)


class ListingOut(ListingCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    status: str
    is_featured: bool = False
    featured_at: datetime | None = None
    created_at: datetime
    owner_name: str | None = None
    owner_credit_score: int | None = None
    category_name: str | None = None
    image_urls: list[str] = Field(default_factory=list)


class ListingPage(BaseModel):
    items: list[ListingOut]
    total: int
    page: int
    page_size: int


class TransactionCreate(BaseModel):
    proposed_price: Decimal = Field(ge=0, le=1000000)
    proposed_time: str | None = Field(default=None, max_length=120)
    proposed_location: str | None = Field(default=None, max_length=160)
    request_note: str = Field(min_length=2, max_length=1000)


class TransactionOut(BaseModel):
    id: int
    listing_id: int
    initiator_id: int
    provider_id: int
    proposed_price: Decimal
    agreed_price: Decimal | None
    proposed_time: str | None
    proposed_location: str | None
    request_note: str
    status: str
    initiator_agreed_at: datetime | None
    provider_agreed_at: datetime | None
    provider_completed_at: datetime | None
    requester_completed_at: datetime | None
    demo_payment_status: str
    demo_paid_at: datetime | None
    agreement_snapshot: dict | None
    listing_title: str | None = None
    initiator_name: str | None = None
    provider_name: str | None = None
    created_at: datetime


class ListingStatusInput(BaseModel):
    status: str = Field(pattern="^(published|offline)$")


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class MessageOut(BaseModel):
    id: int
    transaction_id: int
    sender_id: int
    sender_name: str
    content: str
    created_at: datetime


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    content: str = Field(default="", max_length=500)


class ReportCreate(BaseModel):
    target_type: str = Field(pattern="^(listing|user|transaction)$")
    target_id: int
    transaction_id: int | None = None
    reason: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=5, max_length=2000)


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reporter_id: int
    target_type: str
    target_id: int
    transaction_id: int | None
    reason: str
    description: str
    status: str
    resolution: str | None
    handled_at: datetime | None = None
    created_at: datetime


class AdminResolution(BaseModel):
    resolution: str = Field(min_length=2, max_length=1000)
    score_delta: int = Field(default=0, ge=-100, le=100)
    score_user_id: int | None = None


class CreditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    score_delta: int
    reason: str
    created_at: datetime


class AdminStatsOut(BaseModel):
    pending_verifications: int
    pending_reports: int
    users_total: int
    users_verified: int
    users_disabled: int
    listings_published: int
    listings_offline: int
    listings_featured: int
    transactions_active: int
    transactions_completed: int
    new_users_7d: int
    new_listings_7d: int


class AdminListingOut(ListingOut):
    status_reason: str | None = None
    featured_reason: str | None = None
    owner_status: str | None = None
    owner_verification_status: str | None = None
    report_count: int = 0


class AdminListingPage(BaseModel):
    items: list[AdminListingOut]
    total: int
    page: int
    page_size: int


class AdminListingStatusInput(BaseModel):
    status: str = Field(pattern="^(published|offline)$")
    reason: str = Field(min_length=2, max_length=255)


class AdminFeatureInput(BaseModel):
    reason: str = Field(min_length=2, max_length=255)


class AdminUserOut(BaseModel):
    id: int
    name: str
    account_masked: str
    phone_verified: bool
    email_masked: str | None
    role: str
    verification_status: str
    verification_method: str
    credit_score: int
    status: str
    status_reason: str | None
    created_at: datetime
    listing_count: int
    completed_transactions: int


class AdminUserDetailOut(AdminUserOut):
    reports_filed: int
    reports_against: int
    transactions_total: int
    listings: list[ListingOut] = Field(default_factory=list)
    credit_events: list[CreditEventOut] = Field(default_factory=list)


class AdminUserPage(BaseModel):
    items: list[AdminUserOut]
    total: int
    page: int
    page_size: int


class AdminUserDisableInput(BaseModel):
    reason: str = Field(min_length=2, max_length=255)
    offline_listings: bool = True


class AdminUserEnableInput(BaseModel):
    reason: str = Field(default="账号恢复使用", min_length=2, max_length=255)


class AdminCategoryOut(CategoryOut):
    listing_count: int = 0


class AdminCategoryInput(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    listing_type: str = Field(default="both", pattern="^(resource|skill|both)$")
    is_active: bool = True
    sort_order: int = Field(default=0, ge=-999, le=9999)


class AdminCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    listing_type: str | None = Field(default=None, pattern="^(resource|skill|both)$")
    is_active: bool | None = None
    sort_order: int | None = Field(default=None, ge=-999, le=9999)


class AdminReportOut(BaseModel):
    id: int
    reporter_id: int
    reporter_name: str | None
    target_type: str
    target_id: int
    target_label: str | None
    target_user_id: int | None
    transaction_id: int | None
    transaction_title: str | None
    reason: str
    description: str
    status: str
    resolution: str | None
    handler_name: str | None
    handled_at: datetime | None
    created_at: datetime


class AdminReportMessageOut(BaseModel):
    id: int
    sender_name: str
    content: str
    created_at: datetime


class AdminReportDetailOut(AdminReportOut):
    transaction_status: str | None = None
    transaction_price: Decimal | None = None
    transaction_time: str | None = None
    transaction_location: str | None = None
    messages: list[AdminReportMessageOut] = Field(default_factory=list)


class AdminActionLogOut(BaseModel):
    id: int
    admin_name: str
    action: str
    target_type: str
    target_id: int | None
    summary: str
    created_at: datetime


class AdminLogPage(BaseModel):
    items: list[AdminActionLogOut]
    total: int
    page: int
    page_size: int
