from datetime import datetime
from typing import Optional, Generic, TypeVar, List, Annotated

from pydantic import BaseModel, Field, ConfigDict, StringConstraints

from app.models import RoleEnum, IssueStatusEnum

T = TypeVar("T")

# Plain syntax-only email validation (no live DNS/MX deliverability lookups).
# EmailStr from pydantic[email] performs real DNS checks via email-validator,
# which makes the API fail on any host without outbound DNS access. A simple
# pattern is more than sufficient for this project and keeps registration
# fully self-contained.
EmailStr = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        max_length=120,
    ),
]


# ---------------------------------------------------------------------------
# Auth / Users
# ---------------------------------------------------------------------------
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=6, max_length=100)


class UserCreateByAdmin(UserCreate):
    role: RoleEnum = RoleEnum.student


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    full_name: str
    role: RoleEnum
    is_active: bool
    created_at: datetime


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    role: Optional[RoleEnum] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: RoleEnum
    username: str


# ---------------------------------------------------------------------------
# Books
# ---------------------------------------------------------------------------
class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=150)
    isbn: str = Field(min_length=5, max_length=20)
    category: str = Field(min_length=1, max_length=80)
    published_year: Optional[int] = None
    description: Optional[str] = None
    total_copies: int = Field(default=1, ge=1)


class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    isbn: Optional[str] = None
    category: Optional[str] = None
    published_year: Optional[int] = None
    description: Optional[str] = None
    total_copies: Optional[int] = Field(default=None, ge=0)


class BookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str
    isbn: str
    category: str
    published_year: Optional[int]
    description: Optional[str]
    total_copies: int
    available_copies: int
    created_at: datetime


# ---------------------------------------------------------------------------
# Issue records
# ---------------------------------------------------------------------------
class IssueCreate(BaseModel):
    book_id: int
    user_id: Optional[int] = None  # admin can issue on behalf of a student


class IssueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    user_id: int
    issue_date: datetime
    due_date: datetime
    return_date: Optional[datetime]
    fine_amount: float
    fine_paid: bool
    status: IssueStatusEnum
    book: BookOut
    user: UserOut


class ReturnBookRequest(BaseModel):
    issue_id: int


# ---------------------------------------------------------------------------
# Generic pagination wrapper
# ---------------------------------------------------------------------------
class Page(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
