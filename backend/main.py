from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import sys

# Minimal Debug Mode
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {
        "status": "ok", 
        "message": "Alive (Minimal Mode)", 
        "cwd": os.getcwd(),
        "path": sys.path
    }

@app.get("/")
def read_root():
    return {"Hello": "World"}

# All other logic commented out to isolate crash
# ...


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    if database.init_error:
        return {"status": "error", "detail": database.init_error}
    if not database.db:
        return {"status": "error", "detail": "Database client is None"}
    return {"status": "ok", "message": "Backend is running and connected to Firebase"}


@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: firestore.Client = Depends(deps.get_db)):
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(
        data={"sub": user.username}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: firestore.Client = Depends(deps.get_db)):
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return crud.create_user(db=db, user=user)

@app.get("/users/me", response_model=schemas.User)
async def read_users_me(current_user: schemas.User = Depends(deps.get_current_user)):
    return current_user

@app.post("/groups/", response_model=schemas.Group)
def create_group(
    group: schemas.GroupCreate, 
    db: firestore.Client = Depends(deps.get_db),
    current_user: schemas.User = Depends(deps.get_current_user)
):
    if not current_user.is_senior:
         raise HTTPException(status_code=403, detail="Only seniors can create groups")
    return crud.create_group(db=db, group=group, user_id=current_user.id)

@app.get("/groups/", response_model=List[schemas.Group])
def read_groups(skip: int = 0, limit: int = 100, db: firestore.Client = Depends(deps.get_db)):
    return crud.get_groups(db, skip=skip, limit=limit)

@app.post("/groups/{group_id}/messages/", response_model=schemas.Message)
def create_message_for_group(
    group_id: str, 
    message: schemas.MessageBase, 
    db: firestore.Client = Depends(deps.get_db),
    current_user: schemas.User = Depends(deps.get_current_user)
):
    if message.group_id != group_id:
        raise HTTPException(status_code=400, detail="Group ID mismatch")
    
    return crud.create_message(db=db, message=message, sender_id=current_user.id)

@app.get("/groups/{group_id}/messages/", response_model=List[schemas.Message])
def read_messages(group_id: str, db: firestore.Client = Depends(deps.get_db)):
    return crud.get_messages(db, group_id=group_id)
