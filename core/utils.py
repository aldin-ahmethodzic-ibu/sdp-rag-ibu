import os
from core.settings import ROOT_DIR
from core.logger import get_logger

logger = get_logger(__name__, log_file="utils.log")

def delete_temporary_files():
    """
    Delete all temporary .txt and .pdf files from the data directory.
    """
    try:
        data_dir = os.path.join(ROOT_DIR, "data")
        if not os.path.exists(data_dir):
            logger.warning(f"Data directory {data_dir} does not exist")
            return

        deleted_files = []
        for file in os.listdir(data_dir):
            if file.endswith((".txt", ".pdf")):
                file_path = os.path.join(data_dir, file)
                os.remove(file_path)
                deleted_files.append(file_path)
                logger.info(f"Deleted temporary file: {file_path}")
        
        if deleted_files:
            logger.info(f"Successfully deleted {len(deleted_files)} temporary files")
        else:
            logger.info("No temporary files found to delete")
            
    except Exception as e:
        logger.error(f"Error deleting temporary files: {str(e)}")
        raise 