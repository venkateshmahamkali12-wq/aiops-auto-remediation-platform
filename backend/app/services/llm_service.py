import os
import logging

from openai import OpenAI, APIConnectionError, RateLimitError, APIStatusError

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def ask_llm(prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a senior DevOps AI assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content
    except APIConnectionError:
        logger.exception("Failed to connect to OpenAI API")
        raise RuntimeError("Unable to reach the LLM service. Please try again later.")
    except RateLimitError:
        logger.exception("OpenAI rate limit exceeded")
        raise RuntimeError("LLM rate limit exceeded. Please wait and try again.")
    except APIStatusError as exc:
        logger.exception("OpenAI API error: %s", exc.status_code)
        raise RuntimeError(f"LLM service returned an error (status {exc.status_code}).")
