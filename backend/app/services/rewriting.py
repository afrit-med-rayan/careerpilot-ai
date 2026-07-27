import json
import logging
from typing import Optional

from app.core.config import get_settings
from app.schemas.rewrite import RewriteItem, RewriteRequest, RewriteResponse
from app.services.llm_client import LLMError, generate_structured_json

logger = logging.getLogger(__name__)
settings = get_settings()


def rewrite_bullets_rule_based(parsed: dict) -> RewriteResponse:
    """
    Fallback rule-based rewriter if LLM is unavailable or unconfigured.
    Identifies weak bullets and suggests standard improvements.
    """
    rewrites = []
    experience = parsed.get("experience", [])

    for exp in experience:
        bullets = exp.get("bullets", [])
        for bullet in bullets:
            lowered = bullet.lower()
            if any(weak in lowered for weak in ["responsible for", "worked on", "helped with", "assisted in"]):
                # Transform weak prefix to action verb
                cleaned = bullet
                for weak in ["responsible for ", "Responsible for ", "worked on ", "Worked on ", "helped with ", "Assisted in "]:
                    cleaned = cleaned.replace(weak, "")
                rewritten = f"Spearheaded {cleaned[0].lower() + cleaned[1:] if cleaned else cleaned} to drive measurable performance and efficiency."
                rewrites.append(
                    RewriteItem(
                        original=bullet,
                        rewritten=rewritten,
                        reason="Replaced passive/weak phrasing with a strong action verb ('Spearheaded') and focused on business impact.",
                    )
                )

    if not rewrites and experience:
        # Provide at least one sample improvement if no weak verbs were matched
        first_bullet = experience[0].get("bullets", [""])[0]
        if first_bullet:
            rewrites.append(
                RewriteItem(
                    original=first_bullet,
                    rewritten=f"Optimized and executed: {first_bullet} (Quantify result with exact %, e.g., 'resulting in 25% faster delivery').",
                    reason="Added structural impact template to encourage quantitative metrics.",
                )
            )

    return RewriteResponse(rewrites=rewrites)


async def rewrite_resume_llm(parsed: dict, job_description: Optional[str] = None) -> Optional[RewriteResponse]:
    """
    Calls Anthropic LLM to generate high-impact bullet point rewrites tailored to an optional job description.
    """
    prompt = (
        "Analyze the work experience bullets and summary from this resume data. "
        "Generate improved versions of weak or unquantified bullet points. "
        "Use strong action verbs, STAR method structure, and highlight key competencies.\n\n"
        f"RESUME DATA:\n{json.dumps(parsed, indent=2)}\n\n"
    )

    if job_description and job_description.strip():
        prompt += (
            "TARGET JOB DESCRIPTION:\n"
            f"{job_description.strip()}\n\n"
            "Tailor the rewrites to align with keywords and responsibilities in the target job description while strictly adhering to the facts in the candidate's resume."
        )

    system_prompt = (
        "You are an expert executive resume writer and career coach. "
        "Only use facts present in the provided resume data. Never invent employers, job titles, dates, or metrics. "
        "If information needed to fully answer is missing, state that explicitly rather than fabricating it."
    )

    try:
        return await generate_structured_json(
            prompt=prompt,
            schema_model=RewriteResponse,
            system_prompt=system_prompt,
            temperature=0.2,
        )
    except LLMError as exc:
        logger.error(f"LLM rewrite failed: {exc}")
        return None


async def rewrite_resume(parsed: dict, request: Optional[RewriteRequest] = None) -> RewriteResponse:
    """
    Main entry point for rewriting service. Tries LLM first if API key configured,
    falls back to rule-based suggestion engine.
    """
    job_desc = request.job_description if request else None

    if settings.anthropic_api_key:
        llm_result = await rewrite_resume_llm(parsed, job_desc)
        if llm_result:
            return llm_result

    return rewrite_bullets_rule_based(parsed)
