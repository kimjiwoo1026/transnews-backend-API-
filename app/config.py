import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):
        self.LLM_SERVER_URL: str = os.getenv("LLM_SERVER_URL", "").rstrip("/")
        self.LLM_SUMMARY_PATH: str = os.getenv("LLM_SUMMARY_PATH", "/summary")
        self.LLM_TRANSLATE_PATH: str = os.getenv("LLM_TRANSLATE_PATH", "/translate")
        self.REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "15"))
        self.APP_NAME: str = os.getenv("APP_NAME", "TransNews Backend API")
        self.APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()