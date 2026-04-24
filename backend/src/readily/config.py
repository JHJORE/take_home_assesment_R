"""Single source of truth for runtime configuration.

Read once at each composition root (CLI group, FastAPI app factory) and passed
into adapters explicitly. Keeps env-var coupling out of the adapter classes so
tests don't need to mutate `os.environ`.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    gemini_api_key: str = Field(..., alias="GEMINI_API_KEY")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")

    data_dir: Path = Field(default=Path("data"))
    sample_data_dir: Path = Field(
        default=Path(__file__).resolve().parent.parent.parent / "sample-data"
    )
    policy_glob: str = Field(default="ENG #4/Public Policies/*/*.pdf")
    questionnaire_path: Path = Field(default=Path("ENG #4/Regulatory Questionnaire.pdf"))

    @property
    def questions_json(self) -> Path:
        return self.data_dir / "questions.json"

    @property
    def policies_json(self) -> Path:
        return self.data_dir / "policies.json"

    @property
    def results_json(self) -> Path:
        return self.data_dir / "results.json"

    @property
    def inventory_json(self) -> Path:
        return self.data_dir / "inventory.json"

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"
