# TransNews Backend API

키워드 기반 뉴스 검색과 기사 본문 크롤링/요약, 한→영 번역을 하나의 FastAPI 앱으로 통합한 프로젝트

---

# 프로젝트 구조
```
TRANSNEWS-BACKEND_API
│
├─ app
│  ├─ main.py
│  ├─ config.py
│  │
│  ├─ routers
│  │   ├─ news_router.py
│  │   ├─ crawl_router.py
│  │   └─ pipeline_router.py
│  │
│  ├─ services
│  │   ├─ rss_service.py
│  │   ├─ crawler_service.py
│  │   └─ llm_proxy_service.py
│  │
│  └─ schemas
│      └─ models.py
│
├─ .env
├─ requirements.txt
└─ README.md
```

Client -> FastAPI Backend ->LLM Server

-------
# tech stack

Backend Framework- FastAPI, Python 3.11
Data Processing- BeautifulSoup4, Feedparser
HTTP Client- HTTPX
환경 변수 관리- python-dotenv

-----------
# 설정
루트 디렉토리에 .env 파일을 생성합니다. LLM 서버는 뉴스 요약 및 번역 처리를 담당합니다.
```
LLM_SERVER_URL=http://127.0.0.1:8001
LLM_SUMMARY_PATH=/summary
LLM_TRANSLATE_PATH=/translate
REQUEST_TIMEOUT=15
```
----------
# 설치
### 1. 저장소 클론
```bash
git clone https://github.com/kimjiwoo1026/transnews-backend-API-.git
cd transnews-backend-API-
```

### 2. 가상환경 생성
```bash
python -m venv venv
```

### 3. 가상환경 활성화

Windows
```bash
venv\Scripts\activate
```

Mac / Linux
```bash
source venv/bin/activate
```

### 4. 패키지 설치
```bash
pip install -r requirements.txt
```

---

# 실행 방법

### FastAPI 서버 실행
```bash
uvicorn app.main:app --reload
```

### API 문서 확인
브라우저에서 아래 주소 접속

```
http://127.0.0.1:8000/docs
```




