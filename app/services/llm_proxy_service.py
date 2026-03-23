import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class LLMProxyService:
    async def summarize(self, text: str) -> str:
        if not settings.LLM_SERVER_URL:
            raise ValueError("LLM_SERVER_URL is not configured")

        target_url = f"{settings.LLM_SERVER_URL}{settings.LLM_SUMMARY_PATH}"
        payload = {"text": text}

        logger.info("요약 요청 시작 - url=%s", target_url)

        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
                response = await client.post(target_url, json=payload)
                response.raise_for_status()
                result = response.json()

            summary = result.get("summary")
            if not summary:
                raise ValueError("Missing 'summary' in LLM server response")

            logger.info("요약 요청 성공 - url=%s", target_url)
            return summary

        except httpx.HTTPStatusError as e:
            logger.warning(
                "요약 요청 HTTP 오류 - url=%s, status=%s",
                target_url,
                e.response.status_code,
            )
            raise
        except httpx.RequestError as e:
            logger.warning(
                "요약 요청 네트워크 오류 - url=%s, error=%s",
                target_url,
                str(e),
            )
            raise
        except ValueError as e:
            logger.warning(
                "요약 응답 데이터 오류 - url=%s, error=%s",
                target_url,
                str(e),
            )
            raise
        except Exception:
            logger.exception("요약 프록시 처리 중 예기치 못한 오류 - url=%s", target_url)
            raise

    async def translate(self, text: str, target_lang: str = "en") -> str:
        if not settings.LLM_SERVER_URL:
            raise ValueError("LLM_SERVER_URL is not configured")

        target_url = f"{settings.LLM_SERVER_URL}{settings.LLM_TRANSLATE_PATH}"
        payload = {
            "text": text,
            "target_lang": target_lang,
        }

        logger.info("번역 요청 시작 - url=%s, target_lang=%s", target_url, target_lang)

        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
                response = await client.post(target_url, json=payload)
                response.raise_for_status()
                result = response.json()

            translated_text = result.get("translated_text")
            if not translated_text:
                raise ValueError("Missing 'translated_text' in LLM server response")

            logger.info("번역 요청 성공 - url=%s, target_lang=%s", target_url, target_lang)
            return translated_text

        except httpx.HTTPStatusError as e:
            logger.warning(
                "번역 요청 HTTP 오류 - url=%s, status=%s",
                target_url,
                e.response.status_code,
            )
            raise
        except httpx.RequestError as e:
            logger.warning(
                "번역 요청 네트워크 오류 - url=%s, error=%s",
                target_url,
                str(e),
            )
            raise
        except ValueError as e:
            logger.warning(
                "번역 응답 데이터 오류 - url=%s, error=%s",
                target_url,
                str(e),
            )
            raise
        except Exception:
            logger.exception(
                "번역 프록시 처리 중 예기치 못한 오류 - url=%s, target_lang=%s",
                target_url,
                target_lang,
            )
            raise