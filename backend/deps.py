from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from google.cloud import firestore
from jose import JWTError, jwt
import database, auth, schemas

# Use tokenUrl with /api prefix to work with Vercel routing
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")

# Import get_db from database module instead of redefining it
def get_db():
    """Wrapper to use database.get_db() as a dependency"""
    yield from database.get_db()



async def get_current_user(token: str = Depends(oauth2_scheme), db: firestore.Client = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    # helper to get user from firestore
    # We used username as doc ID in migration, let's stick to that or query?
    # In crud (to be written), we might use username as ID.
    doc_ref = db.collection("users").document(token_data.username)
    doc = doc_ref.get()
    
    if not doc.exists:
        raise credentials_exception
    
    user_data = doc.to_dict()
    # Return object with attribute access for compatibility? 
    # Or just dict if we update code to use dicts.
    # Pydantic models (User) can read from dicts if orm_mode=False or specific handling.
    # models.User was a sqlalchemy class. We should probably return a SimpleNamespace or Pydantic model.
    # Let's map it to a simple class or the Schema itself if possible, but the rest of the app expects attributes.
    
    class UserObj:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            self.id = kwargs.get('username') # ID in schema is str.
            
    return UserObj(**user_data)

