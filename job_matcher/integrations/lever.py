"""
Lever ATS integration.

Lever is another popular Applicant Tracking System with a public postings API.
"""

from datetime import datetime
from typing import Optional
import logging

from .base import JobSearchProvider
from job_matcher.core.models import Job


class LeverProvider(JobSearchProvider):
    """Lever job board provider."""

    API_URL = "https://api.lever.co/v0/postings"

    # Popular companies using Lever
    LEVER_COMPANIES = [
        "netflix",
        "twitch",
        "lyft",
        "robinhood",
        "cloudflare",
        "netlify",
        "mongodb",
        "hashicorp",
        "pagerduty",
        "samsara",
        "gusto",
        "flexport",
        "carta",
        "sourcegraph",
        "linear",
    ]

    @property
    def name(self) -> str:
        return "Lever"

    @property
    def requires_api_key(self) -> bool:
        return False  # Public postings API

    def search_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        remote: bool = False,
        job_type: Optional[str] = None,
        experience_level: Optional[str] = None,
        salary_min: Optional[int] = None,
        limit: int = 50,
    ) -> list[Job]:
        """Search Lever job boards for matching jobs."""
        all_jobs = []

        for company in self.LEVER_COMPANIES:
            if len(all_jobs) >= limit:
                break

            company_jobs = self._get_company_jobs(company)
            filtered = self._filter_jobs(
                company_jobs, query, location, remote, experience_level
            )
            all_jobs.extend(filtered)

        return all_jobs[:limit]

    def _get_company_jobs(self, company_id: str) -> list[Job]:
        """Get all jobs from a company's Lever board."""
        try:
            import requests

            url = f"{self.API_URL}/{company_id}"
            params = {"mode": "json"}

            response = requests.get(url, params=params, timeout=30)

            if response.status_code != 200:
                return []

            data = response.json()
            jobs = []

            for job_data in data:
                job = self._parse_job(job_data, company_id)
                if job:
                    jobs.append(job)

            return jobs

        except ImportError:
            return self._get_sample_jobs(company_id)
        except Exception as e:
            self.logger.debug(f"Error fetching {company_id} Lever jobs: {e}")
            return []

    def _parse_job(self, data: dict, company_id: str) -> Optional[Job]:
        """Parse Lever job data into Job object."""
        try:
            # Categories contain location, team, commitment, etc.
            categories = data.get("categories", {})
            location = categories.get("location", "")
            team = categories.get("team", "")
            commitment = categories.get("commitment", "")

            # Description lists
            lists_html = data.get("lists", [])
            description_parts = []
            for lst in lists_html:
                description_parts.append(lst.get("text", ""))
                description_parts.extend(lst.get("content", "").split("<li>"))

            description = " ".join(description_parts)
            # Basic HTML cleanup
            description = description.replace("</li>", " ").replace("<br>", " ")

            return Job(
                id=f"lever_{company_id}_{data.get('id', '')}",
                title=data.get("text", ""),
                company=company_id.title().replace("-", " "),
                location=location,
                description=data.get("descriptionPlain", "") or description,
                posted_date=datetime.fromtimestamp(
                    data["createdAt"] / 1000
                ) if data.get("createdAt") else None,
                source="lever",
                source_url=data.get("hostedUrl", ""),
                remote_option="remote" in location.lower() or "remote" in commitment.lower(),
                industry=team,
            )
        except Exception as e:
            self.logger.error(f"Error parsing Lever job: {e}")
            return None

    def _filter_jobs(
        self,
        jobs: list[Job],
        query: str,
        location: Optional[str],
        remote: bool,
        experience_level: Optional[str],
    ) -> list[Job]:
        """Filter jobs by search criteria."""
        filtered = []
        query_lower = query.lower()

        for job in jobs:
            # Query match
            if query_lower not in job.title.lower() and query_lower not in job.description.lower():
                continue

            # Location filter
            if location and location.lower() not in job.location.lower():
                if not job.remote_option:
                    continue

            # Remote filter
            if remote and not job.remote_option:
                continue

            filtered.append(job)

        return filtered

    def get_job_details(self, job_id: str) -> Optional[Job]:
        """Get detailed job information from Lever."""
        try:
            import requests

            # Parse company and job ID
            parts = job_id.replace("lever_", "").split("_", 1)
            if len(parts) != 2:
                return None

            company_id, lever_job_id = parts

            url = f"{self.API_URL}/{company_id}/{lever_job_id}"
            response = requests.get(url, timeout=30)

            if response.status_code != 200:
                return None

            return self._parse_job(response.json(), company_id)

        except Exception as e:
            self.logger.error(f"Error getting Lever job details: {e}")
            return None

    def _get_sample_jobs(self, company_id: str) -> list[Job]:
        """Return sample jobs when API is unavailable."""
        return [
            Job(
                id=f"lever_{company_id}_sample",
                title="Software Engineer",
                company=company_id.title(),
                location="Remote",
                description="Join our team building innovative products.",
                source="lever",
                remote_option=True,
            )
        ]

    def get_companies(self) -> list[str]:
        """Get list of companies with Lever job boards."""
        return self.LEVER_COMPANIES.copy()
