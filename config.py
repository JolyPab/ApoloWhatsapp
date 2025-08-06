import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Twilio Configuration
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')
    LEAD_NOTIFICATION_NUMBER = os.environ.get('LEAD_NOTIFICATION_NUMBER')

    # Redis Configuration
    REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
    REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD")
    REDIS_USERNAME = os.environ.get("REDIS_USERNAME", "default")
    
    # Azure OpenAI Configuration
    AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY")
    OPENAI_API_VERSION = os.environ.get("OPENAI_API_VERSION", "2023-05-15")
    AZURE_OPENAI_DEPLOYMENT_NAME = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME")
    
    # Azure Embeddings Configuration
    AZURE_EMBEDDINGS_ENDPOINT = os.environ.get("AZURE_EMBEDDINGS_ENDPOINT")
    AZURE_EMBEDDINGS_API_KEY = os.environ.get("AZURE_EMBEDDINGS_API_KEY")
    AZURE_EMBEDDINGS_DEPLOYMENT_NAME = os.environ.get("AZURE_EMBEDDINGS_DEPLOYMENT_NAME", "text-embedding-ada-002")

    # Vector Store Configuration
    FAISS_INDEX_PATH = os.environ.get("FAISS_INDEX_PATH", "apolo_faiss")
    
    # Logging
    LOGGING_LEVEL = os.environ.get("LOGGING_LEVEL", "INFO").upper()

settings = Settings() 
