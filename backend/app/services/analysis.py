import json
import logging
import re
from typing import Optional

from app.schemas.analysis import AnalysisIssue, ResumeAnalysis
from app.schemas.resume_parsed import ParsedResume
from app.services.llm_client import generate_structured_json, LLMError
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

def analyze_resume_rule_based(parsed: dict) -> ResumeAnalysis:
    """
    Performs a rule-based analysis on the parsed JSON to guarantee a fallback result.
    Checks for missing sections, no metrics, and passive voice heuristics.
    """
    score = 100
    issues = []
    
    # 1. Missing sections
    if not parsed.get("summary"):
        score -= 10
        issues.append(AnalysisIssue(
            section="summary",
            type="missing_section",
            detail="Your resume is missing a professional summary. This helps ATS and recruiters quickly understand your value.",
        ))
        
    experience = parsed.get("experience", [])
    if not experience:
        score -= 20
        issues.append(AnalysisIssue(
            section="experience",
            type="missing_section",
            detail="No work experience found. If you are an entry-level candidate, ensure you include projects or internships.",
        ))
        
    if not parsed.get("education"):
        score -= 10
        issues.append(AnalysisIssue(
            section="education",
            type="missing_section",
            detail="No education section found.",
        ))
        
    if not parsed.get("skills"):
        score -= 10
        issues.append(AnalysisIssue(
            section="skills",
            type="missing_section",
            detail="No skills section found. ATS systems rely heavily on keyword matching in skills.",
        ))

    # 2. Metric detection (regex for numbers, % or $) in experience bullets
    metric_pattern = re.compile(r'\d+|%|\$')
    passive_pattern = re.compile(r'\b(was|were|is|are|been|being)\s+[a-z]+ed\b', re.IGNORECASE)
    
    for exp in experience:
        bullets = exp.get("bullets", [])
        has_metrics = False
        
        for bullet in bullets:
            # Check for metrics
            if metric_pattern.search(bullet):
                has_metrics = True
                
            # Check for passive voice
            if passive_pattern.search(bullet):
                issues.append(AnalysisIssue(
                    section="experience",
                    type="passive_voice",
                    detail=f"Avoid passive voice to sound more impactful.",
                    location_hint=bullet[:50] + "..."
                ))
                score -= 2
                
        if not has_metrics and bullets:
            issues.append(AnalysisIssue(
                section="experience",
                type="no_metric",
                detail=f"Try to quantify your achievements in your role at {exp.get('company', 'this company')}. Use numbers, percentages, or dollar amounts.",
                location_hint=bullets[0][:50] + "..." if bullets else None
            ))
            score -= 5

    # Ensure score doesn't drop below 0
    score = max(0, score)
    
    return ResumeAnalysis(ats_score=score, issues=issues)


async def analyze_resume_llm(parsed: dict) -> Optional[ResumeAnalysis]:
    """
    Performs a deep analysis using the LLM.
    """
    prompt = (
        "Analyze the following parsed resume data as an expert recruiter and ATS system. "
        "Score the resume out of 100 based on its structure, impact, use of metrics, and action verbs. "
        "Identify specific issues like weak verbs, missing metrics, passive voice, or missing crucial sections.\n\n"
        f"{json.dumps(parsed, indent=2)}"
    )
    
    system_prompt = (
        "You are an expert resume reviewer and Applicant Tracking System (ATS). "
        "Provide a strict ATS score and a list of actionable issues. "
        "Be highly critical of bullet points that lack metrics or use weak verbs (e.g., 'helped', 'worked on')."
    )
    
    try:
        return await generate_structured_json(
            prompt=prompt,
            schema_model=ResumeAnalysis,
            system_prompt=system_prompt,
            temperature=0.0
        )
    except LLMError as exc:
        logger.error(f"LLM analysis failed: {exc}")
        return None


async def analyze_resume(parsed: dict) -> ResumeAnalysis:
    """
    Primary entry point for analysis. Tries LLM first (if key is set),
    falls back to rule-based if LLM fails or is not configured.
    """
    if settings.anthropic_api_key:
        llm_result = await analyze_resume_llm(parsed)
        if llm_result:
            return llm_result
            
    # Fallback to rule-based
    return analyze_resume_rule_based(parsed)
