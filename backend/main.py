from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
import traceback
import sys
import os

app = FastAPI(title="College Share API", root_path="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper for Lazy Loading to avoid startup crashes
def get_backend_modules():
    # Adjust path
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    try:
        from backend import schemas, auth, crud, deps, database
        return schemas, auth, crud, deps, database
    except ImportError:
        try:
             import schemas, auth, crud, deps, database
             return schemas, auth, crud, deps, database
        except Exception as e:
            raise RuntimeError(f"Failed to import backend modules: {e}")

@app.get("/health")
def health_check():
    try:
        schemas, auth, crud, deps, database = get_backend_modules()
        
        if database.init_error:
            return {"status": "error", "detail": f"DB Init Error: {database.init_error}"}
        if not database.db:
            return {"status": "error", "detail": "Database client is None (Auth details might be wrong)"}
        return {"status": "ok", "message": "Backend is online"}
    except Exception as e:
        return {"status": "CRITICAL_ERROR", "detail": str(e), "traceback": traceback.format_exc()}

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    schemas, auth, crud, deps, database = get_backend_modules()
    # Manual dependency injection for DB to avoid complex Depends() in lazy load
    # We call deps.get_db manually or use a wrapper? 
    # To keep FastAPI's Depends magic working, we should define 'deps' globally if possible, 
    # but deps imports schemas... circular risk if we are lazy loading.
    # Strategy: Use local imports for the types, but we need Depends() to work.
    
    # Actually, if we lazy load inside the route, FastAPI's `response_model=schemas.Token` fails at startup 
    # because `schemas` is not defined.
    # SOLUTION: Remove response_model from decorator or use forward references?
    # Simpler: We just return dicts.
    pass # logic below
    
    # Wait, simple lazy load is hard with FastAPI decorators using Pydantic models.
    # We will try to import top-level wrapped in try/except but JUST the modules.
    
# ... Rethinking strategy inline to ensure stability ...
# If imports fail at top level, Vercel crashes. 
# We MUST try global import but catch it securely.

startup_error = None
schemas = None
auth = None
crud = None
deps = None
database = None
firestore = None

try:
    from google.cloud import firestore
    # Try absolute import 
    try:
        from backend import schemas, auth, crud, deps, database
    except ImportError:
        import schemas, auth, crud, deps, database
except Exception as e:
    startup_error = f"{str(e)}\n{traceback.format_exc()}"

# If startup_error exists, we define a "broken" app that just reports it.
# If not, we define the real app.

if startup_error:
    @app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE"])
    async def catch_all(path_name: str, request: Request):
        return JSONResponse(
            status_code=500,
            content={
                "status": "STARTUP_CRASH",
                "error": startup_error.split("\n")
            }
        )
else:
    # Real Routes
    @app.post("/token") # Removed response_model to avoid potential issues if schemas is partial
    async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db=Depends(deps.get_db)):
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

    @app.post("/users/")
    def create_user(user: schemas.UserCreate, db=Depends(deps.get_db)):
        # checking username via deps/crud
        db_user = crud.get_user_by_username(db, username=user.username)
        if db_user:
            raise HTTPException(status_code=400, detail="Username already registered")
        return crud.create_user(db=db, user=user)

    @app.get("/users/me")
    async def read_users_me(current_user=Depends(deps.get_current_user)):
        return current_user

    @app.post("/groups/")
    def create_group(group: schemas.GroupCreate, db=Depends(deps.get_db), current_user=Depends(deps.get_current_user)):
        if not current_user.is_senior:
             raise HTTPException(status_code=403, detail="Only seniors can create groups")
        return crud.create_group(db=db, group=group, user_id=current_user.id)

    @app.get("/groups/")
    def read_groups(skip: int = 0, limit: int = 100, db=Depends(deps.get_db)):
        return crud.get_groups(db, skip=skip, limit=limit)

    @app.post("/groups/{group_id}/messages/")
    def create_message_for_group(group_id: str, message: schemas.MessageBase, db=Depends(deps.get_db), current_user=Depends(deps.get_current_user)):
        if message.group_id != group_id:
            raise HTTPException(status_code=400, detail="Group ID mismatch")
        return crud.create_message(db=db, message=message, sender_id=current_user.id)

    @app.get("/groups/{group_id}/messages/")
    def read_messages(group_id: str, db=Depends(deps.get_db)):
        return crud.get_messages(db, group_id=group_id)


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
