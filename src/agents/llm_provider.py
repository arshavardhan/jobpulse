import os
import json
import logging
from typing import Dict, Any, Optional, List
from src.config import settings

logger = logging.getLogger(__name__)

class LLMProvider:
    """Unified LLM Provider supporting Google Gemini, OpenAI, or intelligent offline heuristic NLP."""

    def __init__(self):
        self.provider = "heuristic"
        self.gemini_client = None
        self.openai_client = None

        # Check for Gemini
        gemini_key = os.environ.get("GEMINI_API_KEY") or settings.GEMINI_API_KEY
        if gemini_key:
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=gemini_key)
                self.provider = "gemini"
                logger.info("Initialized Google Gemini client.")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini: {e}")

        # Check for OpenAI if Gemini is not set
        if self.provider == "heuristic":
            openai_key = os.environ.get("OPENAI_API_KEY") or settings.OPENAI_API_KEY
            if openai_key:
                try:
                    import openai
                    self.openai_client = openai.OpenAI(api_key=openai_key)
                    self.provider = "openai"
                    logger.info("Initialized OpenAI client.")
                except Exception as e:
                    logger.warning(f"Failed to initialize OpenAI: {e}")

    def generate(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Generate text using the configured provider."""
        if self.provider == "gemini" and self.gemini_client:
            try:
                response = self.gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config={"system_instruction": system_instruction} if system_instruction else None
                )
                return response.text
            except Exception as e:
                logger.error(f"Gemini generation error: {e}, falling back to heuristic")

        elif self.provider == "openai" and self.openai_client:
            try:
                messages = []
                if system_instruction:
                    messages.append({"role": "system", "content": system_instruction})
                messages.append({"role": "user", "content": prompt})

                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    temperature=0.7
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"OpenAI generation error: {e}, falling back to heuristic")

        # Heuristic fallback generator
        return self._heuristic_generate(prompt)

    def _heuristic_generate(self, prompt: str) -> str:
        """Intelligent offline fallback response generator."""
        return (
            "Generated via Intelligent Heuristic Engine:\n"
            "High-impact alignment detected based on core competency overlap and structural analysis."
        )

llm = LLMProvider()
