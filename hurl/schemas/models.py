"""Pydantic models for data API requests and responses."""

from typing import List, Optional, Any, Union, ClassVar
from pydantic import BaseModel, Field
from .base import ModelReprMixin


class DataItem(ModelReprMixin, BaseModel):
    """Represents a single data item with id, value, and optional tags."""
    
    id: int = Field(..., description="Unique identifier for the data item")
    value: float = Field(..., description="Numeric value of the data item")
    tags: Optional[List[str]] = Field(default=None, description="Optional list of tags")
    metadata: Optional[dict] = Field(default=None, description="Optional metadata dictionary")


class GetDataRequest(ModelReprMixin, BaseModel):
    """Request model for data retrieval."""
    
    # Fields to always include even if None
    always_include_fields: ClassVar[set] = {"limit"}
    
    site: str = Field(..., description="Site identifier")
    measurement: str = Field(..., description="Measurement type")
    from_date: Optional[str] = Field(default=None, description="Start date (ISO format)")
    to_date: Optional[str] = Field(default=None, description="End date (ISO format)")
    limit: Optional[int] = Field(default=None, description="Maximum number of records")
    filters: Optional[dict] = Field(default=None, description="Additional filters")


class GetDataResponse(ModelReprMixin, BaseModel):
    """Response model for data retrieval."""
    
    # Fields to always include even if None
    always_include_fields: ClassVar[set] = {"error_message"}
    
    status: str = Field(..., description="Response status (success, error, etc.)")
    data: Optional[List[DataItem]] = Field(default=None, description="List of data items")
    total_count: Optional[int] = Field(default=None, description="Total number of available records")
    error_message: Optional[str] = Field(default=None, description="Error message if status is error")
    metadata: Optional[dict] = Field(default=None, description="Response metadata")