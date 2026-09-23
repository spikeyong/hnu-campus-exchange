from fastapi import APIRouter

from app.api.v1 import admin, auth, community, listings, transactions

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["认证"])
router.include_router(listings.router, prefix="/listings", tags=["发布信息"])
router.include_router(community.router, tags=["社区治理"])
router.include_router(transactions.router, prefix="/transactions", tags=["交易"])
router.include_router(admin.router, prefix="/admin", tags=["管理端"])
