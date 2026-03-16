import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    LLM_SERVER_URL: str = os.getenv("LLM_SERVER_URL", "").rstrip("/")
    LLM_SUMMARY_PATH: str = os.getenv("LLM_SUMMARY_PATH", "/summary")
    LLM_TRANSLATE_PATH: str = os.getenv("LLM_TRANSLATE_PATH", "/translate")
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "15"))


settings = Settings()