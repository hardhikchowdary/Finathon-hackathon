from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # LLM Settings
    ANTHROPIC_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-3-5-sonnet-20240620"
    
    # Defaults and Dates
    REFERENCE_DATE: Optional[str] = None

    # Scoring Weights
    BASE_PROJECT: float = 10.0
    BASE_CERTIFICATION: float = 8.0
    BASE_TRAINING: float = 4.0
    BASE_SELF_DECLARED: float = 2.0
    
    COMPLEXITY_BASE_FACTOR: float = 0.6
    COMPLEXITY_MULTIPLIER: float = 0.2
    
    ROLE_CONTRIBUTOR: float = 1.0
    ROLE_LEAD: float = 1.3
    ROLE_ARCHITECT: float = 1.5
    
    DEFAULT_HALF_LIFE_MONTHS: int = 24
    SCORE_K: float = 40.0
    
    # Rank Weights
    WEIGHT_SKILL_FIT: float = 0.45
    WEIGHT_DOMAIN_FIT: float = 0.20
    WEIGHT_RECENCY: float = 0.15
    WEIGHT_AVAILABILITY: float = 0.10
    WEIGHT_VERIFICATION: float = 0.10

settings = Settings()
