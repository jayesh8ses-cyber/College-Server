
import firebase_admin
from firebase_admin import credentials, firestore
import os

# Initialize Firebase
# Check if running in a cloud environment where credentials might be auto-discovered,
# or look for the local key file, OR check for env var (common in Vercel/Heroku).
import json

cred_path = "serviceAccountKey.json"
if os.path.exists(cred_path):
    cred = credentials.Certificate(cred_path)
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app(cred)
elif os.getenv("FIREBASE_CREDENTIALS"):
    # Parse JSON from env var
    cred_json = json.loads(os.getenv("FIREBASE_CREDENTIALS"))
    cred = credentials.Certificate(cred_json)
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app(cred)
else:
    # Fallback for environments with default credentials
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app()

db = firestore.client()

def get_db():
    yield db
