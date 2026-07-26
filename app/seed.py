"""
Populate the database with a handful of real, sample book records so the
API is immediately explorable after setup.

Run with:  python -m app.seed
"""
from app.database import Base, engine, SessionLocal
from app.models import Book

SAMPLE_BOOKS = [
    dict(title="Clean Code", author="Robert C. Martin", isbn="9780132350884",
         category="Software Engineering", published_year=2008,
         description="A handbook of agile software craftsmanship.", total_copies=3),
    dict(title="Design Patterns", author="Erich Gamma, Richard Helm, Ralph Johnson, John Vlissides",
         isbn="9780201633610", category="Software Engineering", published_year=1994,
         description="Elements of reusable object-oriented software.", total_copies=2),
    dict(title="The Pragmatic Programmer", author="David Thomas, Andrew Hunt",
         isbn="9780135957059", category="Software Engineering", published_year=2019,
         description="Your journey to mastery, 20th anniversary edition.", total_copies=2),
    dict(title="Introduction to Algorithms", author="Thomas H. Cormen",
         isbn="9780262046305", category="Computer Science", published_year=2022,
         description="Comprehensive coverage of modern algorithms and data structures.",
         total_copies=4),
    dict(title="Database System Concepts", author="Abraham Silberschatz",
         isbn="9780078022159", category="Computer Science", published_year=2019,
         description="Foundational concepts of database systems and design.", total_copies=3),
    dict(title="Computer Networking: A Top-Down Approach", author="James F. Kurose",
         isbn="9780133594140", category="Computer Science", published_year=2016,
         description="A top-down approach to understanding computer networks.",
         total_copies=2),
    dict(title="Sapiens: A Brief History of Humankind", author="Yuval Noah Harari",
         isbn="9780062316097", category="History", published_year=2015,
         description="An exploration of the history and impact of Homo sapiens.",
         total_copies=2),
    dict(title="Atomic Habits", author="James Clear", isbn="9780735211292",
         category="Self-Help", published_year=2018,
         description="An easy and proven way to build good habits and break bad ones.",
         total_copies=3),
    dict(title="The Pragmatic Thinking & Learning", author="Andy Hunt",
         isbn="9781934356050", category="Self-Help", published_year=2008,
         description="Refactor your wetware — how to become a better programmer.",
         total_copies=1),
    dict(title="Deep Work", author="Cal Newport", isbn="9781455586691",
         category="Self-Help", published_year=2016,
         description="Rules for focused success in a distracted world.", total_copies=2),
]


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        added = 0
        for data in SAMPLE_BOOKS:
            if not db.query(Book).filter(Book.isbn == data["isbn"]).first():
                book = Book(**data, available_copies=data["total_copies"])
                db.add(book)
                added += 1
        db.commit()
        print(f"[seed] Added {added} new sample book(s). Total books in catalog: "
              f"{db.query(Book).count()}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
