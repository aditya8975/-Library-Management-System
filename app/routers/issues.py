import math
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.models import Book, User, IssueRecord, IssueStatusEnum, RoleEnum
from app.schemas import IssueCreate, IssueOut, ReturnBookRequest, Page
from app.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/issues", tags=["Issue & Return"])


def _calculate_fine(due_date: datetime, as_of: datetime) -> float:
    """₹FINE_PER_DAY for every day (rounded up) past the due date."""
    if as_of <= due_date:
        return 0.0
    overdue_days = math.ceil((as_of - due_date).total_seconds() / 86400)
    return round(overdue_days * settings.FINE_PER_DAY, 2)


def _sync_overdue_status(record: IssueRecord) -> IssueRecord:
    """Recompute live status/fine for a still-issued record (read-time only, not persisted)."""
    if record.status == IssueStatusEnum.issued:
        now = datetime.utcnow()
        record.fine_amount = _calculate_fine(record.due_date, now)
        if now > record.due_date:
            record.status = IssueStatusEnum.overdue
    return record


@router.post("", response_model=IssueOut, status_code=status.HTTP_201_CREATED)
def issue_book(
    payload: IssueCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Issue a book to a student.
    - Students can only issue to themselves (user_id is ignored/forced to self).
    - Admins may issue on behalf of any student via user_id.
    """
    target_user_id = current_user.id
    if current_user.role == RoleEnum.admin and payload.user_id:
        target_user_id = payload.user_id
        target_user = db.get(User, target_user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="Target user not found")

    book = db.get(Book, payload.book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.available_copies <= 0:
        raise HTTPException(status_code=400, detail="No copies of this book are currently available")

    # Prevent the same user holding the same book twice at once.
    existing = (
        db.query(IssueRecord)
        .filter(
            IssueRecord.book_id == book.id,
            IssueRecord.user_id == target_user_id,
            IssueRecord.status.in_([IssueStatusEnum.issued, IssueStatusEnum.overdue]),
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="This user already has this book issued")

    now = datetime.utcnow()
    record = IssueRecord(
        book_id=book.id,
        user_id=target_user_id,
        issue_date=now,
        due_date=now + timedelta(days=settings.ISSUE_PERIOD_DAYS),
        status=IssueStatusEnum.issued,
    )
    book.available_copies -= 1

    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.post("/return", response_model=IssueOut)
def return_book(
    payload: ReturnBookRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = (
        db.query(IssueRecord)
        .options(joinedload(IssueRecord.book), joinedload(IssueRecord.user))
        .filter(IssueRecord.id == payload.issue_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Issue record not found")

    if current_user.role != RoleEnum.admin and record.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only return your own books")

    if record.status == IssueStatusEnum.returned:
        raise HTTPException(status_code=400, detail="This book has already been returned")

    now = datetime.utcnow()
    record.return_date = now
    record.fine_amount = _calculate_fine(record.due_date, now)
    record.status = IssueStatusEnum.returned

    record.book.available_copies += 1

    db.commit()
    db.refresh(record)
    return record


@router.get("", response_model=Page[IssueOut])
def list_issues(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status_filter: Optional[IssueStatusEnum] = Query(None, alias="status"),
    user_id: Optional[int] = Query(None, description="Admin-only: filter by a specific student"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Students see only their own issue history.
    Admins see everyone's, optionally filtered by user_id.
    """
    query = db.query(IssueRecord).options(
        joinedload(IssueRecord.book), joinedload(IssueRecord.user)
    )

    if current_user.role == RoleEnum.admin:
        if user_id:
            query = query.filter(IssueRecord.user_id == user_id)
    else:
        query = query.filter(IssueRecord.user_id == current_user.id)

    if status_filter:
        query = query.filter(IssueRecord.status == status_filter)

    total = query.count()
    records = (
        query.order_by(IssueRecord.issue_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [_sync_overdue_status(r) for r in records]

    return Page(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)),
    )


@router.get("/{issue_id}", response_model=IssueOut)
def get_issue(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = (
        db.query(IssueRecord)
        .options(joinedload(IssueRecord.book), joinedload(IssueRecord.user))
        .filter(IssueRecord.id == issue_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Issue record not found")
    if current_user.role != RoleEnum.admin and record.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only view your own issue records")
    return _sync_overdue_status(record)


@router.post("/{issue_id}/pay-fine", response_model=IssueOut)
def pay_fine(
    issue_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)
):
    """Admin-only: mark an outstanding fine as paid (e.g. after a desk payment)."""
    record = db.get(IssueRecord, issue_id)
    if not record:
        raise HTTPException(status_code=404, detail="Issue record not found")
    if record.fine_amount <= 0:
        raise HTTPException(status_code=400, detail="This record has no outstanding fine")

    record.fine_paid = True
    db.commit()
    db.refresh(record)
    return record
