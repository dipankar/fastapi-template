from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from .auth import auth_router
from .database import engine, Base
from .tasks import task_router
from .views import router as view_router
from .config import settings
import asyncio
from .database import get_db
from .websocket import websocket_endpoint
from .queue import broker


app = FastAPI(title="Simplified Web Framework")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables
Base.metadata.create_all(bind=engine)

# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(task_router, prefix="/api/tasks", tags=["tasks"])
app.include_router(view_router)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return {"message": "Welcome to the Simplified Web Framework"}

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Simplified Web Framework API",
        version="1.0.0",
        description="A simplified web framework with JWT authentication",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer Auth": {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "Enter: **'Bearer &lt;JWT&gt;'**, where JWT is the access token"
        }
    }
    # Apply it to all secured endpoints
    for path in openapi_schema["paths"]:
        if path not in ["/register", "/token"]:  # Exclude register and login routes
            openapi_schema["paths"][path]["security"] = [{"Bearer Auth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

async def get_current_user_ws(token: str, db: Session):
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


app.add_websocket_route("/ws", websocket_endpoint)

@app.on_event("startup")
async def startup_event():
    db = next(get_db())
    # Create default superuser if it doesn't exist
    if not db.query(User).filter(User.is_superuser == True).first():
        superuser = User(
            username="admin",
            email="admin@example.com",
            is_superuser=True,
            is_active=True
        )
        superuser.set_password("admin")  # You should implement this method in the User model
        db.add(superuser)
        db.commit()

    # Create default roles and permissions if they don't exist
    default_roles = ["admin", "user"]
    default_permissions = ["create", "read", "update", "delete"]
    
    for role_name in default_roles:
        if not db.query(Role).filter(Role.name == role_name).first():
            role = Role(name=role_name)
            db.add(role)
    
    for perm_name in default_permissions:
        if not db.query(Permission).filter(Permission.name == perm_name).first():
            permission = Permission(name=perm_name)
            db.add(permission)
    
    db.commit()
    broker.start()

@app.on_event("shutdown")
async def shutdown_event():
    # Stop the Dramatiq worker
    broker.stop()
