from pymongo import MongoClient
from fastapi import HTTPException, status
import os

# MongoDB connection
init_error = None
db = None
client = None

try:
    # Get MongoDB connection string from environment
    mongodb_uri = os.getenv("MONGODB_URI")
    
    if not mongodb_uri:
        init_error = "MONGODB_URI environment variable not set"
    else:
        # Connect to MongoDB
        client = MongoClient(mongodb_uri)
        
        # Get database (extract db name from URI or use default)
        db = client.college_server
        
        # Test connection
        client.server_info()
        
except Exception as e:
    init_error = f"MongoDB Connection Error: {str(e)}"
    db = None


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
