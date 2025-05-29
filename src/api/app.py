from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from .auth import (
    create_access_token,
    get_current_user,
    authenticate_user,
    get_password_hash,
    get_user,
)
from data_model.mongo_db.db import init_db
from data_model.pydantic_models.auth import Token, User, UserCreate
from data_model.mongo_db.schemas.user import User as DBUser

app = FastAPI(title="SDP RAG API")

app.swagger_ui_init_oauth = {
    "usePkceWithAuthorizationCodeGrant": True
}

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version="1.0.0",
        description="SDP RAG API",
        routes=app.routes,
    )
    
    openapi_schema["components"] = {
        "securitySchemes": {
            "Bearer": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
    }
    
    openapi_schema["security"] = [{"Bearer": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

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

@app.post("/register", response_model=User)
async def register_user(user_data: UserCreate):
    # Check if username already exists
    if await get_user(user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = DBUser(
        user_id=await DBUser.count() + 1,
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        user_type=user_data.user_type,
    )
    await db_user.insert()
    
    return User(
        user_id=db_user.user_id,
        user_type=db_user.user_type,
        email=db_user.email,
        username=db_user.username,
        disabled=False
    )

@app.get("/")
async def root():
    return {"message": "Welcome to SDP RAG API"}
