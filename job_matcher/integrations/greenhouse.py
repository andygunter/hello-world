"""
Greenhouse ATS integration.

Greenhouse is a popular Applicant Tracking System used by many tech companies.
Their job board API is public and doesn't require authentication for reading jobs.
"""

from datetime import datetime
from typing import Optional
import logging

from .base import JobSearchProvider
from job_matcher.core.models import Job


class GreenhouseProvider(JobSearchProvider):
    """Greenhouse job board provider."""

    API_URL = "https://boards-api.greenhouse.io/v1/boards"

    # Popular companies using Greenhouse
    GREENHOUSE_COMPANIES = [
        "airbnb",
        "slack",
        "doordash",
        "coinbase",
        "instacart",
        "datadog",
        "figma",
        "notion",
        "databricks",
        "plaid",
        "affirm",
        "brex",
        "ramp",
        "discord",
        "reddit",
    ]

    @property
    def name(self) -> str:
        return "Greenhouse"

    @property
    def requires_api_key(self) -> bool:
        return False  # Public API for job boards

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
        """Search Greenhouse job boards for matching jobs."""
        all_jobs = []

        for company in self.GREENHOUSE_COMPANIES:
            if len(all_jobs) >= limit:
                break

            company_jobs = self._get_company_jobs(company)
            filtered = self._filter_jobs(
                company_jobs, query, location, remote, experience_level
            )
            all_jobs.extend(filtered)

        return all_jobs[:limit]

    def _get_company_jobs(self, company_id: str) -> list[Job]:
        """Get all jobs from a company's Greenhouse board."""
        try:
            import requests

            url = f"{self.API_URL}/{company_id}/jobs"
            params = {"content": "true"}  # Include job descriptions

            response = requests.get(url, params=params, timeout=30)

            if response.status_code != 200:
                return []

            data = response.json()
            jobs = []

            for job_data in data.get("jobs", []):
                job = self._parse_job(job_data, company_id)
                if job:
                    jobs.append(job)

            return jobs

        except ImportError:
            return self._get_sample_jobs(company_id)
        except Exception as e:
            self.logger.debug(f"Error fetching {company_id} jobs: {e}")
            return []

    def _parse_job(self, data: dict, company_id: str) -> Optional[Job]:
        """Parse Greenhouse job data into Job object."""
        try:
            # Extract location
            location_data = data.get("location", {})
            location = location_data.get("name", "") if isinstance(location_data, dict) else str(location_data)

            # Parse departments
            departments = [d.get("name", "") for d in data.get("departments", [])]

            # Extract content/description
            content = data.get("content", "")

            return Job(
                id=f"greenhouse_{company_id}_{data.get('id', '')}",
                title=data.get("title", ""),
                company=company_id.title().replace("-", " "),
                location=location,
                description=content,
                posted_date=datetime.fromisoformat(
                    data["updated_at"].replace("Z", "+00:00")
                ) if data.get("updated_at") else None,
                source="greenhouse",
                source_url=data.get("absolute_url", ""),
                remote_option="remote" in location.lower(),
                industry=departments[0] if departments else "",
            )
        except Exception as e:
            self.logger.error(f"Error parsing Greenhouse job: {e}")
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
            # Query match (title or description)
            if query_lower not in job.title.lower() and query_lower not in job.description.lower():
                continue

            # Location filter
            if location and location.lower() not in job.location.lower():
                if not job.remote_option:
                    continue

            # Remote filter
            if remote and not job.remote_option:
                continue

            # Experience level (check title/description)
            if experience_level:
                exp_lower = experience_level.lower()
                text = f"{job.title} {job.description}".lower()
                if exp_lower == "senior" and "senior" not in text and "sr." not in text:
                    continue
                if exp_lower == "entry" and "junior" not in text and "entry" not in text:
                    continue

            filtered.append(job)

        return filtered

    def get_job_details(self, job_id: str) -> Optional[Job]:
        """Get detailed job information from Greenhouse."""
        try:
            import requests

            # Parse company and job ID from our format
            parts = job_id.replace("greenhouse_", "").split("_", 1)
            if len(parts) != 2:
                return None

            company_id, gh_job_id = parts

            url = f"{self.API_URL}/{company_id}/jobs/{gh_job_id}"
            response = requests.get(url, timeout=30)

            if response.status_code != 200:
                return None

            return self._parse_job(response.json(), company_id)

        except Exception as e:
            self.logger.error(f"Error getting Greenhouse job details: {e}")
            return None

    def _get_sample_jobs(self, company_id: str) -> list[Job]:
        """Return sample jobs when API is unavailable."""
        return [
            Job(
                id=f"greenhouse_{company_id}_sample",
                title="Software Engineer",
                company=company_id.title(),
                location="San Francisco, CA",
                description="Join our engineering team to build amazing products.",
                source="greenhouse",
                remote_option=True,
            )
        ]

    def get_companies(self) -> list[str]:
        """Get list of companies with Greenhouse job boards."""
        return self.GREENHOUSE_COMPANIES.copy()

    def add_company(self, company_id: str) -> None:
        """Add a company to track."""
        if company_id not in self.GREENHOUSE_COMPANIES:
            self.GREENHOUSE_COMPANIES.append(company_id)
