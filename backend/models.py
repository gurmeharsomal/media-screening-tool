from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class Candidate(BaseModel):
    name: str = Field(..., min_length=1, description="Full name of the candidate")
    dob: Optional[str] = Field(None, description="Date of birth in YYYY-MM-DD format")
    occupation: Optional[str] = Field(None, description="Occupation or job title")


class MatchRequest(BaseModel):
    candidate: Candidate
    article: str = Field(..., min_length=1, description="Raw article text to analyze")


class Stage1Result(BaseModel):
    stage: int = Field(1, description="Pipeline stage")
    decision: str = Field(..., description="match, no_match, or review")
    score: int = Field(..., ge=0, le=100, description="Fuzzy match score")
    best_person: str = Field(..., description="Best matching person entity")
    candidate_variant: str = Field(..., description="Candidate name variant used")
    all_variants: str = Field(..., description="All generated name variants for the candidate")
    penalty: int = Field(0, ge=0, le=100, description="Penalty applied for conflicts")
    reasons: str = Field(..., description="Plain English explanation of the decision")


class Stage2Result(BaseModel):
    decision: str = Field(..., description="match or no_match")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="LLM confidence score")
    evidence_sentence: str = Field(..., description="Supporting evidence from article")
    reasons: str = Field(..., description="Plain English explanation of the decision")


class MatchResponse(BaseModel):
    decision: str = Field(..., description="Final decision: match or no_match")
    stage: int = Field(..., description="Stage that made the decision (1 or 2)")
    score: int = Field(..., ge=0, le=100, description="Overall score")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="LLM confidence if stage 2")
    explanation: str = Field(..., description="Human-readable explanation")
    details: Dict[str, Any] = Field(..., description="Detailed results from each stage") 