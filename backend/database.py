
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

def get_db():
    if init_error:
        # We can't yield db if it failed. Raise http exception or yield None?
        # Better to raise exception inside the dependency usage but we are in a generator.
        # We'll handle checking this in the health endpoint or main.
        # For now yield None or raise. raising here might crash the request.
        pass 
    yield db

