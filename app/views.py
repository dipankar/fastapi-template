from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .database import get_db
from .models import Item, User
from .schemas import ItemCreate, UserCreate
from .auth import jwt_required, create_access_token, get_password_hash, verify_password

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.post("/register", response_class=JSONResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = get_password_hash(user.password)
    new_user = User(username=user.username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully"}

@router.post("/token", response_class=JSONResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/items", response_class=HTMLResponse)
@jwt_required()
async def list_items(request: Request, db: Session = Depends(get_db), current_user: User = Depends()):
    items = db.query(Item).filter(Item.owner_id == current_user.id).all()
    return templates.TemplateResponse("items.html", {"request": request, "items": items})

@router.post("/items", response_class=HTMLResponse)
@jwt_required()
async def create_item(
    request: Request,
    item: ItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends()
):
    new_item = Item(name=item.name, description=item.description, owner_id=current_user.id)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return templates.TemplateResponse("item_row.html", {"request": request, "item": new_item})

@router.delete("/items/{item_id}", response_class=HTMLResponse)
@jwt_required()
async def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends()
):
    item = db.query(Item).filter(Item.id == item_id, Item.owner_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return ""

@router.get("/protected", response_class=JSONResponse)
@jwt_required()
async def protected_route(current_user: User = Depends()):
    return {"message": f"Hello, {current_user.username}! This is a protected route."}