"""
Base repository with common CRUD operations.
"""

import uuid
from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.base import Base

# Type variable for model classes
ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    Base repository providing common CRUD operations.
    
    Subclasses should specify the model class.
    """
    
    model: Type[ModelT]
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, id: uuid.UUID) -> Optional[ModelT]:
        """
        Get a single entity by ID.
        
        Args:
            id: Entity UUID
            
        Returns:
            Entity or None if not found
        """
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelT]:
        """
        Get all entities with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum records to return
            
        Returns:
            List of entities
        """
        result = await self.session.execute(
            select(self.model)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def count(self) -> int:
        """
        Count total entities.
        
        Returns:
            Total count
        """
        result = await self.session.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar() or 0
    
    async def create(self, entity: ModelT) -> ModelT:
        """
        Create a new entity.
        
        Args:
            entity: Entity to create
            
        Returns:
            Created entity with ID
        """
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity
    
    async def create_many(self, entities: List[ModelT]) -> List[ModelT]:
        """
        Create multiple entities.
        
        Args:
            entities: List of entities to create
            
        Returns:
            Created entities with IDs
        """
        self.session.add_all(entities)
        await self.session.flush()
        for entity in entities:
            await self.session.refresh(entity)
        return entities
    
    async def update(self, entity: ModelT) -> ModelT:
        """
        Update an existing entity.
        
        Args:
            entity: Entity with updated values
            
        Returns:
            Updated entity
        """
        await self.session.flush()
        await self.session.refresh(entity)
        return entity
    
    async def delete(self, entity: ModelT) -> None:
        """
        Delete an entity.
        
        Args:
            entity: Entity to delete
        """
        await self.session.delete(entity)
        await self.session.flush()
    
    async def delete_by_id(self, id: uuid.UUID) -> bool:
        """
        Delete an entity by ID.
        
        Args:
            id: Entity UUID
            
        Returns:
            True if deleted, False if not found
        """
        entity = await self.get_by_id(id)
        if entity:
            await self.delete(entity)
            return True
        return False
    
    async def exists(self, id: uuid.UUID) -> bool:
        """
        Check if an entity exists.
        
        Args:
            id: Entity UUID
            
        Returns:
            True if exists
        """
        result = await self.session.execute(
            select(func.count()).select_from(self.model).where(self.model.id == id)
        )
        return (result.scalar() or 0) > 0
