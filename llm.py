"""
llm.py — OpenAI API wrapper

Single responsibility: send a prompt to OpenAI and return the text response.
All retry logic, error formatting, and model config lives here so the rest of
the app never imports openai directly.
"""

import time
import openai
from dotenv import load_dotenv

load_dotenv()

MODEL = "gpt-4o"
MAX_TOKENS = 1000
MAX_RETRIES = 2
RETRY_DELAY = 2  # seconds between retries on overload


def call_llm(
    messages: list[dict],
    system_prompt: str = "",
    temperature: float = 0.7,
) -> str:
    """
    Call the OpenAI Chat Completions API.

    Args:
        messages:      List of {"role": "user"|"assistant", "content": str}
        system_prompt: Optional system message prepended to the conversation
        temperature:   Sampling temperature (0.0–1.0)

    Returns:
        The assistant's response as a plain string.

    Raises:
        RuntimeError with a user-friendly message on failure.
    """
    full_messages = []
    if system_prompt:
        full_messages.append({"role": "system", "content": system_prompt})
    full_messages.extend(messages)

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = openai.chat.completions.create(
                model=MODEL,
                messages=full_messages,
                max_tokens=MAX_TOKENS,
                temperature=temperature,
            )
            return response.choices[0].message.content.strip()

        except openai.RateLimitError:
            raise RuntimeError(
                "⚠️ Rate limit reached — wait a moment and try again."
            )
        except openai.APIStatusError as e:
            if e.status_code == 529 and attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            raise RuntimeError(
                f"⚠️ API error ({e.status_code}) — please try again."
            )
        except openai.APIConnectionError:
            raise RuntimeError(
                "⚠️ Network error — check your connection and try again."
            )

    raise RuntimeError("⚠️ Service unavailable — please try again shortly.")


def stream_llm(
    messages: list[dict],
    system_prompt: str = "",
    temperature: float = 0.7,
):
    """
    Stream a response from the OpenAI API, yielding text chunks as they arrive.
    Use with Streamlit's st.write_stream() for a live typewriter effect.

    Yields:
        str — incremental text chunks

    Raises:
        RuntimeError with a user-friendly message on failure.
    """
    full_messages = []
    if system_prompt:
        full_messages.append({"role": "system", "content": system_prompt})
    full_messages.extend(messages)

    try:
        with openai.chat.completions.create(
            model=MODEL,
            messages=full_messages,
            max_tokens=MAX_TOKENS,
            temperature=temperature,
            stream=True,
        ) as stream:
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta

    except openai.RateLimitError:
        raise RuntimeError("⚠️ Rate limit reached — wait a moment and try again.")
    except openai.APIStatusError as e:
        raise RuntimeError(f"⚠️ API error ({e.status_code}) — please try again.")
    except openai.APIConnectionError:
        raise RuntimeError("⚠️ Network error — check your connection and try again.")
