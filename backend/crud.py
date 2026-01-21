
from google.cloud import firestore
from . import schemas, auth, models
import datetime

# We are mocking models.User behavior with a simple class or dict in deps, 
# but here we return raw dicts or objects that schemas can parse.
# Schemas use orm_mode=True, so objects with attributes are expected.

class SimpleObj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

def get_user(db: firestore.Client, user_id: str):
    # logic assumes user_id is the doc ID (username)
    doc = db.collection("users").document(user_id).get()
    if doc.exists:
        data = doc.to_dict()
        data['id'] = user_id
        return SimpleObj(**data)
    return None

def get_user_by_username(db: firestore.Client, username: str):
    # In our design, username is the doc ID.
    return get_user(db, username)

def create_user(db: firestore.Client, user: schemas.UserCreate):
    hashed_password = auth.get_password_hash(user.password)
    user_data = {
        "username": user.username,
        "email": user.email,
        "hashed_password": hashed_password,
        "is_senior": user.is_senior
    }
    # Use username as document ID
    db.collection("users").document(user.username).set(user_data)
    
    user_data['id'] = user.username
    return SimpleObj(**user_data)

def create_group(db: firestore.Client, group: schemas.GroupCreate, user_id: str):
    group_data = group.dict()
    group_data['creator_id'] = user_id
    
    # Auto-generate ID
    _, doc_ref = db.collection("groups").add(group_data)
    
    group_data['id'] = doc_ref.id
    return SimpleObj(**group_data)

def get_groups(db: firestore.Client, skip: int = 0, limit: int = 100):
    # Firestore offset/limit
    docs = db.collection("groups").limit(limit).offset(skip).stream() # offset might be inefficient in fs but ok for now
    groups = []
    for doc in docs:
        data = doc.to_dict()
        data['id'] = doc.id
        groups.append(SimpleObj(**data))
    return groups

# Messages
# Note: In main.py, create_message_for_group called internal crud logic? No, it called db.add direct in main.py? 
# Let's check main.py again. Ah, main.py has `create_message_for_group` logic inline: 
# `db_message = models.Message(...)`. We should probably move that to crud or update main.py to use this.
# Let's add message support here to be clean.


def create_message(db: firestore.Client, message: schemas.MessageBase, sender_id: str):
    msg_data = message.dict()
    msg_data['sender_id'] = sender_id
    msg_data['timestamp'] = datetime.datetime.utcnow()
    
    # Store in subcollection or root?
    # Structure: groups/{group_id}/messages/{message_id}
    # group_id is in message.group_id
    
    # Check if group exists first? Optional but good.
    group_ref = db.collection("groups").document(message.group_id)
    # verify existence if needed, or just write.
    
    _, doc_ref = group_ref.collection("messages").add(msg_data)
    
    msg_data['id'] = doc_ref.id
    return SimpleObj(**msg_data)

def get_messages(db: firestore.Client, group_id: str):
    docs = db.collection("groups").document(group_id).collection("messages").order_by("timestamp").stream()
    messages = []
    for doc in docs:
        data = doc.to_dict()
        data['id'] = doc.id
        messages.append(SimpleObj(**data))
    return messages
