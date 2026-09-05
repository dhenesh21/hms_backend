from pydantic import BaseModel
from typing import Optional, List
from app.models.terminology import CodeSystem


class TerminologyCodeCreate(BaseModel):
    code_system: CodeSystem
    code: str
    display_name: str
    description: Optional[str] = None
    parent_code: Optional[str] = None


class TerminologyCodeResponse(BaseModel):
    id: int
    code_system: CodeSystem
    code: str
    display_name: str
    parent_code: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class TerminologyMappingCreate(BaseModel):
    source_code_id: int
    target_code_id: int
    mapping_confidence: Optional[str] = None


class TerminologyMappingResponse(BaseModel):
    id: int
    source_code_id: int
    target_code_id: int
    mapping_confidence: Optional[str]

    class Config:
        from_attributes = True


class BulkImportResult(BaseModel):
    imported: int
    skipped_duplicates: int
