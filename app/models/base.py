from sqlalchemy import Column, DateTime, Boolean, String, Integer, func, event
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Query
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime
import json
from typing import Any, Dict
from fastapi import WebSocket
from .queue import send_model_update

class BaseQuery(Query):
    def get(self, ident):
        # Override get method to exclude deleted items
        obj = super(BaseQuery, self).get(ident)
        if obj is not None and obj.deleted:
            return None
        return obj

    def __iter__(self):
        # Exclude deleted items from iteration
        return filter(lambda obj: not obj.deleted, super(BaseQuery, self).__iter__())

class Base:
    query_class = BaseQuery

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime)
    disabled = Column(Boolean, default=False)
    disabled_at = Column(DateTime)
    _meta_data = Column('meta_data', String)

    @hybrid_property
    def meta_data(self) -> Dict[str, Any]:
        return json.loads(self._meta_data) if self._meta_data else {}

    @meta_data.setter
    def meta_data(self, value: Dict[str, Any]):
        self._meta_data = json.dumps(value)

    def delete(self):
        self.deleted = True
        self.deleted_at = datetime.utcnow()

    def disable(self):
        self.disabled = True
        self.disabled_at = datetime.utcnow()

    def enable(self):
        self.disabled = False
        self.disabled_at = None

    @classmethod
    def get_by_id(cls, session, id):
        return session.query(cls).filter(cls.id == id, cls.deleted == False).first()
    
    @classmethod
    async def get_related_users(cls, db, item_id) -> List[int]:
        """
        This method should be overridden in child classes to return a list of user IDs
        that should receive updates for this item.
        """
        raise NotImplementedError("get_related_users must be implemented in child classes")

    @classmethod
    def notify_related_users(cls, db, item_id, action):
        related_users = cls.get_related_users(db, item_id)
        for user_id in related_users:
            send_model_update.send(user_id, cls.__name__, item_id, action)

@event.listens_for(Base, 'after_update', propagate=True)
def after_update(mapper, connection, target):
    target.notify_related_users(connection, target.id, "update")

@event.listens_for(Base, 'after_insert', propagate=True)
def after_insert(mapper, connection, target):
    target.notify_related_users(connection, target.id, "create")

@event.listens_for(Base, 'after_delete', propagate=True)
def after_delete(mapper, connection, target):
    target.notify_related_users(connection, target.id, "delete")

@event.listens_for(Base, 'before_insert', propagate=True)
def set_created_updated_at(mapper, connection, target):
    now = datetime.utcnow()
    target.created_at = now
    target.updated_at = now

@event.listens_for(Base, 'before_update', propagate=True)
def set_updated_at(mapper, connection, target):
    target.updated_at = datetime.utcnow()

@event.listens_for(Base, 'load', propagate=True)
def receive_load(target, context):
    # Deserialize meta_data when the object is loaded
    target.meta_data = json.loads(target._meta_data) if target._meta_data else {}

@event.listens_for(Base, 'before_insert', propagate=True)
@event.listens_for(Base, 'before_update', propagate=True)
def receive_before_save(mapper, connection, target):
    # Serialize meta_data before saving
    target._meta_data = json.dumps(target.meta_data) if target.meta_data else None