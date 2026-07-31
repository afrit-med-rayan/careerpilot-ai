import logging
from dataclasses import dataclass, field
from typing import List, Optional
import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class NormalizedJob:
    external_id: str
    source: str  # 'adzuna' | 'remotive'
    title: str
    company: str
    description: str
    url: str
    location: Optional[str] = None
    required_skills: List[str] = field(default_factory=list)


async def fetch_remotive_jobs(query: str, limit: int = 25) -> List[NormalizedJob]:
    """
    Fetches job postings from Remotive API (no API key required).
    Documentation: https://remotive.com/api-documentation
    """
    url = f"https://remotive.com/api/remote-jobs?search={query}&limit={limit}"
    jobs = []
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(url)
            if res.status_code == 200:
                data = res.json()
                raw_jobs = data.get("jobs", [])
                for item in raw_jobs[:limit]:
                    job_id = str(item.get("id"))
                    title = item.get("title") or "Unknown Title"
                    company = item.get("company_name") or "Unknown Company"
                    description = item.get("description") or ""
                    job_url = item.get("url") or f"https://remotive.com/job/{job_id}"
                    location = item.get("candidate_required_location") or "Remote"
                    tags = item.get("tags") or []
                    
                    jobs.append(
                        NormalizedJob(
                            external_id=job_id,
                            source="remotive",
                            title=title,
                            company=company,
                            description=description,
                            url=job_url,
                            location=location,
                            required_skills=tags if isinstance(tags, list) else [],
                        )
                    )
            else:
                logger.warning(f"Remotive API returned status {res.status_code}")
    except Exception as exc:
        logger.error(f"Error fetching from Remotive API: {exc}")
        
    return jobs


async def fetch_adzuna_jobs(query: str, location: Optional[str] = None, limit: int = 25) -> List[NormalizedJob]:
    """
    Fetches job postings from Adzuna API (requires ADZUNA_APP_ID & ADZUNA_APP_KEY).
    Documentation: https://developer.adzuna.com/
    """
    if not settings.adzuna_app_id or not settings.adzuna_app_key:
        logger.info("Adzuna API credentials not configured. Skipping Adzuna connector.")
        return []

    # Country defaults to 'us' (can be extended)
    where_param = f"&where={location}" if location else ""
    url = (
        f"https://api.adzuna.com/v1/api/jobs/us/search/1"
        f"?app_id={settings.adzuna_app_id}&app_key={settings.adzuna_app_key}"
        f"&what={query}{where_param}&results_per_page={limit}"
    )
    jobs = []

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(url)
            if res.status_code == 200:
                data = res.json()
                results = data.get("results", [])
                for item in results:
                    job_id = str(item.get("id"))
                    title = item.get("title") or "Unknown Title"
                    company = (item.get("company") or {}).get("display_name") or "Unknown Company"
                    description = item.get("description") or ""
                    job_url = item.get("redirect_url") or ""
                    loc_display = (item.get("location") or {}).get("display_name") or location or "US"

                    jobs.append(
                        NormalizedJob(
                            external_id=job_id,
                            source="adzuna",
                            title=title,
                            company=company,
                            description=description,
                            url=job_url,
                            location=loc_display,
                            required_skills=[],
                        )
                    )
            else:
                logger.warning(f"Adzuna API returned status {res.status_code}")
    except Exception as exc:
        logger.error(f"Error fetching from Adzuna API: {exc}")

    return jobs


async def fetch_all_jobs(query: str, location: Optional[str] = None, limit: int = 25) -> List[NormalizedJob]:
    """
    Fetches jobs from all active connectors (Remotive fallback + Adzuna if configured).
    """
    remotive_jobs = await fetch_remotive_jobs(query=query, limit=limit)
    adzuna_jobs = await fetch_adzuna_jobs(query=query, location=location, limit=limit)
    
    # Deduplicate by (source, external_id)
    combined = remotive_jobs + adzuna_jobs
    seen = set()
    unique_jobs = []
    
    for j in combined:
        key = (j.source, j.external_id)
        if key not in seen:
            seen.add(key)
            unique_jobs.append(j)
            
    return unique_jobs
