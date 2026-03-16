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

        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
                response = await client.post(target_url, json=payload)
                response.raise_for_status()
                result = response.json()

            summary = result.get("summary")
            if not summary:
                raise ValueError("Missing 'summary' in LLM server response")

            return summary

        except Exception as e:
            logger.error("Summary proxy request failed: %s", str(e))
            raise

    async def translate(self, text: str, target_lang: str = "en") -> str:
        if not settings.LLM_SERVER_URL:
            raise ValueError("LLM_SERVER_URL is not configured")

        target_url = f"{settings.LLM_SERVER_URL}{settings.LLM_TRANSLATE_PATH}"
        payload = {
            "text": text,
            "target_lang": target_lang,
        }

        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
                response = await client.post(target_url, json=payload)
                response.raise_for_status()
                result = response.json()

            translated_text = result.get("translated_text")
            if not translated_text:
                raise ValueError("Missing 'translated_text' in LLM server response")

            return translated_text

        except Exception as e:
            logger.error("Translate proxy request failed: %s", str(e))
            raise