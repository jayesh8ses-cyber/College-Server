from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pymongo.database import Database
from jose import JWTError, jwt
import database, auth, schemas

# Use tokenUrl with /api prefix to work with Vercel routing
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")

# Import get_db from database module instead of redefining it
def get_db():
    """Wrapper to use database.get_db() as a dependency"""
    yield from database.get_db()


async def get_current_user(token: str = Depends(oauth2_scheme), db: Database = Depends(get_db)):
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
    
    # Get user from MongoDB
    user_data = db.users.find_one({"username": token_data.username})
    
    if not user_data:
        raise credentials_exception
    
    # Return object with attribute access for compatibility
    class UserObj:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            self.id = kwargs.get('username')  # ID in schema is str
            
    return UserObj(**user_data)
