from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from .database import get_db
from .models.user import User
from .config import settings
import secrets
import smtplib
from email.mime.text import MIMEText
from google.oauth2 import id_token
from google.auth.transport import requests
import jwt as apple_jwt

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

def send_magic_link(email: str, token: str):
    msg = MIMEText(f"Your magic link is: {settings.BASE_URL}/auth/verify/{token}")
    msg['Subject'] = "Your Magic Link"
    msg['From'] = settings.EMAIL_FROM
    msg['To'] = email
    
    with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(msg)

@router.post("/magic-link")
async def send_magic_link_email(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    token = secrets.token_urlsafe()
    user.magic_link_token = token
    user.magic_link_expiry = datetime.utcnow() + timedelta(hours=1)
    db.commit()

    send_magic_link(email, token)
    return {"message": "Magic link sent to your email"}

@router.get("/verify/{token}")
async def verify_magic_link(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.magic_link_token == token, User.magic_link_expiry > datetime.utcnow()).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/gmail-login")
async def gmail_login(token: str, db: Session = Depends(get_db)):
    try:
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), settings.GOOGLE_CLIENT_ID)
        email = idinfo['email']
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid token")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, username=email, auth_provider='gmail')
        db.add(user)
        db.commit()

    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/apple-login")
async def apple_login(token: str, db: Session = Depends(get_db)):
    try:
        decoded = apple_jwt.decode(token, settings.APPLE_PUBLIC_KEY, algorithms=['RS256'])
        email = decoded['email']
    except:
        raise HTTPException(status_code=400, detail="Invalid token")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, username=email, auth_provider='apple')
        db.add(user)
        db.commit()

    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}