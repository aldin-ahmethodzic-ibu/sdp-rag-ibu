from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
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
from data_ingestion.web_scraper import URLIngestion
from data_ingestion.vespa_ingestion import DocumentIngestion
from data_ingestion.file_processor import FileIngestion
from core.logger import get_logger
from core.utils import delete_temporary_files
from src.chatbot import Chatbot
import uuid

app = FastAPI(title="SDP RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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

@app.post("/ingest-file")
async def ingest_file(
    file: UploadFile = File(...),
    current_user: DBUser = Depends(get_current_user)
):
    """
    Ingest content from an uploaded PDF or TXT file into the Vespa vector database.
    Only users with admin privileges can access this endpoint.
    
    Args:
        file: The uploaded file (PDF or TXT)
        current_user: Current authenticated user
        
    Returns:
        dict: Status message and file information
        
    Raises:
        HTTPException: If user is not an admin or if ingestion fails
    """
    # Only admin users can ingest files
    if current_user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can ingest files"
        )
    
    # Check file type
    if not file.filename.lower().endswith(('.pdf', '.txt')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF and TXT files are supported"
        )
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Initialize ingestion classes
        file_ingestion = FileIngestion()
        doc_ingestion = DocumentIngestion()
        
        # Process file and extract text
        text = file_ingestion.process_file(file_content, file.filename)
        
        if not text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract text from file"
            )
        
        # Ingest document into Vespa
        doc_ingestion.ingest_documents()
        
        # Clean up temporary files
        delete_temporary_files()
        
        return {
            "status": "success",
            "message": "File successfully ingested into Vespa",
            "filename": file.filename
        }
        
    except Exception as e:
        logger.error(f"Error during file ingestion: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: DBUser = Depends(get_current_user)
):
    """
    Chat with the RAG-powered IBU chatbot.
    
    Args:
        request: Chat request containing the user's question and optional session_id
        current_user: Current authenticated user
        
    Returns:
        ChatResponse: The chatbot's answer and session ID
        
    Raises:
        HTTPException: If chat processing fails
    """
    try:
        if not hasattr(app, 'chatbot'):
            app.chatbot = Chatbot()
            
        # Use provided session_id or create new session
        session_id = request.session_id
        if not session_id:
            session_id = str(uuid.uuid4())
            session = Session(
                session_id=session_id,
                user_id=str(current_user.user_id),
                messages=[
                    Message(content=request.question, role="user")
                ]
            )
            await session.insert()
        else:
            # Get existing session
            session = await Session.find_one(Session.session_id == session_id)
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found"
                )
            # Verify session belongs to user
            if session.user_id != str(current_user.user_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this session"
                )
            # Append new message
            session.messages.append(Message(content=request.question, role="user"))
            await session.save()
        
        # Get answer from chatbot
        answer = app.chatbot.get_answer(request.question, session_id)
        
        # Append assistant's response to session
        session.messages.append(Message(content=answer, role="assistant"))
        await session.save()
        
        return ChatResponse(
            answer=answer,
            session_id=session_id
        )
        
    except Exception as e:
        error_msg = f"Error during chat: {type(e).__name__}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": error_msg,
                "type": type(e).__name__,
                "message": str(e) if str(e) else "Unknown error occurred"
            }
        )

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

@app.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: DBUser = Depends(get_current_user)
):
    """
    Delete a specific chat session.
    
    Args:
        session_id: ID of the session to delete
        current_user: Current authenticated user
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If session not found or user not authorized
    """
    try:
        # Find the session
        session = await Session.find_one(Session.session_id == session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
            
        # Verify session belongs to user
        if session.user_id != str(current_user.user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this session"
            )
            
        # Delete the session
        await session.delete()
        
        return {
            "status": "success",
            "message": f"Session {session_id} successfully deleted"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error deleting session: {type(e).__name__}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": error_msg,
                "type": type(e).__name__,
                "message": str(e) if str(e) else "Unknown error occurred"
            }
        )
