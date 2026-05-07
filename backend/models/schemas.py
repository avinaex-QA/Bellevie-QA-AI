"""
Pydantic models for request/response validation throughout the API.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class SourceType(str, Enum):
    JIRA = "jira"
    DOCUMENT = "document"
    TEXT = "text"
    GITHUB_PR = "github_pr"
    MIXED = "mixed"


class Priority(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class TestType(str, Enum):
    FUNCTIONAL = "Functional"
    API = "API"
    SECURITY = "Security"
    UI = "UI"
    PERFORMANCE = "Performance"
    REGRESSION = "Regression"
    NEGATIVE = "Negative"
    EDGE_CASE = "Edge Case"


class TestCase(BaseModel):
    id: str = Field(..., description="Unique test case ID, e.g. TC-001")
    priority: str = Field(..., description="High, Medium, or Low")
    title: str = Field(..., description="Clear, action-based test case title")
    preconditions: str = Field(..., description="Prerequisites before test execution")
    steps: List[str] = Field(..., description="Ordered list of test steps")
    expected_result: str = Field(..., description="Measurable expected outcome")
    actual_result: str = Field(default="", description="Left blank for manual execution")
    tags: List[str] = Field(default_factory=list, description="e.g. Smoke, Regression, Sanity")
    test_type: str = Field(default="Functional", description="Category of test")


class TestSummary(BaseModel):
    total: int
    high_priority: int
    medium_priority: int
    low_priority: int
    module_detected: str = "General"


class GenerateRequest(BaseModel):
    source_type: SourceType
    jira_id: Optional[str] = None
    text_input: Optional[str] = None
    github_pr_url: Optional[str] = None
    additional_context: Optional[str] = None


class GenerateResponse(BaseModel):
    success: bool
    test_cases: List[TestCase]
    summary: TestSummary
    source_info: Dict[str, Any] = Field(default_factory=dict)
    message: Optional[str] = None


class JiraTicket(BaseModel):
    ticket_id: str
    summary: str
    description: str
    acceptance_criteria: str = ""
    comments: List[str] = Field(default_factory=list)
    status: str = ""
    priority: str = ""
    issue_type: str = ""
    labels: List[str] = Field(default_factory=list)
    raw_text: str = ""


class ExportRequest(BaseModel):
    test_cases: List[TestCase]
    sheet_title: str = "Test Cases"
    project_name: str = "AI Generated Test Cases"
    source_type: str = "text"
    module_detected: str = "General"


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None


class JiraFetchRequest(BaseModel):
    ticket_id: str


class GitPRRequest(BaseModel):
    pr_url: str
