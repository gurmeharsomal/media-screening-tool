# MIT License
# Copyright (c) 2024 Media Screening Tool

import re
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Request
from models import MatchRequest, MatchResponse, Stage1Result, Stage2Result
from rule_engine import stage1_filter
from llm_validator import stage2_validate

router = APIRouter()

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


def extract_context_around_person(article: str, person_name: str, window: int = 500) -> str:
    """Extract context around the best matching person."""
    match = re.search(re.escape(person_name), article, re.IGNORECASE)
    if not match:
        return article[:window]
    
    start = match.start()
    end = match.end()
    
    context_start = max(0, start - window // 2)
    context_end = min(len(article), end + window // 2)
    
    return article[context_start:context_end]


@router.post("/match", response_model=MatchResponse)
async def match_candidate(request: MatchRequest, raw_request: Request) -> MatchResponse:
    """Two-stage pipeline for candidate-article matching."""
    logger.info(f"Received /match request: candidate={request.candidate.model_dump()} article_length={len(request.article)} from {raw_request.client.host}")
    try:
        # Stage 1: Deterministic filtering
        stage1_result = stage1_filter(request.candidate, request.article)
        logger.info(f"Stage 1 result: {stage1_result.model_dump()}")
        
        if stage1_result.decision in ["match", "no_match"]:
            explanation = f"Stage 1: {stage1_result.decision} (score: {stage1_result.score}). {stage1_result.reasons}"
            if stage1_result.penalty > 0:
                explanation += f" Penalty applied: {stage1_result.penalty} points."
            logger.info(f"Returning Stage 1 decision: {stage1_result.decision}")
            return MatchResponse(
                decision=stage1_result.decision,
                stage=1,
                score=stage1_result.score,
                confidence=None,
                explanation=explanation,
                details={"stage1": stage1_result.model_dump()}
            )
        
        # Stage 2: LLM validation for borderline cases
        context = extract_context_around_person(
            request.article, 
            stage1_result.best_person
        )
        stage2_result = stage2_validate(request.candidate, context, stage1_result, request.article)
        logger.info(f"Stage 2 result: {stage2_result.model_dump()}")
        
        if stage2_result.decision == "match" and stage2_result.confidence >= 0.82:
            final_decision = "match"
            explanation = f"Stage 2: match with {stage2_result.confidence:.2f} confidence. {stage2_result.reasons}"
        else:
            final_decision = "no_match"
            explanation = f"Stage 2: no_match (confidence: {stage2_result.confidence:.2f}). {stage2_result.reasons}"
        logger.info(f"Returning Stage 2 decision: {final_decision}")
        return MatchResponse(
            decision=final_decision,
            stage=2,
            score=stage1_result.score,
            confidence=stage2_result.confidence,
            explanation=explanation,
            details={
                "stage1": stage1_result.model_dump(),
                "stage2": stage2_result.model_dump()
            }
        )
    except Exception as e:
        logger.error(f"Error processing /match request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    logger.info("Health check requested.")
    return {"status": "healthy"} 