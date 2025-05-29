from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from src.api.auth import (
    create_access_token,
    get_current_user,
    authenticate_user,
    get_password_hash,
    get_user,
)
from data_model.mongo_db.db import init_db
from data_model.pydantic_models.auth import Token, User, UserCreate
from data_model.pydantic_models.chat import ChatRequest, ChatResponse, SessionResponse
from data_model.mongo_db.schemas.user import User as DBUser
from data_model.mongo_db.schemas.session import Session, Message
from data_ingestion.url_to_txt import URLIngestion
from data_ingestion.docs_ingestion import DocumentIngestion
from core.logger import get_logger
from core.utils import delete_temporary_files
from src.chatbot import Chatbot
import uuid

app = FastAPI(title="SDP RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
logger = get_logger(__name__, log_file="ingestion.log")

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
    if await get_user(user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
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

@app.post("/ingest-urls")
async def ingest_urls(urls: List[str], current_user: DBUser = Depends(get_current_user)):
    """
    Ingest content from a list of URLs into the Vespa vector database.
    Only users with admin privileges can access this endpoint.
    
    Args:
        urls: List of URLs to scrape and ingest
        current_user: Current authenticated user
        
    Returns:
        dict: Status message and list of processed URLs
        
    Raises:
        HTTPException: If user is not an admin or if ingestion fails
    """
    # Only admin users can ingest URLs
    if current_user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can ingest URLs"
        )
        
    try:
        # Initialize ingestion classes
        url_ingestion = URLIngestion()
        doc_ingestion = DocumentIngestion()
        
        # Process URLs and save to text files
        url_ingestion.process_urls(urls)
        
        # Ingest documents into Vespa
        doc_ingestion.ingest_documents()
        
        # Clean up temporary files
        delete_temporary_files()
        
        return {
            "status": "success",
            "message": "URLs successfully ingested into Vespa",
            "processed_urls": urls
        }
        
    except Exception as e:
        logger.error(f"Error during URL ingestion: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Ensure the webdriver is closed
        if 'url_ingestion' in locals():
            url_ingestion.driver.quit()

@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: DBUser = Depends(get_current_user)
):
    """
    Chat with the RAG-powered IBU chatbot.
    
    Args:
        request: Chat request containing the user's question
        current_user: Current authenticated user
        
    Returns:
        ChatResponse: The chatbot's answer and session ID
        
    Raises:
        HTTPException: If chat processing fails
    """
    try:
        if not hasattr(app, 'chatbot'):
            app.chatbot = Chatbot()
            
        session_id = str(uuid.uuid4())
        
        answer = app.chatbot.get_answer(request.question, session_id)
        
        session = Session(
            session_id=session_id,
            user_id=str(current_user.user_id),
            messages=[
                Message(content=request.question, role="user"),
                Message(content=answer, role="assistant")
            ]
        )
        await session.insert()
        
        return ChatResponse(
            answer=answer,
            session_id=session_id
        )
        
    except Exception as e:
        logger.error(f"Error during chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions", response_model=List[SessionResponse])
async def get_sessions(current_user: DBUser = Depends(get_current_user)):
    """
    Get all chat sessions for the authenticated user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        List[SessionResponse]: List of all sessions with their messages
        
    Raises:
        HTTPException: If session retrieval fails
    """
    try:
        sessions = await Session.find(
            Session.user_id == str(current_user.user_id)
        ).sort(-Session.created_at).to_list()
        
        return sessions
        
    except Exception as e:
        error_msg = f"Error retrieving sessions: {type(e).__name__}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": error_msg,
                "type": type(e).__name__,
                "message": str(e) if str(e) else "Unknown error occurred"
            }
        )
