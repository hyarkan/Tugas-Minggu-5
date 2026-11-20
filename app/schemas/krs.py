from datetime import time
from pydantic import BaseModel, ConfigDict, Field


class AddCourseRequest(BaseModel):
    kode_mk: str = Field(min_length=1, max_length=20)


class KRSDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    krs_id: int
    kode_mk: str
    nilai: str | None


class KRSResponse(BaseModel):
    id: int
    nim: str
    semester: str
    status: str
    total_sks: int
    mata_kuliah: list[str]


class KRSValidationResponse(BaseModel):
    valid: bool
    errors: list[str]
