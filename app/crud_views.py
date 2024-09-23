from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from .database import get_db
from . import models, schemas
from .auth import get_current_user
import inflect

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
p = inflect.engine()

def get_model_fields(model):
    return [column.key for column in inspect(model).columns if column.key not in ['id', 'created_at', 'updated_at']]

def get_foreign_keys(model):
    return [column.key for column in inspect(model).columns if column.foreign_keys]

def check_permission(user: models.User, action: str, model_name: str):
    required_permission = f"{action}_{model_name}"
    for role in user.roles:
        if any(perm.name == required_permission for perm in role.permissions):
            return True
    raise HTTPException(status_code=403, detail="Permission denied")

@router.get("/{model_name}", response_class=HTMLResponse)
async def list_items(request: Request, model_name: str, page: int = 1, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_permission(current_user, "read", model_name)
    model = getattr(models, model_name.capitalize())
    items = db.query(model).offset((page - 1) * 10).limit(10).all()
    total = db.query(model).count()
    return templates.TemplateResponse("crud_list.html", {
        "request": request,
        "items": items,
        "model_name": model_name,
        "fields": get_model_fields(model),
        "page": page,
        "total_pages": (total - 1) // 10 + 1
    })

@router.get("/{model_name}/create", response_class=HTMLResponse)
async def create_form(request: Request, model_name: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_permission(current_user, "create", model_name)
    model = getattr(models, model_name.capitalize())
    fields = get_model_fields(model)
    foreign_keys = get_foreign_keys(model)
    fk_options = {}
    for fk in foreign_keys:
        fk_model = getattr(models, fk.replace("_id", "").capitalize())
        fk_options[fk] = db.query(fk_model).all()
    return templates.TemplateResponse("crud_form.html", {
        "request": request,
        "model_name": model_name,
        "fields": fields,
        "foreign_keys": foreign_keys,
        "fk_options": fk_options,
        "item": None
    })

@router.post("/{model_name}/create", response_class=HTMLResponse)
async def create_item(request: Request, model_name: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_permission(current_user, "create", model_name)
    model = getattr(models, model_name.capitalize())
    schema = getattr(schemas, f"{model_name.capitalize()}Create")
    form_data = await request.form()
    try:
        item_data = schema(**form_data)
        db_item = model(**item_data.dict())
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return templates.TemplateResponse("crud_item.html", {
            "request": request,
            "item": db_item,
            "model_name": model_name,
            "fields": get_model_fields(model)
        })
    except Exception as e:
        return templates.TemplateResponse("crud_form.html", {
            "request": request,
            "model_name": model_name,
            "fields": get_model_fields(model),
            "foreign_keys": get_foreign_keys(model),
            "fk_options": {fk: db.query(getattr(models, fk.replace("_id", "").capitalize())).all() for fk in get_foreign_keys(model)},
            "item": None,
            "error": str(e)
        })
    
@router.delete("/{model_name}/{item_id}", response_class=HTMLResponse)
async def delete_item(request: Request, model_name: str, item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_permission(current_user, "delete", model_name)
    model = getattr(models, model_name.capitalize())
    item = db.query(model).filter(model.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return ""

# Add a new route for user management
@router.get("/users/manage", response_class=HTMLResponse)
async def manage_users(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_permission(current_user, "manage", "users")
    users = db.query(models.User).all()
    roles = db.query(models.Role).all()
    return templates.TemplateResponse("manage_users.html", {
        "request": request,
        "users": users,
        "roles": roles
    })

@router.post("/users/{user_id}/roles", response_class=HTMLResponse)
async def update_user_roles(user_id: int, role_ids: List[int], db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_permission(current_user, "manage", "users")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    roles = db.query(models.Role).filter(models.Role.id.in_(role_ids)).all()
    user.roles = roles
    db.commit()
    return templates.TemplateResponse("user_roles.html", {"request": request, "user": user})