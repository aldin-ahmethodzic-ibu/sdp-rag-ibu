from dotenv import load_dotenv
import os

load_dotenv()

ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
SECRET_KEY = os.environ.get("SECRET_KEY")

VESPA_HOST = os.environ.get("VESPA_HOST")
VESPA_PORT = os.environ.get("VESPA_PORT")
