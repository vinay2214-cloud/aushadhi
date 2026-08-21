"""AUSHADHI — agent audit log models.

Mirrors the `agent_logs` collection in docs/DATABASE_SCHEMA.md.
Every agent run writes one document (STARTED -> COMPLETED/FAILED).
All timestamps are ISO 8601 UTC strings.
"""

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

AgentName = Literal["SENTINEL", "DQMS", "FORECAST", "PROCUREMENT", "ALERT"]
AgentStatus = Literal["STARTED", "COMPLETED", "FAILED", "RETRYING"]


class AgentLogError(BaseModel):
    """Error detail recorded on a FAILED or RETRYING run."""

    model_config = ConfigDict(extra="ignore")

    message: str
    retry_count: int = 0

    def to_firestore_dict(self) -> dict:
        return self.model_dump()


class AgentLog(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    center_id: Optional[str] = None
    agent_name: AgentName
    action: str
    status: AgentStatus
    input: Dict[str, Any] = Field(default_factory=dict)
    output: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: int = 0

    gemini_prompt: Optional[str] = None
    gemini_response: Optional[str] = None
    error: Optional[AgentLogError] = None

    created_at: str
    completed_at: Optional[str] = None

    def to_firestore_dict(self, exclude_none: bool = True) -> dict:
        """Firestore document body.

        Optional audit fields (`gemini_prompt`, `gemini_response`, `error`) are
        dropped when unset to keep log documents small; `center_id` and
        `completed_at` are always written so district-wide and in-flight runs
        stay queryable.
        """
        data = self.model_dump(exclude_none=exclude_none)
        data.setdefault("center_id", self.center_id)
        data.setdefault("completed_at", self.completed_at)
        return data
