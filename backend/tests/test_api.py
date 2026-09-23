from collections.abc import Generator
import os
import shutil
import tempfile

os.environ["DATABASE_URL"] = "sqlite://"
TEST_UPLOAD_DIR = tempfile.mkdtemp(prefix="campus-exchange-tests-")
os.environ["UPLOAD_DIR"] = TEST_UPLOAD_DIR

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db import Base, get_db
from app.main import app
from app.models import Category, User


PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"test-image-content"


@pytest.fixture(scope="session", autouse=True)
def cleanup_uploads():
    yield
    shutil.rmtree(TEST_UPLOAD_DIR, ignore_errors=True)


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    with session_factory() as db:
        db.add_all(
            [
                Category(name="生活用品", listing_type="resource"),
                Category(name="技能辅导", listing_type="skill"),
                User(
                    username="admin",
                    password_hash=hash_password("Admin123!"),
                    name="管理员",
                    role="admin",
                    verification_status="verified",
                ),
            ]
        )
        db.commit()

    def override_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


def auth_headers(client: TestClient, identifier: str, password: str = "Student123!") -> dict[str, str]:
    if identifier == "admin":
        response = client.post("/api/v1/auth/login", json={"identifier": identifier, "password": password})
    else:
        sms = client.post("/api/v1/auth/sms/send", json={"phone": identifier, "purpose": "login"})
        assert sms.status_code == 200, sms.text
        response = client.post("/api/v1/auth/sms/login", json={"phone": identifier, "sms_code": sms.json()["debug_code"]})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def register_phone(client: TestClient, phone: str, name: str) -> dict:
    sms = client.post("/api/v1/auth/sms/send", json={"phone": phone, "purpose": "register"})
    assert sms.status_code == 200, sms.text
    response = client.post(
        "/api/v1/auth/register",
        json={
            "phone": phone,
            "sms_code": sms.json()["debug_code"],
            "name": name,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def submit_verification(client: TestClient, headers: dict[str, str], student_no: str, college: str = "信息科学技术学院") -> int:
    challenge = client.post("/api/v1/auth/verification/challenge", headers=headers)
    assert challenge.status_code == 200, challenge.text
    response = client.post(
        "/api/v1/auth/verification/submit",
        headers=headers,
        data={
            "challenge_id": challenge.json()["id"],
            "student_no": student_no,
            "college": college,
            "grade": "2024级",
        },
        files={"evidence": ("evidence.png", PNG_BYTES, "image/png")},
    )
    assert response.status_code == 200, response.text
    return challenge.json()["id"]


def approve_verification(client: TestClient, admin_headers: dict[str, str], verification_id: int) -> dict:
    response = client.post(f"/api/v1/admin/verifications/{verification_id}/approve", headers=admin_headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_phone_registration_and_manual_verification(client: TestClient):
    assert client.get("/health").json()["status"] == "ok"
    registered = register_phone(client, "13800000001", "小海")
    assert registered["user"]["account_masked"] == "*******0001"
    assert registered["user"]["phone_verified"] is True
    assert registered["user"]["verification_status"] == "unverified"
    assert registered["user"]["student_no_masked"] is None
    assert "email" not in registered["user"]

    email_contract = client.post(
        "/api/v1/auth/register",
        json={"email": "student@hainanu.edu.cn", "name": "旧表单"},
    )
    assert email_contract.status_code == 422

    sms = client.post("/api/v1/auth/sms/send", json={"phone": "13800000001", "purpose": "login"}).json()
    wrong_code = "000001" if sms["debug_code"] != "000001" else "000002"
    assert client.post("/api/v1/auth/sms/login", json={"phone": "13800000001", "sms_code": wrong_code}).status_code == 400
    assert client.post("/api/v1/auth/login", json={"identifier": "13800000001", "password": "Student123!"}).status_code == 401
    sms_login = client.post("/api/v1/auth/sms/login", json={"phone": "13800000001", "sms_code": sms["debug_code"]})
    assert sms_login.status_code == 200
    assert client.post("/api/v1/auth/sms/login", json={"phone": "13800000001", "sms_code": sms["debug_code"]}).status_code == 400
    headers = {"Authorization": f"Bearer {sms_login.json()['access_token']}"}
    email_code = client.post(
        "/api/v1/auth/email/send",
        headers=headers,
        json={"email": "student@example.com"},
    )
    assert email_code.status_code == 200, email_code.text
    bound = client.post(
        "/api/v1/auth/email/bind",
        headers=headers,
        json={"email": "STUDENT@example.com", "code": email_code.json()["debug_code"]},
    )
    assert bound.status_code == 200, bound.text
    assert bound.json()["email_verified"] is True
    assert bound.json()["email_masked"] == "s***t@example.com"
    assert bound.json()["verification_status"] == "unverified"
    blocked_listing = client.post(
        "/api/v1/listings",
        headers=headers,
        json={"type": "resource", "category_id": 1, "title": "未认证发布", "description": "应该被阻止", "price": 10},
    )
    assert blocked_listing.status_code == 403

    verification_id = submit_verification(client, headers, "202412345678")
    admin_headers = auth_headers(client, "admin", "Admin123!")
    assert client.post(
        "/api/v1/listings",
        headers=admin_headers,
        json={"type": "resource", "category_id": 1, "title": "管理员发布", "description": "管理员不得参与学生交易", "price": 10},
    ).status_code == 403
    pending = client.get("/api/v1/admin/verifications", headers=admin_headers)
    assert pending.status_code == 200
    assert pending.json()[0]["id"] == verification_id
    assert pending.json()[0]["user_name"] == "小海"
    assert pending.json()[0]["phone_masked"] == "*******0001"
    assert pending.json()[0]["student_no_masked"] == "********5678"
    assert pending.json()[0]["evidence_url"]

    approved = approve_verification(client, admin_headers, verification_id)
    assert approved["status"] == "approved"
    assert approved["evidence_url"] is None
    assert client.get(f"/api/v1/admin/verifications/{verification_id}/evidence", headers=admin_headers).status_code == 404
    me = client.get("/api/v1/auth/me", headers=headers).json()
    assert me["verification_status"] == "verified"
    assert me["student_no_masked"] == "********5678"


def test_course_demo_verification_is_explicit(client: TestClient):
    registered = register_phone(client, "13800000002", "演示学生")
    headers = {"Authorization": f"Bearer {registered['access_token']}"}
    response = client.post(
        "/api/v1/auth/verification/demo",
        headers=headers,
        json={"student_no": "DEMO 20240002", "college": "计算机科学与技术学院", "grade": "2024级"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["verification_status"] == "verified"
    assert response.json()["verification_method"] == "demo"
    assert response.json()["student_no_masked"].endswith("0002")


def test_duplicate_student_number_is_rejected(client: TestClient):
    first = register_phone(client, "13800000003", "第一位学生")
    second = register_phone(client, "13800000004", "第二位学生")
    first_headers = {"Authorization": f"Bearer {first['access_token']}"}
    second_headers = {"Authorization": f"Bearer {second['access_token']}"}
    submit_verification(client, first_headers, "202400001111")
    duplicate_challenge = client.post("/api/v1/auth/verification/challenge", headers=second_headers).json()
    duplicate = client.post(
        "/api/v1/auth/verification/submit",
        headers=second_headers,
        data={"challenge_id": duplicate_challenge["id"], "student_no": "2024 0000 1111", "college": "经济学院", "grade": "2024级"},
        files={"evidence": ("evidence.png", PNG_BYTES, "image/png")},
    )
    assert duplicate.status_code == 409


def test_verified_students_can_complete_two_party_transaction(client: TestClient):
    accounts = [
        ("13800000011", "发布者", "202400000011"),
        ("13800000012", "需求者", "202400000012"),
        ("13800000013", "无关用户", "202400000013"),
    ]
    admin_headers = auth_headers(client, "admin", "Admin123!")
    account_headers = {}
    for phone, name, student_no in accounts:
        registered = register_phone(client, phone, name)
        student_headers = {"Authorization": f"Bearer {registered['access_token']}"}
        account_headers[phone] = student_headers
        verification_id = submit_verification(client, student_headers, student_no)
        approve_verification(client, admin_headers, verification_id)

    seller_headers = account_headers[accounts[0][0]]
    buyer_headers = account_headers[accounts[1][0]]
    outsider_headers = account_headers[accounts[2][0]]
    listing = client.post(
        "/api/v1/listings",
        headers=seller_headers,
        json={"type": "resource", "category_id": 1, "title": "高数教材", "description": "九成新教材", "price": 20},
    )
    assert listing.status_code == 201
    listing_id = listing.json()["id"]
    assert client.get("/api/v1/listings/mine", headers=seller_headers).json()[0]["id"] == listing_id
    assert client.patch(
        f"/api/v1/listings/mine/{listing_id}/status",
        headers=seller_headers,
        json={"status": "offline"},
    ).json()["status"] == "offline"
    assert client.patch(
        f"/api/v1/listings/mine/{listing_id}/status",
        headers=seller_headers,
        json={"status": "published"},
    ).json()["status"] == "published"
    assert client.post(f"/api/v1/listings/{listing_id}/favorite", headers=buyer_headers).status_code == 201
    assert client.get("/api/v1/listings/favorites/mine", headers=buyer_headers).json()[0]["id"] == listing_id
    invalid_image = client.post(
        f"/api/v1/listings/{listing_id}/images",
        headers=seller_headers,
        files={"file": ("unsafe.txt", b"not an image", "text/plain")},
    )
    assert invalid_image.status_code == 400
    spoofed_image = client.post(
        f"/api/v1/listings/{listing_id}/images",
        headers=seller_headers,
        files={"file": ("fake.png", b"not really a png", "image/png")},
    )
    assert spoofed_image.status_code == 400

    transaction = client.post(
        f"/api/v1/transactions?listing_id={listing_id}",
        headers=buyer_headers,
        json={"proposed_price": 18, "proposed_time": "周六下午", "proposed_location": "图书馆", "request_note": "希望交换教材"},
    )
    assert transaction.status_code == 201
    transaction_id = transaction.json()["id"]
    competing = client.post(
        f"/api/v1/transactions?listing_id={listing_id}",
        headers=outsider_headers,
        json={"proposed_price": 19, "proposed_time": "周日下午", "proposed_location": "教学楼", "request_note": "另一个请求"},
    )
    assert competing.status_code == 201
    competing_id = competing.json()["id"]
    assert client.post(
        f"/api/v1/transactions/{transaction_id}/cancel",
        params={"reason": "发布者不能替发起者取消"},
        headers=seller_headers,
    ).status_code == 403
    assert client.get(f"/api/v1/transactions/{transaction_id}", headers=outsider_headers).status_code == 403
    assert client.post(
        f"/api/v1/transactions/{transaction_id}/reviews",
        headers=buyer_headers,
        json={"rating": 5, "content": "过早评价"},
    ).status_code == 400

    message = client.post(
        f"/api/v1/transactions/{transaction_id}/messages",
        headers=buyer_headers,
        json={"content": "请确认周六下午是否方便"},
    )
    assert message.status_code == 201
    assert client.get(f"/api/v1/transactions/{transaction_id}/messages", headers=seller_headers).json()[0]["content"] == "请确认周六下午是否方便"
    assert client.get(f"/api/v1/transactions/{transaction_id}/messages", headers=outsider_headers).status_code == 403
    assert client.post(f"/api/v1/transactions/{transaction_id}/accept", headers=seller_headers).json()["status"] == "pending_initiator"
    assert client.post(f"/api/v1/transactions/{competing_id}/accept", headers=seller_headers).json()["status"] == "pending_initiator"
    agreed = client.post(f"/api/v1/transactions/{transaction_id}/agree", headers=buyer_headers).json()
    assert agreed["status"] == "agreed"
    assert agreed["demo_payment_status"] == "unpaid"
    assert client.post(f"/api/v1/transactions/{transaction_id}/simulate-payment", headers=seller_headers).status_code == 403
    simulated_payment = client.post(f"/api/v1/transactions/{transaction_id}/simulate-payment", headers=buyer_headers)
    assert simulated_payment.status_code == 200, simulated_payment.text
    assert simulated_payment.json()["demo_payment_status"] == "simulated_paid"
    assert simulated_payment.json()["status"] == "agreed"
    assert client.post(f"/api/v1/transactions/{transaction_id}/simulate-payment", headers=buyer_headers).status_code == 409
    assert client.get(f"/api/v1/transactions/{competing_id}", headers=outsider_headers).json()["status"] == "rejected"
    assert client.post(f"/api/v1/transactions/{competing_id}/agree", headers=outsider_headers).status_code == 400
    assert client.post(f"/api/v1/transactions/{transaction_id}/provider-complete", headers=seller_headers).json()["status"] == "provider_confirmed"
    completed = client.post(f"/api/v1/transactions/{transaction_id}/requester-complete", headers=buyer_headers)
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert client.post(
        f"/api/v1/transactions/{transaction_id}/messages",
        headers=buyer_headers,
        json={"content": "结束后消息"},
    ).status_code == 400
    assert client.get("/api/v1/credit/me", headers=buyer_headers).json()[0]["score_delta"] == 1
    assert client.post(
        f"/api/v1/transactions/{transaction_id}/reviews",
        headers=buyer_headers,
        json={"rating": 5, "content": "顺利完成"},
    ).status_code == 201
    assert client.post(
        f"/api/v1/transactions/{transaction_id}/reviews",
        headers=buyer_headers,
        json={"rating": 5},
    ).status_code == 409

    second_listing = client.post(
        "/api/v1/listings",
        headers=seller_headers,
        json={"type": "resource", "category_id": 1, "title": "线性代数教材", "description": "用于验证反向确认顺序", "price": 16},
    ).json()
    reverse_transaction = client.post(
        f"/api/v1/transactions?listing_id={second_listing['id']}",
        headers=buyer_headers,
        json={"proposed_price": 16, "proposed_time": "周日", "proposed_location": "图书馆", "request_note": "需求方先确认收到"},
    ).json()
    reverse_id = reverse_transaction["id"]
    client.post(f"/api/v1/transactions/{reverse_id}/accept", headers=seller_headers)
    client.post(f"/api/v1/transactions/{reverse_id}/agree", headers=buyer_headers)
    requester_first = client.post(f"/api/v1/transactions/{reverse_id}/requester-complete", headers=buyer_headers)
    assert requester_first.json()["status"] == "requester_confirmed"
    assert client.post(
        f"/api/v1/transactions/{reverse_id}/cancel",
        params={"reason": "确认完成后不能取消"},
        headers=buyer_headers,
    ).status_code == 400
    assert client.post(f"/api/v1/transactions/{reverse_id}/provider-complete", headers=seller_headers).json()["status"] == "completed"

    report = client.post(
        "/api/v1/reports",
        headers=buyer_headers,
        json={
            "target_type": "user",
            "target_id": completed.json()["provider_id"],
            "transaction_id": transaction_id,
            "reason": "信息核查",
            "description": "请管理员核查交易信息",
        },
    )
    assert report.status_code == 201
    assert client.get("/api/v1/admin/reports", headers=admin_headers).status_code == 200
    assert client.post(
        f"/api/v1/admin/reports/{report.json()['id']}/resolve",
        headers=admin_headers,
        json={"resolution": "已核查，无违规", "score_delta": 0},
    ).status_code == 200
