from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator


class NoteInput(BaseModel):
    # 旧终态研究
    run_id: Optional[int] = None
    # 新复发（MCF）研究，二者必须且只能填一个
    recurrent_run_id: Optional[int] = None
    title: str = Field(min_length=2, max_length=120)
    interpretation: str = Field(min_length=8, max_length=2000)
    recommendation: str = Field(min_length=8, max_length=2000)

    @model_validator(mode="after")
    def _exactly_one_run(self):
        if bool(self.run_id) == bool(self.recurrent_run_id):
            raise ValueError("必须且只能关联一个研究（终态研究或复发研究）")
        return self


class ReviewInput(BaseModel):
    status: Literal["approved", "rejected"]
    review_note: str = Field(min_length=8, max_length=1000)
