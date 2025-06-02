import os
from typing import Optional
from PyPDF2 import PdfReader
from core.logger import get_logger
from core.settings import ROOT_DIR

logger = get_logger(__name__, log_file="ingestion.log")

class FileIngestion:
    def __init__(self):
        """Initialize the file ingestion handler"""
        self.data_dir = os.path.join(ROOT_DIR, "data")
        os.makedirs(self.data_dir, exist_ok=True)
    
    def save_uploaded_file(self, file_content: bytes, filename: str) -> str:
        """
        Save an uploaded file to the data directory.
        
        Args:
            file_content: The content of the uploaded file
            filename: Original filename
            
        Returns:
            str: Path to the saved file
        """
        try:
            # Ensure filename is safe
            safe_filename = os.path.basename(filename)
            filepath = os.path.join(self.data_dir, safe_filename)
            
            # Save the file
            with open(filepath, 'wb') as f:
                f.write(file_content)
            
            logger.info(f"Successfully saved uploaded file to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving uploaded file: {str(e)}")
            raise
    
    def extract_text_from_pdf(self, filepath: str) -> Optional[str]:
        """
        Extract text content from a PDF file.
        
        Args:
            filepath: Path to the PDF file
            
        Returns:
            Optional[str]: Extracted text or None if extraction fails
        """
        try:
            logger.info(f"Extracting text from PDF: {filepath}")
            
            with open(filepath, 'rb') as file:
                pdf_reader = PdfReader(file)
                text = ""
                
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                
                if text.strip():
                    logger.info(f"Successfully extracted text from PDF: {filepath}")
                    return text.strip()
                else:
                    logger.warning(f"No text content found in PDF: {filepath}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error extracting text from PDF {filepath}: {str(e)}")
            return None
    
    def extract_text_from_txt(self, filepath: str) -> Optional[str]:
        """
        Extract text content from a TXT file.
        
        Args:
            filepath: Path to the TXT file
            
        Returns:
            Optional[str]: Extracted text or None if extraction fails
        """
        try:
            logger.info(f"Extracting text from TXT file: {filepath}")
            
            with open(filepath, 'r', encoding='utf-8') as file:
                text = file.read()
                
            if text.strip():
                logger.info(f"Successfully extracted text from TXT file: {filepath}")
                return text.strip()
            else:
                logger.warning(f"No text content found in TXT file: {filepath}")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting text from TXT file {filepath}: {str(e)}")
            return None
    
    def process_file(self, file_content: bytes, filename: str) -> Optional[str]:
        """
        Process an uploaded file and extract its text content.
        
        Args:
            file_content: The content of the uploaded file
            filename: Original filename
            
        Returns:
            Optional[str]: Extracted text or None if processing fails
        """
        try:
            # Save the uploaded file
            filepath = self.save_uploaded_file(file_content, filename)
            
            # Extract text based on file type
            if filename.lower().endswith('.pdf'):
                text = self.extract_text_from_pdf(filepath)
            elif filename.lower().endswith('.txt'):
                text = self.extract_text_from_txt(filepath)
            else:
                logger.error(f"Unsupported file type: {filename}")
                return None
            
            if text:
                # Save the extracted text to a new TXT file
                txt_filename = os.path.splitext(filename)[0] + '.txt'
                txt_filepath = os.path.join(self.data_dir, txt_filename)
                
                with open(txt_filepath, 'w', encoding='utf-8') as f:
                    f.write(text)
                
                logger.info(f"Successfully saved extracted text to {txt_filepath}")
                return text
            
            return None
            
        except Exception as e:
            logger.error(f"Error processing file {filename}: {str(e)}")
            return None 