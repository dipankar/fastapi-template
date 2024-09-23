from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime

class ItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = {}

class ItemCreate(ItemBase):
    pass

class Item(ItemBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    deleted: bool
    deleted_at: Optional[datetime]
    disabled: bool
    disabled_at: Optional[datetime]

    class Config:
        orm_mode = True

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    deleted: bool
    deleted_at: Optional[datetime]
    disabled: bool
    disabled_at: Optional[datetime]

    class Config:
        orm_mode = True