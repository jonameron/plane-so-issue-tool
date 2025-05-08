from typing import List, Optional
from pydantic import BaseModel, Field

class IssueProperty(BaseModel):
    display_name: str
    description: str
    property_type: str = "text"  # Default to text type
    relation_type: Optional[str] = None
    default_value: Optional[List[str]] = None
    validation_rules: dict = Field(default_factory=dict)
    is_required: bool = True
    is_active: bool = True
    is_multi: bool = False

class ModuleIssue(BaseModel):
    body: str
    description: str

class Module(BaseModel):
    name: str
    issues: List[ModuleIssue]

class Issue(BaseModel):
    name: str
    description: str
    module_id: Optional[str] = None
    properties: Optional[List[IssueProperty]] = None 