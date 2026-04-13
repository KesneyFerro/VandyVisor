from datetime import datetime
from typing import Any, Dict, Optional, Type, TypeVar, Generic, List

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, func
from sqlalchemy.ext.declarative import as_declarative, declared_attr

from app.db.session import Base

# Type variable for the SQLAlchemy ORM models
ModelType = TypeVar("ModelType", bound=Base)

# Type variable for the Pydantic schemas used for data validation
SchemaType = TypeVar("SchemaType", bound=BaseModel)


@as_declarative()
class Base:
    id: Any
    __name__: str
    
    # Generate __tablename__ automatically based on class name
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
    
    # Common columns for all tables
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class CRUDBase(Generic[ModelType, SchemaType]):
    """
    Base class for CRUD operations.
    """
    
    def __init__(self, model: Type[ModelType]):
        self.model = model
    
    async def get(self, db_session, id: Any) -> Optional[ModelType]:
        """Get a record by id."""
        return await db_session.query(self.model).filter(self.model.id == id).first()
    
    async def get_multi(
        self, db_session, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        """Get multiple records."""
        return await db_session.query(self.model).offset(skip).limit(limit).all()
    
    async def create(self, db_session, *, obj_in: SchemaType) -> ModelType:
        """Create a new record."""
        obj_in_data = obj_in.dict()
        db_obj = self.model(**obj_in_data)
        db_session.add(db_obj)
        await db_session.commit()
        await db_session.refresh(db_obj)
        return db_obj
    
    async def update(
        self, db_session, *, db_obj: ModelType, obj_in: SchemaType
    ) -> ModelType:
        """Update a record."""
        obj_data = db_obj.__dict__
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        db_session.add(db_obj)
        await db_session.commit()
        await db_session.refresh(db_obj)
        return db_obj
    
    async def remove(self, db_session, *, id: int) -> ModelType:
        """Remove a record."""
        obj = await db_session.query(self.model).get(id)
        await db_session.delete(obj)
        await db_session.commit()
        return obj
