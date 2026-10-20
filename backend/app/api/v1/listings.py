from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_user
from app.db import get_db
from app.models import Category, Favorite, Listing, ListingImage, User
from app.schemas import CategoryOut, ListingCreate, ListingOut, ListingPage, ListingStatusInput

router = APIRouter()


def listing_out(item: Listing) -> ListingOut:
    return ListingOut(
        id=item.id,
        owner_id=item.owner_id,
        category_id=item.category_id,
        type=item.type,
        title=item.title,
        description=item.description,
        price=item.price,
        price_unit=item.price_unit,
        location=item.location,
        service_mode=item.service_mode,
        available_time=item.available_time,
        condition_level=item.condition_level,
        expected_exchange=item.expected_exchange,
        status=item.status,
        is_featured=item.is_featured,
        featured_at=item.featured_at,
        created_at=item.created_at,
        owner_name=item.owner.name if item.owner else None,
        owner_credit_score=item.owner.credit_score if item.owner else None,
        category_name=item.category.name if item.category else None,
        image_urls=[f"/uploads/{image.storage_key}" for image in item.images],
    )


@router.get("/categories", response_model=list[CategoryOut])
def categories(db: Session = Depends(get_db)):
    return list(db.scalars(select(Category).where(Category.is_active.is_(True)).order_by(Category.sort_order, Category.id)))


@router.get("", response_model=ListingPage)
def list_listings(
    keyword: str | None = None,
    listing_type: str | None = Query(default=None, alias="type", pattern="^(resource|skill)$"),
    category_id: int | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    stmt = select(Listing).where(Listing.status == "published")
    if keyword:
        like = f"%{keyword.strip()}%"
        stmt = stmt.where(or_(Listing.title.ilike(like), Listing.description.ilike(like), Listing.location.ilike(like)))
    if listing_type:
        stmt = stmt.where(Listing.type == listing_type)
    if category_id:
        stmt = stmt.where(Listing.category_id == category_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(db.scalars(stmt.order_by(Listing.created_at.desc()).offset((page - 1) * page_size).limit(page_size)))
    return ListingPage(items=[listing_out(item) for item in items], total=total, page=page, page_size=page_size)


@router.post("", response_model=ListingOut, status_code=status.HTTP_201_CREATED)
def create_listing(payload: ListingCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "student" or user.verification_status != "verified":
        raise HTTPException(status_code=403, detail="完成学生认证后才能发布内容")
    category = db.get(Category, payload.category_id)
    if not category or not category.is_active:
        raise HTTPException(status_code=400, detail="分类不存在或已停用")
    if category.listing_type not in ("both", payload.type):
        raise HTTPException(status_code=400, detail="该分类不适用于当前发布类型")
    item = Listing(owner_id=user.id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return listing_out(item)


@router.get("/favorites/mine", response_model=list[ListingOut])
def my_favorites(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.scalars(
        select(Listing)
        .join(Favorite, Favorite.listing_id == Listing.id)
        .where(Favorite.user_id == user.id, Listing.status != "deleted")
        .order_by(Listing.created_at.desc())
    )
    return [listing_out(item) for item in items]


@router.get("/mine", response_model=list[ListingOut])
def my_listings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.scalars(
        select(Listing)
        .where(Listing.owner_id == user.id, Listing.status != "deleted")
        .order_by(Listing.created_at.desc())
    )
    return [listing_out(item) for item in items]


@router.patch("/mine/{listing_id}/status", response_model=ListingOut)
def update_listing_status(
    listing_id: int,
    payload: ListingStatusInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.get(Listing, listing_id)
    if not item or item.owner_id != user.id:
        raise HTTPException(status_code=404, detail="发布信息不存在")
    if item.status not in ("published", "offline"):
        raise HTTPException(status_code=400, detail="当前状态不能切换上下架")
    item.status = payload.status
    db.commit()
    db.refresh(item)
    return listing_out(item)


@router.get("/{listing_id}", response_model=ListingOut)
def get_listing(listing_id: int, db: Session = Depends(get_db)):
    item = db.get(Listing, listing_id)
    if not item or item.status == "deleted":
        raise HTTPException(status_code=404, detail="发布信息不存在")
    return listing_out(item)


@router.post("/{listing_id}/images", response_model=ListingOut)
async def upload_listing_image(
    listing_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.get(Listing, listing_id)
    if not item or item.owner_id != user.id:
        raise HTTPException(status_code=404, detail="发布信息不存在")
    if len(item.images) >= 6:
        raise HTTPException(status_code=400, detail="每条发布最多上传 6 张图片")
    allowed_types = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="只允许 JPEG、PNG 或 WebP 图片")
    content = await file.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="单张图片不能超过 5 MB")
    signatures = {
        "image/jpeg": content.startswith(b"\xff\xd8\xff"),
        "image/png": content.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP",
    }
    if not signatures[file.content_type]:
        raise HTTPException(status_code=400, detail="图片内容与文件类型不匹配")
    storage_key = f"{uuid4().hex}{allowed_types[file.content_type]}"
    target = Path(settings.public_upload_dir).resolve() / storage_key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    db.add(ListingImage(listing_id=item.id, storage_key=storage_key, sort_order=len(item.images)))
    db.commit()
    db.refresh(item)
    return listing_out(item)


@router.post("/{listing_id}/favorite", status_code=status.HTTP_201_CREATED)
def add_favorite(listing_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not db.get(Listing, listing_id):
        raise HTTPException(status_code=404, detail="发布信息不存在")
    existing = db.scalar(select(Favorite).where(Favorite.user_id == user.id, Favorite.listing_id == listing_id))
    if not existing:
        db.add(Favorite(user_id=user.id, listing_id=listing_id))
        db.commit()
    return {"message": "已收藏"}


@router.delete("/{listing_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite(listing_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    favorite = db.scalar(select(Favorite).where(Favorite.user_id == user.id, Favorite.listing_id == listing_id))
    if favorite:
        db.delete(favorite)
        db.commit()


@router.patch("/{listing_id}", response_model=ListingOut)
def update_listing(listing_id: int, payload: ListingCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.get(Listing, listing_id)
    if not item or item.owner_id != user.id:
        raise HTTPException(status_code=404, detail="发布信息不存在")
    if item.status not in ("published", "offline"):
        raise HTTPException(status_code=400, detail="当前状态不能编辑")
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return listing_out(item)


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_listing(listing_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.get(Listing, listing_id)
    if not item or item.owner_id != user.id:
        raise HTTPException(status_code=404, detail="发布信息不存在")
    item.status = "deleted"
    db.commit()
