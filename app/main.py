from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine, SessionLocal
from app.models import User, RoleEnum
from app.security import hash_password
from app.routers import auth, books, issues, users


def _bootstrap_admin() -> None:
    """Create a default admin account on first run if no users exist yet."""
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            admin = User(
                username=settings.DEFAULT_ADMIN_USERNAME,
                email=settings.DEFAULT_ADMIN_EMAIL,
                full_name="Library Administrator",
                hashed_password=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
                role=RoleEnum.admin,
            )
            db.add(admin)
            db.commit()
            print(
                f"[bootstrap] Created default admin user "
                f"'{settings.DEFAULT_ADMIN_USERNAME}' — change this password after first login."
            )
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _bootstrap_admin()
    yield


app = FastAPI(
    title="Library Management System API",
    description=(
        "A production-style backend for managing a library's book catalog, "
        "user accounts, and book issue/return workflow with fine calculation."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(books.router)
app.include_router(issues.router)


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "service": "Library Management System API"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}
