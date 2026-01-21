
import firebase_admin
from firebase_admin import credentials, firestore
import os

# Initialize Firebase
import json
import traceback

init_error = None

try:
    cred_path = "serviceAccountKey.json"
    if os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        try:
            firebase_admin.get_app()
        except ValueError:
            firebase_admin.initialize_app(cred)
    elif os.getenv("FIREBASE_CREDENTIALS"):
        # Parse JSON from env var
        try:
            cred_json = json.loads(os.getenv("FIREBASE_CREDENTIALS"))
            cred = credentials.Certificate(cred_json)
            try:
                firebase_admin.get_app()
            except ValueError:
                firebase_admin.initialize_app(cred)
        except Exception as e:
            init_error = f"Failed to parse FIREBASE_CREDENTIALS: {str(e)}"
            raise e
    else:
        # Fallback
        try:
            firebase_admin.get_app()
        except ValueError:
            firebase_admin.initialize_app()
except Exception as e:
    init_error = f"Firebase Init Error: {str(e)}\n{traceback.format_exc()}"

db = None
if not init_error:
    try:
        db = firestore.client()
    except Exception as e:
        init_error = f"Firestore Client Error: {str(e)}"

from fastapi import HTTPException, status

def get_db():
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


