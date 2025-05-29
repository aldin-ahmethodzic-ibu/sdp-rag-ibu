from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from .auth import (
    create_access_token,
    get_current_user,
    authenticate_user,
)
from data_model.mongo_db.db import init_db
from data_model.pydantic_models.auth import Token, User
from data_model.mongo_db.schemas.user import User as DBUser

app = FastAPI(title="SDP RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.on_event("startup")
async def startup_event():
    await init_db()

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: DBUser = Depends(get_current_user)):
    return User(
        user_id=current_user.user_id,
        user_type=current_user.user_type,
        email=current_user.email,
        username=current_user.username,
        disabled=current_user.disabled
    )

@app.get("/")
async def root():
    return {"message": "Welcome to SDP RAG API"}
