from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Category(str, Enum):
    PHISHING = "phishing"
    BRUTE_FORCE = "brute_force"
    DATA_EXFILTRATION = "data_exfiltration"
    CREDENTIAL_ABUSE = "credential_abuse"
    INSIDER_THREAT = "insider_threat"
    MALWARE = "malware"


class SecurityAlert(BaseModel):
    id: str
    timestamp: str
    source: str
    raw_text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class Classification(BaseModel):
    severity: Severity
    category: Category
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


class EvalResult(BaseModel):
    alert_id: str
    expected: Classification
    actual: Classification
    severity_match: bool
    category_match: bool
