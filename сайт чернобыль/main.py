from fastapi import FastAPI, HTTPException, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import hashlib
import os
from db_config import engine, SessionLocal, Base
from user_models import User, Tour, Booking
import uvicorn

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Экскурсии в Чернобыль", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

@app.get("/")
async def read_root():
    file_path = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return HTMLResponse(content="<h1>Главная страница</h1>")

@app.get("/about")
async def read_about():
    file_path = os.path.join(BASE_DIR, "about.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return HTMLResponse(content="<h1>О поездках</h1>")

@app.get("/contacts")
async def read_contacts():
    file_path = os.path.join(BASE_DIR, "contacts.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return HTMLResponse(content="<h1>Контакты</h1>")

@app.post("/api/register")
async def register_user(
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    tour_type: str = Form("однодневный"),
    participants: int = Form(1),
    preferred_date: str = Form(None),
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")
    
    hashed_password = hash_password(password)
    
    new_user = User(
        name=name,
        email=email,
        phone=phone,
        password=hashed_password,
        tour_type=tour_type,
        participants=participants,
        preferred_date=preferred_date
    )
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        tour = db.query(Tour).filter(Tour.name == tour_type).first()
        if not tour:
            tour = Tour(name=tour_type, price=100 if tour_type == "однодневный" else 250)
            db.add(tour)
            db.commit()
        
        booking = Booking(
            user_id=new_user.id,
            tour_id=tour.id,
            participants=participants,
            total_price=tour.price * participants,
            status="подтверждено"
        )
        db.add(booking)
        db.commit()
        
        return JSONResponse(
            content={
                "message": "Регистрация успешна! Бронь создана.",
                "user_id": new_user.id,
                "booking_id": booking.id,
                "total_price": booking.total_price
            },
            status_code=201
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка базы данных")

@app.post("/api/login")
async def login_user(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    hashed_password = hash_password(password)
    user = db.query(User).filter(User.email == email, User.password == hashed_password).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    
    bookings = db.query(Booking).filter(Booking.user_id == user.id).all()
    bookings_data = []
    for booking in bookings:
        tour = db.query(Tour).filter(Tour.id == booking.tour_id).first()
        bookings_data.append({
            "id": booking.id,
            "tour": tour.name if tour else "Неизвестный тур",
            "participants": booking.participants,
            "total_price": booking.total_price,
            "status": booking.status,
            "created_at": booking.created_at.strftime("%d.%m.%Y %H:%M")
        })
    
    return JSONResponse(
        content={
            "message": "Вход выполнен успешно",
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "bookings": bookings_data
        }
    )

@app.get("/api/users")
async def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [
        {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "tour_type": user.tour_type,
            "created_at": user.created_at.strftime("%d.%m.%Y")
        }
        for user in users
    ]

@app.get("/api/bookings")
async def get_bookings(db: Session = Depends(get_db)):
    bookings = db.query(Booking).join(User).join(Tour).all()
    return [
        {
            "id": booking.id,
            "user_name": booking.user.name,
            "user_email": booking.user.email,
            "tour_name": booking.tour.name,
            "participants": booking.participants,
            "total_price": booking.total_price,
            "status": booking.status,
            "created_at": booking.created_at.strftime("%d.%m.%Y %H:%M")
        }
        for booking in bookings
    ]

@app.post("/api/add_tour")
async def add_tour(
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    duration: str = Form(...),
    db: Session = Depends(get_db)
):
    existing_tour = db.query(Tour).filter(Tour.name == name).first()
    if existing_tour:
        raise HTTPException(status_code=400, detail="Тур с таким названием уже существует")
    
    new_tour = Tour(
        name=name,
        description=description,
        price=price,
        duration=duration
    )
    
    db.add(new_tour)
    db.commit()
    db.refresh(new_tour)
    
    return JSONResponse(
        content={
            "message": "Тур добавлен успешно",
            "tour_id": new_tour.id,
            "name": new_tour.name
        },
        status_code=201
    )

@app.get("/api/tours")
async def get_tours(db: Session = Depends(get_db)):
    tours = db.query(Tour).all()
    return [
        {
            "id": tour.id,
            "name": tour.name,
            "description": tour.description,
            "price": tour.price,
            "duration": tour.duration,
            "available": tour.available
        }
        for tour in tours
    ]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)