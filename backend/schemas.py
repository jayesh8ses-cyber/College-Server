from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class UserBase(BaseModel):
    username: str
    email: str
    is_senior: bool = False

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: str
    
    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class GroupBase(BaseModel):
    name: str
    description: Optional[str] = None

class GroupCreate(GroupBase):
    pass

class Group(GroupBase):
    id: str
    creator_id: str
    
    class Config:
        orm_mode = True

class MessageBase(BaseModel):
    content: str
    group_id: str

class MessageCreate(MessageBase):
    pass

class Message(MessageBase):
    id: str
    sender_id: str
    timestamp: datetime
    
    class Config:
        orm_mode = True
