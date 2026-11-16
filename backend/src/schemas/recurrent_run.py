from pydantic import BaseModel, Field


class RecurrentRunInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    cohort_a_id: int
    cohort_b_id: int
    cutoff_hours: float = Field(default=1450., gt=0, le=1_000_000, allow_inf_nan=False)
    confidence: float = Field(default=.95, ge=.8, le=.99, allow_inf_nan=False)
