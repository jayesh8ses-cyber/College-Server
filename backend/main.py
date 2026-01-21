from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from . import models, database, schemas, auth, crud, deps
from typing import List

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="College Share API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(deps.get_db)):
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
def create_user(user: schemas.UserCreate, db: Session = Depends(deps.get_db)):
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return crud.create_user(db=db, user=user)

@app.get("/users/me", response_model=schemas.User)
async def read_users_me(current_user: models.User = Depends(deps.get_current_user)):
    return current_user

@app.post("/groups/", response_model=schemas.Group)
def create_group(
    group: schemas.GroupCreate, 
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    # Only seniors can create groups? Project requirement said "any college senior could create a group"
    # Assuming is_senior checks are enforced here if strict, or let anyone create for now.
    # Let's enforce it for fun/correctness based on prompt.
    if not current_user.is_senior:
         raise HTTPException(status_code=403, detail="Only seniors can create groups")
    return crud.create_group(db=db, group=group, user_id=current_user.id)

@app.get("/groups/", response_model=List[schemas.Group])
def read_groups(skip: int = 0, limit: int = 100, db: Session = Depends(deps.get_db)):
    return crud.get_groups(db, skip=skip, limit=limit)

@app.post("/groups/{group_id}/messages/", response_model=schemas.Message)
def create_message_for_group(
    group_id: int, 
    message: schemas.MessageBase, 
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    db_message = models.Message(**message.dict(), sender_id=current_user.id) # group_id is in message base or passed?
    # MessageBase has group_id, but usually we take it from URL.
    # Let's override/ensure consistency
    if message.group_id != group_id:
        raise HTTPException(status_code=400, detail="Group ID mismatch")
    
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

@app.get("/groups/{group_id}/messages/", response_model=List[schemas.Message])
def read_messages(group_id: int, db: Session = Depends(deps.get_db)):
    return db.query(models.Message).filter(models.Message.group_id == group_id).all()
