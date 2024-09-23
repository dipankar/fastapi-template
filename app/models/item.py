from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base

class Item(Base):
    __tablename__ = 'items'

    name = Column(String, index=True)
    description = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="items")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.meta_data = kwargs.get('meta_data', {})