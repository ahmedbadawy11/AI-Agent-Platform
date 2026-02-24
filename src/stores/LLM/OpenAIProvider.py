import logging
import tempfile
import os

from openai import OpenAI

from ..LLMEnums import OpenAIEnums

class OpenAIProvider():

    def __init__(self, api_key: str,
                default_generation_max_output_tokens: int = 1000,
                default_generation_temperature: float = 0.1):
        self.api_key = api_key
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature
        self.generation_model_id = None
        self.stt_model_id = None
        self.tts_model_id = None
        self.tts_voice = None
      
        self.client = OpenAI(api_key=api_key or "")
        
        self.logger = logging.getLogger(__name__)

    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id # this will allow dynamic model selection while run time

    def set_stt_model(self, model_id: str):
        self.stt_model_id = model_id

    def set_tts_model(self, model_id: str):
        self.tts_model_id = model_id

  

    def generate_chat(
        self,
        messages: list[dict],
        max_output_tokens: int = None,
        temperature: float = None,
    ) -> str | None:
        """Generate assistant reply given full conversation history (for chat with context)."""
        if not self.client:
            self.logger.error("OpenAI client is not initialized.")
            return None
        if not self.generation_model_id:
            self.logger.error("Generation model for OpenAI was not set.")
            return None
        max_output_tokens = max_output_tokens or self.default_generation_max_output_tokens
        temperature = temperature or self.default_generation_temperature
        response = self.client.chat.completions.create(
            model=self.generation_model_id,
            messages=messages,
            max_tokens=max_output_tokens,
            temperature=temperature,
        )
        if not response or not response.choices or len(response.choices) == 0 or not response.choices[0].message:
            self.logger.error("Error while generating chat with OpenAI.")
            return None
        msg = response.choices[0].message
        return getattr(msg, "content", None) or (msg.model_dump().get("content") if hasattr(msg, "model_dump") else None)

    def generate_chat_stream(
        self,
        messages: list[dict],
        max_output_tokens: int = None,
        temperature: float = None,
    ):
        """Stream assistant reply chunk by chunk. Yields content deltas (str). Caller can accumulate and persist when done."""
        if not self.client:
            self.logger.error("OpenAI client is not initialized.")
            return
        if not self.generation_model_id:
            self.logger.error("Generation model for OpenAI was not set.")
            return
        max_output_tokens = max_output_tokens or self.default_generation_max_output_tokens
        temperature = temperature or self.default_generation_temperature
        stream = self.client.chat.completions.create(
            model=self.generation_model_id,
            messages=messages,
            max_tokens=max_output_tokens,
            temperature=temperature,
            stream=True,
        )
        for chunk in stream:
            if not chunk.choices or len(chunk.choices) == 0:
                continue
            delta = chunk.choices[0].delta
            if delta is None:
                continue
            content = getattr(delta, "content", None) or (delta.model_dump().get("content") if hasattr(delta, "model_dump") else None)
            if content:
                yield content

    def speech_to_text(self, audio_file, filename: str = "audio.webm") -> str | None:
        """Convert audio file to text using OpenAI transcription API."""
        
        if not self.client:
            self.logger.error("OpenAI client is not initialized.")
            return None

        model = getattr(self, "stt_model_id", None) or "whisper-1"

        # Ensure we have bytes
        if hasattr(audio_file, "read"):
            audio_bytes = audio_file.read()
        else:
            audio_bytes = bytes(audio_file)

        # Whisper needs a file with correct extension so it recognizes the format.
        # BytesIO without a filename can be sent as "file" with no extension and get "Unrecognized file format".
        ext = os.path.splitext(filename)[1] or ".webm"
        if not ext.startswith("."):
            ext = "." + ext
        try:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            try:
                with open(tmp_path, "rb") as f:
                    response = self.client.audio.transcriptions.create(
                        model=model,
                        file=f,
                    )
                if response and hasattr(response, "text"):
                    return response.text.strip()
                return None
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
        except Exception as e:
            self.logger.error("Speech-to-text error: %s", e)
            return None

    def text_to_speech(self, text: str, voice: str = "alloy") -> bytes | None:
        """Convert text to audio bytes using OpenAI TTS."""
        if not self.client:
            self.logger.error("OpenAI client is not initialized.")
            return None
        model = getattr(self, "tts_model_id", None) or "tts-1"
        try:
            response = self.client.audio.speech.create(
                model=model,
                voice=voice,
                input=text,
            )
            if response and hasattr(response, "content"):
                return response.content
            return None
        except Exception as e:
            self.logger.error("Text-to-speech error: %s", e)
            return None

    def construct_prompt(self, prompt: str, role: dict):
        # for openai we can use system role to set the behavior of the model
        return {
            "role":role,
            "content":prompt
        }
        


