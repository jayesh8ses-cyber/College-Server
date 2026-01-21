
import sqlite3
import firebase_admin
from firebase_admin import credentials, firestore
import os
import sys

# Initialize Firebase
# Ensure serviceAccountKey.json is in the same directory
if not os.path.exists("serviceAccountKey.json"):
    print("Error: serviceAccountKey.json not found in the current directory.")
    sys.exit(1)

cred = credentials.Certificate("serviceAccountKey.json")
try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app(cred)

db = firestore.client()

# SQLite Connection
SQLITE_DB_PATH = "college_share.db" # Default name from database.py
if not os.path.exists(SQLITE_DB_PATH):
    print(f"Error: {SQLITE_DB_PATH} not found.")
    sys.exit(1)

conn = sqlite3.connect(SQLITE_DB_PATH)
cursor = conn.cursor()

def migrate_users():
    print("Migrating users...")
    cursor.execute("SELECT id, username, email, hashed_password, is_senior FROM users")
    users = cursor.fetchall()
    
    for user in users:
        user_id, username, email, hashed_password, is_senior = user
        # create document with username as ID for easy lookup, or auto-id
        # Using username as ID ensures uniqueness as per our logic
        user_doc_ref = db.collection("users").document(username)
        user_doc_ref.set({
            "username": username,
            "email": email,
            "hashed_password": hashed_password,
            "is_senior": bool(is_senior),
            "original_sqlite_id": user_id
        })
        print(f"  Migrated user: {username}")
    print("Users migrated.\n")

def migrate_groups_and_messages():
    print("Migrating groups...")
    cursor.execute("SELECT id, name, description, creator_id FROM groups")
    groups = cursor.fetchall()
    
    group_map = {} # Map old ID to new ID (auto-generated)

    for group in groups:
        old_id, name, description, creator_id = group
        
        # Get creator username
        cursor.execute("SELECT username FROM users WHERE id = ?", (creator_id,))
        creator = cursor.fetchone()
        creator_username = creator[0] if creator else "unknown"

        # Create new group in Firestore
        doc_ref = db.collection("groups").document()
        doc_ref.set({
            "name": name,
            "description": description,
            "creator_username": creator_username
        })
        group_map[old_id] = doc_ref.id
        print(f"  Migrated group: {name} ({old_id} -> {doc_ref.id})")
        
        # Migrate messages for this group
        migrate_messages(old_id, doc_ref.id, creator_username) # passing creator just in case? no needed.

    print("Groups migrated.\n")
    return group_map

def migrate_messages(sqlite_group_id, firestore_group_id, creator_username_hint):
    # print(f"    Migrating messages for group {sqlite_group_id}...")
    cursor.execute("SELECT id, content, sender_id, timestamp FROM messages WHERE group_id = ?", (sqlite_group_id,))
    messages = cursor.fetchall()
    
    for msg in messages:
        old_msg_id, content, sender_id, timestamp = msg
        
        # Get sender username
        cursor.execute("SELECT username FROM users WHERE id = ?", (sender_id,))
        sender = cursor.fetchone()
        sender_username = sender[0] if sender else "unknown"

        # Add to subcollection
        db.collection("groups").document(firestore_group_id).collection("messages").add({
            "content": content,
            "sender_username": sender_username,
            "timestamp": timestamp, # SQLite timestamp string, Firestore handles strings ok or parse if needed
            "original_sqlite_id": old_msg_id
        })
    # print(f"    Migrated {len(messages)} messages.")

if __name__ == "__main__":
    print("Starting migration...")
    migrate_users()
    migrate_groups_and_messages()
    print("Migration complete!")
    conn.close()
