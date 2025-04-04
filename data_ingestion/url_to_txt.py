from bs4 import BeautifulSoup
from typing import List, Optional
from core.config import URLS_TO_SCRAPE
from core.logger import get_logger
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time
from core.settings import ROOT_DIR
import os

logger = get_logger(__name__, log_file="ingestion.log")

class URLIngestion:
    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
    def extract_text_from_url(self, url: str) -> Optional[str]:
        """
        Extract text content from a given URL using Selenium and BeautifulSoup.

        :param url: URL to extract text from
        :return: Extracted text or None if extraction fails
        """
        try:
            logger.info(f"Attempting to extract text from URL: {url}")
            
            # Wait for the dynamic content to load before scraping
            self.driver.get(url)
            
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            time.sleep(3)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text and clean it
            text = soup.get_text(separator='\n', strip=True)
            
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            text = '\n'.join(lines)
            
            if text:
                logger.info(f"Successfully extracted text from URL: {url}")
                return text
            else:
                logger.warning(f"No text content found at URL: {url}")
                return None
            
        except Exception as e:
            logger.error(f"Error extracting text from URL {url}: {str(e)}")
            return None

    def process_urls(self, urls: List[str] = URLS_TO_SCRAPE) -> None:
        """
        Process a list of URLs and extract text from each one.

        :param urls: List of URLs to process. Defaults to URLS_TO_SCRAPE from config
        """
        logger.info(f"Starting to process {len(urls)} URLs")
        
        try:
            for url in urls:
                text = self.extract_text_from_url(url)
                if text:
                    # Create a filename from the URL
                    filename = url.split('/')[-1] or 'index'
                    filename = f"{filename}.txt"
                    
                    data_dir = os.path.join(ROOT_DIR, "data")
                    os.makedirs(data_dir, exist_ok=True)
                    filepath = os.path.join(data_dir, filename)
                    
                    # Save the text to file
                    try:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(text)
                        logger.info(f"Successfully saved extracted text to {filepath}")
                    except Exception as e:
                        logger.error(f"Failed to save text to file {filepath}: {str(e)}")
        finally:
            self.driver.quit()

if __name__ == "__main__":
    # Run the URL ingestion
    url_ingestion = URLIngestion()
    url_ingestion.process_urls()