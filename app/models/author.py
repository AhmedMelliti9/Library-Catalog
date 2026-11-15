from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class AuthorCreate(BaseModel):
    first_name: str
    last_name: str
    nationality: Optional[str] = None


class AuthorUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    nationality: Optional[str] = None


class AuthorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    nationality: Optional[str]
    created_at: datetime
