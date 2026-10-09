"""Typed request/response contracts for the HTTP API."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from typing_extensions import Annotated

from .pipeline.analysis import MAX_CHARS

Priority = Literal["URGENT", "IMPORTANT", "FYI"]
FindingKind = Literal["task", "question", "decision", "information"]
ConversationText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_CHARS)]

class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: ConversationText

class SourceMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    timestamp: str
    sender: str
    text: str

class SourceLink(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str
    label: str

class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    priority: Priority
    topic: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=300)
    explanation: str = Field(min_length=1, max_length=1500)
    kind: FindingKind
    deadline: str | None = None
    links: list[SourceLink] = Field(default_factory=list)
    sources: list[SourceMessage] = Field(min_length=1)

class AnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    overview: list[str] = Field(min_length=1, max_length=20)
    categories: dict[Priority, list[Finding]]
    message_count: int = Field(ge=0)

    @model_validator(mode="after")
    def has_exact_priority_buckets(self):
        required={"URGENT", "IMPORTANT", "FYI"}
        if set(self.categories) != required:
            raise ValueError("Response must contain exactly URGENT, IMPORTANT, and FYI categories")
        for priority, findings in self.categories.items():
            if any(finding.priority != priority for finding in findings):
                raise ValueError("Finding priority does not match its response category")
        return self
