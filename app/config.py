import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        self.MAIN_SERVER_URL: str = os.getenv("MAIN_SERVER_URL", "").rstrip("/")
        self.REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "15"))
        self.APP_NAME: str = os.getenv("APP_NAME", "TransNews Backend API")
        self.APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
        self.NAVER_CLIENT_ID: str = os.getenv("NAVER_CLIENT_ID", "")
        self.NAVER_CLIENT_SECRET: str = os.getenv("NAVER_CLIENT_SECRET", "")

settings = Settings()