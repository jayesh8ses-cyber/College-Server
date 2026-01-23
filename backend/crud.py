from pymongo.database import Database
from fastapi import HTTPException, status
import schemas, auth
from datetime import datetime
from bson import ObjectId

# Simple object wrapper for MongoDB data
class SimpleObj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def get_user(db: Database, user_id: str):
    """Get user by ID (username)"""
    try:
        user_data = db.users.find_one({"username": user_id})
        if user_data:
            user_data['id'] = user_data['username']
            return SimpleObj(**user_data)
        return None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user: {str(e)}"
        )


def get_user_by_username(db: Database, username: str):
    """Get user by username"""
    return get_user(db, username)


def create_user(db: Database, user: schemas.UserCreate):
    """Create a new user"""
    try:
        hashed_password = auth.get_password_hash(user.password)
        user_data = {
            "username": user.username,
            "email": user.email,
            "hashed_password": hashed_password,
            "is_senior": user.is_senior,
            "created_at": datetime.utcnow()
        }
        
        # Check if user already exists
        existing_user = db.users.find_one({"username": user.username})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Insert user
        db.users.insert_one(user_data)
        
        user_data['id'] = user.username
        return SimpleObj(**user_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}"
        )


def create_group(db: Database, group: schemas.GroupCreate, user_id: str):
    """Create a new group"""
    try:
        group_data = group.dict()
        group_data['creator_id'] = user_id
        group_data['created_at'] = datetime.utcnow()
        
        # Insert group
        result = db.groups.insert_one(group_data)
        
        # Get the inserted document
        group_data['id'] = str(result.inserted_id)
        group_data['_id'] = result.inserted_id
        
        return SimpleObj(**group_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating group: {str(e)}"
        )


def get_groups(db: Database, skip: int = 0, limit: int = 100):
    """Get all groups with pagination"""
    try:
        cursor = db.groups.find().skip(skip).limit(limit)
        groups = []
        for doc in cursor:
            doc['id'] = str(doc['_id'])
            groups.append(SimpleObj(**doc))
        return groups
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching groups: {str(e)}"
        )


def create_message(db: Database, message: schemas.MessageBase, sender_id: str):
    """Create a new message in a group"""
    try:
        # Verify group exists
        group = db.groups.find_one({"_id": ObjectId(message.group_id)})
        
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Group not found"
            )
        
        msg_data = message.dict()
        msg_data['sender_id'] = sender_id
        msg_data['timestamp'] = datetime.utcnow()
        msg_data['group_id'] = message.group_id
        
        # Insert message
        result = db.messages.insert_one(msg_data)
        
        msg_data['id'] = str(result.inserted_id)
        msg_data['_id'] = result.inserted_id
        
        return SimpleObj(**msg_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating message: {str(e)}"
        )


def get_messages(db: Database, group_id: str):
    """Get all messages for a group"""
    try:
        # Verify group exists
        group = db.groups.find_one({"_id": ObjectId(group_id)})
        
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Group not found"
            )
        
        # Get messages ordered by timestamp
        cursor = db.messages.find({"group_id": group_id}).sort("timestamp", 1)
        messages = []
        for doc in cursor:
            doc['id'] = str(doc['_id'])
            messages.append(SimpleObj(**doc))
        return messages
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching messages: {str(e)}"
        )
