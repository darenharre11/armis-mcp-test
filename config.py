import os
from dotenv import load_dotenv

load_dotenv()

ARMIS_API_KEY = os.getenv("ARMIS_API_KEY")
ARMIS_MCP_URL = os.getenv("ARMIS_MCP_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")


def validate():
    """Validate required configuration is present."""
    missing = []
    if not ARMIS_API_KEY:
        missing.append("ARMIS_API_KEY")
    if not ARMIS_MCP_URL:
        missing.append("ARMIS_MCP_URL")
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
