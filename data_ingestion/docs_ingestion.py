import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any
import glob
import hashlib

from langchain.text_splitter import RecursiveCharacterTextSplitter
from core.logger import get_logger
from core.settings import ROOT_DIR, VESPA_HOST, VESPA_PORT
from data_ingestion.embedder import Embedder
from data_model.vespa_ai.vespa_client import VespaClient

logger = get_logger(__name__, log_file="ingestion.log")

class DocumentIngestion:
    def __init__(self):
        """Initialize the document ingestion with Vespa client and embedder"""
        self.vespa_client = VespaClient(vespa_host=VESPA_HOST, vespa_port=VESPA_PORT)
        self.embedder = Embedder()
        self.data_dir = os.path.join(ROOT_DIR, "data")
        
        self.chunk_size = 1000
        self.chunk_overlap = 200
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )
    
    def get_files_to_ingest(self) -> List[str]:
        """Get list of all text files in the data directory"""
        try:
            # Find all .txt files in data directory
            txt_files = glob.glob(os.path.join(self.data_dir, "*.txt"))
            logger.info(f"Found {len(txt_files)} text files in data directory")
            return txt_files
        except Exception as e:
            logger.error(f"Error getting files to ingest: {str(e)}")
            raise
    
    def read_file(self, file_path: str) -> str:
        """Read content from a file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.info(f"Successfully read file: {file_path}")
            return content
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            raise
    
    def create_resource_document(self, file_path: str, content: str) -> Dict[str, Any]:
        """Create a resource document for the Vespa resources schema"""
        try:
            resource_id = hashlib.md5(content.encode('utf-8')).hexdigest()
            
            # Extract title from filename
            filename = os.path.basename(file_path)
            title = os.path.splitext(filename)[0]
            
            # Generate embedding for the whole content
            logger.info(f"Generating embedding for resource: {title}")
            embedding = self.embedder.openai_embedding(content)
            
            metadata = {
                "source": file_path,
                "file_type": "text",
                "file_size": len(content)
            }
            
            resource_doc = {
                "id": resource_id,
                "fields": {
                    "resource_id": resource_id,
                    "title": title,
                    "resource_text": content,
                    "embedding": embedding,
                    "metadata": json.dumps(metadata)
                }
            }
            
            logger.info(f"Created resource document for {title} with ID: {resource_id}")
            return resource_doc
        except Exception as e:
            logger.error(f"Error creating resource document for {file_path}: {str(e)}")
            raise
    
    def chunk_document(self, resource_id: str, content: str) -> List[Dict[str, Any]]:
        """Split document into chunks using LangChain's RecursiveCharacterTextSplitter"""
        try:
            # Split the text into chunks
            logger.info(f"Splitting document with resource_id {resource_id} into chunks")
            chunks = self.text_splitter.split_text(content)
            logger.info(f"Document split into {len(chunks)} chunks")
            
            chunk_documents = []
            
            # Process each chunk
            for i, chunk_text in enumerate(chunks):
                chunk_id = hashlib.md5(f"{resource_id}{chunk_text}".encode('utf-8')).hexdigest()
                
                logger.info(f"Generating embedding for chunk {i+1}/{len(chunks)}")
                embedding = self.embedder.openai_embedding(chunk_text)
                
                metadata = {
                    "chunk_index": i,
                    "parent_resource_id": resource_id
                }
                
                chunk_doc = {
                    "id": chunk_id,
                    "fields": {
                        "chunk_id": chunk_id,
                        "resource_id": resource_id,
                        "chunk_text": chunk_text,
                        "embedding": embedding,
                        "metadata": json.dumps(metadata)
                    }
                }
                
                chunk_documents.append(chunk_doc)
            
            return chunk_documents
        except Exception as e:
            logger.error(f"Error chunking document {resource_id}: {str(e)}")
            raise
    
    def ingest_documents(self):
        """Ingest all documents from the data directory into Vespa"""
        try:
            # Get all files to ingest
            files = self.get_files_to_ingest()
            
            for file_path in files:
                logger.info(f"Processing file: {file_path}")
                
                content = self.read_file(file_path)
                
                # Create a resource document and insert it into Vespa
                resource_doc = self.create_resource_document(file_path, content)
                resource_id = resource_doc["id"]
                
                logger.info(f"Inserting resource document into Vespa: {resource_id}")
                self.vespa_client.insert_one("resources", resource_doc)
                
                # Insert chunks into Vespa
                chunk_docs = self.chunk_document(resource_id, content)
                
                logger.info(f"Inserting {len(chunk_docs)} chunk documents into Vespa")
                self.vespa_client.insert_many("chunks", chunk_docs)
                
                logger.info(f"Successfully processed and ingested file: {file_path}")
            
            logger.info(f"Document ingestion complete. Processed {len(files)} files")
        except Exception as e:
            logger.error(f"Error during document ingestion: {str(e)}")
            raise

if __name__ == "__main__":
    # Run the document ingestion
    ingestion = DocumentIngestion()
    ingestion.ingest_documents()