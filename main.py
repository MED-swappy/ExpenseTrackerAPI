import os
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import create_engine, Float, String,  Integer, func, CheckConstraint, select
from sqlalchemy.orm import sessionmaker, DeclarativeBase, mapped_column, Mapped, Session
from pydantic import BaseModel
from datetime import datetime


DATABASE_URL = "os.environ["DATABASE_URL"]"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI()


class CreateExpense(BaseModel):
    name : str
    amount : int
    price : float
    category : str
    

class PatchExpense(BaseModel):
    name : str | None = None
    amount : int | None = None
    price : float | None = None
    category : str | None = None


class Base(DeclarativeBase):
  pass

class Expenses(Base):
    __tablename__ = "Expenses"
    id : Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name : Mapped[str] = mapped_column(String(100), nullable=False)
    amount : Mapped[int] = mapped_column(Integer, nullable=False)
    price : Mapped[float] = mapped_column(Float(precision=3), nullable=False)
    category : Mapped[str] = mapped_column(String(100), nullable=False)
    created_at : Mapped[datetime] = mapped_column(server_default= func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("price >= 0", name="price_non_negative!"),
        CheckConstraint("amount >= 1", name="amount_non_negative_non_zero!")
        )
 
Base.metadata.create_all(engine)

@app.get("/")
def root():
    return {"message" : "Welcome to my Expense Tracker API!"}

@app.get("/expense")
def get_expenses(db: Session = Depends(get_db)):
    return db.query(Expenses).all()

@app.post("/expense")
def post_expenses(exp : CreateExpense, db: Session = Depends(get_db)):
    new_expense = Expenses(
        name = exp.name,
        amount= exp.amount,
        price = exp.price,
        category = exp.category
    )
    try:
        db.add(new_expense)
        db.commit()
        db.refresh(new_expense)
    except:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    return new_expense


@app.get("/expense/total")
def get_expenses_total(db: Session = Depends(get_db)):
    query = db.scalar(select(func.sum(Expenses.price * Expenses.amount)))
    if query is None:
         raise HTTPException(status_code=404, detail="The Expenses Table is EMPTY!")
    return {"total_spent": round(query, 2)}

@app.get("/expense/by-category")
def get_expenses_by_category(db: Session = Depends(get_db)):

    results = db.query(
        Expenses.category,
        func.sum(Expenses.price * Expenses.amount)
    ).group_by(Expenses.category).all()

    if not results:
        raise HTTPException(
            status_code=404,
            detail="The Expenses Table is EMPTY!"
        )

    return [
        {"category": category, "total_spent": round(total, 2)}
        for category, total in results
    ]

@app.get("/expense/{id}")
def get_expenses_by_id(id: int, db: Session = Depends(get_db)):
    query = db.query(Expenses).filter(Expenses.id == id).first()
    if query is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The Corresponding id doesn't exist!")
    return query


@app.patch("/expense/{id}")
def patch_expense(id: int,exp: PatchExpense , db: Session = Depends(get_db)):
    query = db.query(Expenses).filter(Expenses.id == id).first()
    if query is None:
       raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The Corresponding id doesn't exist!")
    if exp.name is not None:
       query.name = exp.name
    if exp.price is not None:
       query.price = exp.price
    if exp.category is not None:
       query.category = exp.category
    if exp.amount is not None:
       query.amount = exp.amount
    db.commit()
    db.refresh(query)
    return query

@app.delete("/expense/{id}")
def delete_expense(id: int, db: Session = Depends(get_db)):
    query = db.query(Expenses).filter(Expenses.id == id).first()
    if query is None:
      raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The Corresponding id doesn't exist!")
    db.delete(query)
    db.commit()
    return {"message" : "the Expense was deleted successfully!"}