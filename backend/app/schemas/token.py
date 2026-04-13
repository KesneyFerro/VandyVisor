from pydantic import BaseModel


class Token(BaseModel):
    """Schema for authentication token"""
    access_token: str
    token_type: str
