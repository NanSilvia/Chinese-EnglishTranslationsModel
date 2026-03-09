"""
Card and Folder CRUD routes - all require authentication.
Server-authoritative: the backend is the source of truth.
"""

from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .db_models import User, Card, Folder
from .auth import get_current_user

router = APIRouter(tags=["cards"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CardCreate(BaseModel):
    title: Optional[str] = None
    text_zh: str = Field(..., min_length=1)
    folder_id: Optional[int] = None
    source: str = Field(default="manual", max_length=50)


class CardUpdate(BaseModel):
    title: Optional[str] = None
    text_zh: Optional[str] = None
    folder_id: Optional[int] = None
    source: Optional[str] = None


class CardOut(BaseModel):
    id: int
    title: Optional[str]
    text_zh: str
    folder_id: Optional[int]
    source: str
    created_at: str
    updated_at: Optional[str]

    @classmethod
    def from_orm_card(cls, card: Card) -> "CardOut":
        return cls(
            id=card.id,
            title=card.title,
            text_zh=card.text_zh,
            folder_id=card.folder_id,
            source=card.source,
            created_at=card.created_at.isoformat() if card.created_at else "",
            updated_at=card.updated_at.isoformat() if card.updated_at else None,
        )


class CardListResponse(BaseModel):
    cards: List[CardOut]
    total: int
    page: int
    page_size: int


class FolderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class FolderUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class FolderOut(BaseModel):
    id: int
    name: str
    created_at: str

    @classmethod
    def from_orm_folder(cls, folder: Folder) -> "FolderOut":
        return cls(
            id=folder.id,
            name=folder.name,
            created_at=folder.created_at.isoformat() if folder.created_at else "",
        )


class SyncCardItem(BaseModel):
    """A card from the client for bulk sync."""

    local_id: Optional[int] = None
    server_id: Optional[int] = None
    title: Optional[str] = None
    text_zh: str
    folder_name: Optional[str] = None
    source: str = "manual"
    created_at: Optional[str] = None


class SyncRequest(BaseModel):
    cards: List[SyncCardItem]
    folders: List[str] = Field(default_factory=list)


class SyncResponse(BaseModel):
    cards: List[CardOut]
    folders: List[FolderOut]


# ---------------------------------------------------------------------------
# Card endpoints
# ---------------------------------------------------------------------------


@router.get("/cards", response_model=CardListResponse)
async def list_cards(
    folder_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the authenticated user's cards, optionally filtered by folder."""
    query = select(Card).where(Card.user_id == user.id)
    count_query = select(func.count(Card.id)).where(Card.user_id == user.id)

    if folder_id is not None:
        query = query.where(Card.folder_id == folder_id)
        count_query = count_query.where(Card.folder_id == folder_id)

    query = query.order_by(Card.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    result = await db.execute(query)
    cards = result.scalars().all()

    return CardListResponse(
        cards=[CardOut.from_orm_card(c) for c in cards],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/cards/{card_id}", response_model=CardOut)
async def get_card(
    card_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single card by ID (must belong to the authenticated user)."""
    result = await db.execute(
        select(Card).where(Card.id == card_id, Card.user_id == user.id)
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return CardOut.from_orm_card(card)


@router.post("/cards", response_model=CardOut, status_code=201)
async def create_card(
    body: CardCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new card for the authenticated user."""
    # Validate folder belongs to user if provided
    if body.folder_id is not None:
        folder_res = await db.execute(
            select(Folder).where(Folder.id == body.folder_id, Folder.user_id == user.id)
        )
        if not folder_res.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Folder not found")

    card = Card(
        user_id=user.id,
        title=body.title,
        text_zh=body.text_zh,
        folder_id=body.folder_id,
        source=body.source,
    )
    db.add(card)
    await db.flush()
    return CardOut.from_orm_card(card)


@router.put("/cards/{card_id}", response_model=CardOut)
async def update_card(
    card_id: int,
    body: CardUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing card."""
    result = await db.execute(
        select(Card).where(Card.id == card_id, Card.user_id == user.id)
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    if body.text_zh is not None:
        card.text_zh = body.text_zh
    if body.title is not None:
        card.title = body.title
    if body.folder_id is not None:
        # Validate folder belongs to user
        folder_res = await db.execute(
            select(Folder).where(Folder.id == body.folder_id, Folder.user_id == user.id)
        )
        if not folder_res.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Folder not found")
        card.folder_id = body.folder_id
    if body.source is not None:
        card.source = body.source

    card.updated_at = datetime.now(timezone.utc)
    db.add(card)
    await db.flush()
    return CardOut.from_orm_card(card)


@router.delete("/cards/{card_id}", status_code=204)
async def delete_card(
    card_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a card."""
    result = await db.execute(
        select(Card).where(Card.id == card_id, Card.user_id == user.id)
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    await db.delete(card)
    return None


# ---------------------------------------------------------------------------
# Folder endpoints
# ---------------------------------------------------------------------------


@router.get("/folders", response_model=List[FolderOut])
async def list_folders(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the authenticated user's folders."""
    result = await db.execute(
        select(Folder).where(Folder.user_id == user.id).order_by(Folder.name)
    )
    folders = result.scalars().all()
    return [FolderOut.from_orm_folder(f) for f in folders]


@router.get("/folders/{folder_id}", response_model=FolderOut)
async def get_folder(
    folder_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single folder."""
    result = await db.execute(
        select(Folder).where(Folder.id == folder_id, Folder.user_id == user.id)
    )
    folder = result.scalar_one_or_none()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    return FolderOut.from_orm_folder(folder)


@router.post("/folders", response_model=FolderOut, status_code=201)
async def create_folder(
    body: FolderCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new folder."""
    # Check uniqueness per user
    existing = await db.execute(
        select(Folder).where(Folder.user_id == user.id, Folder.name == body.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Folder name already exists")

    folder = Folder(user_id=user.id, name=body.name)
    db.add(folder)
    await db.flush()
    return FolderOut.from_orm_folder(folder)


@router.put("/folders/{folder_id}", response_model=FolderOut)
async def update_folder(
    folder_id: int,
    body: FolderUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rename a folder."""
    result = await db.execute(
        select(Folder).where(Folder.id == folder_id, Folder.user_id == user.id)
    )
    folder = result.scalar_one_or_none()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    folder.name = body.name
    db.add(folder)
    await db.flush()
    return FolderOut.from_orm_folder(folder)


@router.delete("/folders/{folder_id}", status_code=204)
async def delete_folder(
    folder_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a folder. Cards in the folder get their folder_id set to NULL."""
    result = await db.execute(
        select(Folder).where(Folder.id == folder_id, Folder.user_id == user.id)
    )
    folder = result.scalar_one_or_none()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    # Nullify folder_id on cards
    from sqlalchemy import update

    await db.execute(
        update(Card)
        .where(Card.folder_id == folder_id, Card.user_id == user.id)
        .values(folder_id=None)
    )

    await db.delete(folder)
    return None


# ---------------------------------------------------------------------------
# Sync endpoint - server-authoritative
# ---------------------------------------------------------------------------


@router.post("/cards/sync", response_model=SyncResponse)
async def sync_cards(
    body: SyncRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk sync: client sends its local cards/folders, server merges them
    and returns the authoritative full state.

    - Cards with a `server_id` are treated as updates (if they exist).
    - Cards without a `server_id` are created as new.
    - Folders are created if they don't already exist.
    """
    # --- Resolve folders ---
    folder_map: dict[str, int] = {}  # name → id
    existing_folders = await db.execute(select(Folder).where(Folder.user_id == user.id))
    for f in existing_folders.scalars():
        folder_map[f.name] = f.id

    for name in body.folders:
        if name not in folder_map:
            new_folder = Folder(user_id=user.id, name=name)
            db.add(new_folder)
            await db.flush()
            folder_map[name] = new_folder.id

    # --- Resolve cards ---
    for item in body.cards:
        folder_id = folder_map.get(item.folder_name) if item.folder_name else None

        if item.server_id:
            # Try to update existing
            res = await db.execute(
                select(Card).where(Card.id == item.server_id, Card.user_id == user.id)
            )
            card = res.scalar_one_or_none()
            if card:
                card.title = item.title
                card.text_zh = item.text_zh
                card.folder_id = folder_id
                card.source = item.source
                card.updated_at = datetime.now(timezone.utc)
                db.add(card)
                continue

        # Create new card
        new_card = Card(
            user_id=user.id,
            title=item.title,
            text_zh=item.text_zh,
            folder_id=folder_id,
            source=item.source,
        )
        if item.created_at:
            try:
                new_card.created_at = datetime.fromisoformat(item.created_at)
            except ValueError:
                pass
        db.add(new_card)

    await db.flush()

    # Return full server state
    all_cards = await db.execute(
        select(Card).where(Card.user_id == user.id).order_by(Card.created_at.desc())
    )
    all_folders = await db.execute(
        select(Folder).where(Folder.user_id == user.id).order_by(Folder.name)
    )

    return SyncResponse(
        cards=[CardOut.from_orm_card(c) for c in all_cards.scalars()],
        folders=[FolderOut.from_orm_folder(f) for f in all_folders.scalars()],
    )
