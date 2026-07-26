import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Book, User
from app.schemas import BookCreate, BookUpdate, BookOut, Page
from app.dependencies import require_admin, get_current_user

router = APIRouter(prefix="/books", tags=["Books"])


@router.post("", response_model=BookOut, status_code=status.HTTP_201_CREATED)
def create_book(
    book_in: BookCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)
):
    """Admin-only: add a new book to the catalog."""
    if db.query(Book).filter(Book.isbn == book_in.isbn).first():
        raise HTTPException(status_code=400, detail="A book with this ISBN already exists")

    book = Book(
        title=book_in.title,
        author=book_in.author,
        isbn=book_in.isbn,
        category=book_in.category,
        published_year=book_in.published_year,
        description=book_in.description,
        total_copies=book_in.total_copies,
        available_copies=book_in.total_copies,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


@router.get("", response_model=Page[BookOut])
def list_books(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search by title or author"),
    category: Optional[str] = Query(None),
    author: Optional[str] = Query(None),
    available_only: bool = Query(False, description="Only show books with available copies"),
    db: Session = Depends(get_db),
):
    """Public: browse/search the catalog. Available to any authenticated or anonymous caller."""
    query = db.query(Book)

    if search:
        like = f"%{search}%"
        query = query.filter((Book.title.ilike(like)) | (Book.author.ilike(like)))
    if category:
        query = query.filter(Book.category.ilike(f"%{category}%"))
    if author:
        query = query.filter(Book.author.ilike(f"%{author}%"))
    if available_only:
        query = query.filter(Book.available_copies > 0)

    total = query.count()
    items = (
        query.order_by(Book.title).offset((page - 1) * page_size).limit(page_size).all()
    )
    return Page(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)),
    )


@router.get("/{book_id}", response_model=BookOut)
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.put("/{book_id}", response_model=BookOut)
def update_book(
    book_id: int,
    payload: BookUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    data = payload.model_dump(exclude_unset=True)

    if "isbn" in data and data["isbn"] != book.isbn:
        if db.query(Book).filter(Book.isbn == data["isbn"]).first():
            raise HTTPException(status_code=400, detail="A book with this ISBN already exists")

    if "total_copies" in data:
        new_total = data["total_copies"]
        currently_issued = book.total_copies - book.available_copies
        if new_total < currently_issued:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Cannot set total_copies below {currently_issued}: "
                    f"that many copies are currently issued out."
                ),
            )
        book.available_copies = new_total - currently_issued

    for field, value in data.items():
        setattr(book, field, value)

    db.commit()
    db.refresh(book)
    return book


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.available_copies != book.total_copies:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a book while copies are still issued out",
        )
    db.delete(book)
    db.commit()
    return None
