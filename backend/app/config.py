import os

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-nano")
MOCK_PAYMENTS = os.getenv("MOCK_PAYMENTS", "true").lower() == "true"
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./quorum.db")
