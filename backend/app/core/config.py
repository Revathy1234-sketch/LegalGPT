import os
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # =========================
    # Database
    # =========================
    DATABASE_URL: str

    # =========================
    # Authentication
    # =========================
    SECRET_KEY: str

    JWT_SECRET: str

    ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # =========================
    # Gemini
    # =========================
    GEMINI_API_KEY: str = ""

    GEMINI_MODEL: str = ""

    # =========================
    # OpenRouter
    # =========================
    OPENROUTER_API_KEY: str = ""

    OPENROUTER_MODEL: str = ""

    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    # =========================
    # NVIDIA
    # =========================
    NVIDIA_API_KEY: str = ""

    NVIDIA_MODEL: str = "openai/gpt-oss-20b"

    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"

    # =========================
    # Environment
    # =========================
    ENVIRONMENT: str = "development"

    DEBUG: bool = False

    # =========================
    # File Storage
    # =========================
    UPLOAD_DIR: str = "./uploads"

    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024

    # =========================
    # FAISS
    # =========================
    FAISS_INDEX_PATH: str = "./faiss_index"

    # =========================
    # Embeddings
    # =========================
    EMBEDDING_MODEL: str = (
        "sentence-transformers/all-MiniLM-L6-v2"
    )

    TOP_K_RETRIEVAL: int = 10
    MIN_RELEVANCE_SCORE: float = 0.20
    SEMANTIC_TOP_K: int = 15
    BM25_TOP_K: int = 15
    MAX_CHUNK_RESULTS: int = 8
    EMBEDDING_BATCH_SIZE: int = 32

    MAX_SUMMARY_CHARS: int = 15000

    # =========================
    # CORS
    # =========================
    ALLOWED_ORIGINS: str = (
        "http://localhost:3000,"
        "http://127.0.0.1:3000"
    )

    # =========================
    # Validators
    # =========================
    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str):
            return value.lower() in {
                "1",
                "true",
                "yes",
                "on"
            }
        return value

    # =========================
    # Pydantic Settings
    # =========================
    model_config = SettingsConfigDict(
        env_file=os.path.join(
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(__file__)
                )
            ),
            ".env"
        ),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()