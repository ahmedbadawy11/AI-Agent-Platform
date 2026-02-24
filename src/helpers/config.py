from pydantic_settings import BaseSettings, SettingsConfigDict


class settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str
    APP_VERSION: str
    OPENAI_API_KEY: str | None = None
    POSTGRES_PASSWORD: str
    POSTGRES_USERNAME: str
    POSTGRES_MAIN_DATABASE: str
    POSTGRES_PORT: int
    POSTGRES_HOST: str
    GENERATION_MODEL_ID: str | None = None
    EMBEDDING_MODEL_ID: str | None = None
    EMBEDDING_MODEL_SIZE: int | None = None
    INPUT_DAFAULT_MAX_CHARACTERS: int | None = None
    GENERATION_DAFAULT_MAX_TOKENS: int | None = None
    GENERATION_DAFAULT_TEMPERATURE: float | None = None
    STT_MODEL_ID: str = "whisper-1"
    TTS_MODEL_ID: str = "tts-1"
    TTS_VOICE: str = "alloy"
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR


def get_settings():
    # settings_instance = settings()
    # return settings_instance.
    return settings()