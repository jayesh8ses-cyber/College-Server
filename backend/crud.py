
from google.cloud import firestore
from fastapi import HTTPException, status
import schemas, auth
import datetime

# Simple object wrapper for Firestore data
class SimpleObj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def get_user(db: firestore.Client, user_id: str):
    """Get user by ID (username)"""
    try:
        doc = db.collection("users").document(user_id).get()
        if doc.exists:
            data = doc.to_dict()
            data['id'] = user_id
            return SimpleObj(**data)
        return None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user: {str(e)}"
        )


def get_user_by_username(db: firestore.Client, username: str):
    """Get user by username (using username as doc ID)"""
    return get_user(db, username)


def create_user(db: firestore.Client, user: schemas.UserCreate):
    """Create a new user"""
    try:
        hashed_password = auth.get_password_hash(user.password)
        user_data = {
            "username": user.username,
            "email": user.email,
            "hashed_password": hashed_password,
            "is_senior": user.is_senior
        }
        
        # Check if user already exists
        existing_user = db.collection("users").document(user.username).get()
        if existing_user.exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Create user document
        db.collection("users").document(user.username).set(user_data)
        
        user_data['id'] = user.username
        return SimpleObj(**user_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}"
        )


def create_group(db: firestore.Client, group: schemas.GroupCreate, user_id: str):
    """Create a new group"""
    try:
        group_data = group.dict()
        group_data['creator_id'] = user_id
        group_data['created_at'] = firestore.SERVER_TIMESTAMP
        
        # Auto-generate ID
        _, doc_ref = db.collection("groups").add(group_data)
        
        # Fetch the document to get the server timestamp
        created_doc = doc_ref.get()
        group_data = created_doc.to_dict()
        group_data['id'] = doc_ref.id
        
        return SimpleObj(**group_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating group: {str(e)}"
        )


def get_groups(db: firestore.Client, skip: int = 0, limit: int = 100):
    """Get all groups with pagination"""
    try:
        docs = db.collection("groups").limit(limit).offset(skip).stream()
        groups = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            groups.append(SimpleObj(**data))
        return groups
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching groups: {str(e)}"
        )


def create_message(db: firestore.Client, message: schemas.MessageBase, sender_id: str):
    """Create a new message in a group"""
    try:
        msg_data = message.dict()
        msg_data['sender_id'] = sender_id
        msg_data['timestamp'] = firestore.SERVER_TIMESTAMP
        
        # Verify group exists
        group_ref = db.collection("groups").document(message.group_id)
        group_doc = group_ref.get()
        
        if not group_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Group not found"
            )
        
        # Add message to subcollection
        _, doc_ref = group_ref.collection("messages").add(msg_data)
        
        # Fetch the created message to get server timestamp
        created_msg = doc_ref.get()
        msg_data = created_msg.to_dict()
        msg_data['id'] = doc_ref.id
        
        return SimpleObj(**msg_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating message: {str(e)}"
        )


def get_messages(db: firestore.Client, group_id: str):
    """Get all messages for a group"""
    try:
        # Verify group exists
        group_ref = db.collection("groups").document(group_id)
        group_doc = group_ref.get()
        
        if not group_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Group not found"
            )
        
        # Get messages ordered by timestamp
        docs = group_ref.collection("messages").order_by("timestamp").stream()
        messages = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            messages.append(SimpleObj(**data))
        return messages
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching messages: {str(e)}"
        )
