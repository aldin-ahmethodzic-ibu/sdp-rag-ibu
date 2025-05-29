from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from core.settings import MONGO_URI, DATABASE_NAME
from data_model.mongo_db.schemas.user import User
from data_model.mongo_db.schemas.session import Session

async def init_db():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DATABASE_NAME]
    await init_beanie(database=db, document_models=[User, Session])