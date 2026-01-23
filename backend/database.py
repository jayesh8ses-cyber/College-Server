from pymongo import MongoClient
from fastapi import HTTPException, status
import os
import sys

# MongoDB connection
init_error = None
db = None
client = None

print("=== MONGODB INITIALIZATION DEBUG ===", file=sys.stderr)

try:
    # Get MongoDB connection string from environment
    mongodb_uri = os.getenv("MONGODB_URI")
    
    print(f"MONGODB_URI exists: {mongodb_uri is not None}", file=sys.stderr)
    
    if not mongodb_uri:
        init_error = "MONGODB_URI environment variable not set"
        print(f"ERROR: {init_error}", file=sys.stderr)
    else:
        print(f"Connection string length: {len(mongodb_uri)}", file=sys.stderr)
        print(f"Connection string starts with: {mongodb_uri[:20]}...", file=sys.stderr)
        
        # Connect to MongoDB
        print("Attempting MongoDB connection...", file=sys.stderr)
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        
        # Get database (extract db name from URI or use default)
        db = client.college_server
        
        # Test connection
        print("Testing connection with server_info()...", file=sys.stderr)
        info = client.server_info()
        print(f"MongoDB connected successfully! Version: {info.get('version')}", file=sys.stderr)
        
except Exception as e:
    init_error = f"MongoDB Connection Error: {str(e)}"
    print(f"EXCEPTION: {init_error}", file=sys.stderr)
    print(f"Exception type: {type(e).__name__}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    db = None

print("=== MONGODB INITIALIZATION COMPLETE ===", file=sys.stderr)
print(f"Final status - db is None: {db is None}, init_error: {init_error}", file=sys.stderr)


def get_db():
    """Dependency to get MongoDB database"""
    if init_error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database initialization failed: {init_error}"
        )
    if not db:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database client is not initialized"
        )
    yield db
