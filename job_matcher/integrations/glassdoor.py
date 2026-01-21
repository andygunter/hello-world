"""
Glassdoor job search integration.

Provides job search with company ratings and salary insights.
"""

from datetime import datetime
from typing import Optional
import logging

from .base import JobSearchProvider
from job_matcher.core.models import Job


class GlassdoorProvider(JobSearchProvider):
    """Glassdoor job search provider with company insights."""

    BASE_URL = "https://www.glassdoor.com"
    API_URL = "https://api.glassdoor.com/api/api.htm"

    @property
    def name(self) -> str:
        return "Glassdoor"

    @property
    def requires_api_key(self) -> bool:
        return True  # Requires partner API access

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
        """Search Glassdoor for jobs."""
        if self.api_key:
            return self._search_via_api(
                query, location, remote, job_type, salary_min, limit
            )
        else:
            return self._get_sample_jobs(query, location, limit)

    def _search_via_api(
        self,
        query: str,
        location: Optional[str],
        remote: bool,
        job_type: Optional[str],
        salary_min: Optional[int],
        limit: int,
    ) -> list[Job]:
        """Search using Glassdoor Partner API."""
        try:
            import requests

            params = {
                "v": "1",
                "format": "json",
                "t.p": self.api_key,  # Partner ID
                "t.k": self.api_key,  # Partner key (simplified)
                "action": "jobs",
                "q": query,
                "l": location or "",
                "pn": 1,  # Page number
                "ps": min(limit, 30),  # Page size
            }

            if remote:
                params["remoteWorkType"] = "1"

            response = requests.get(self.API_URL, params=params, timeout=30)

            if response.status_code != 200:
                self.logger.error(f"Glassdoor API error: {response.status_code}")
                return self._get_sample_jobs(query, location, limit)

            data = response.json()
            jobs = []

            for job_data in data.get("response", {}).get("jobListings", []):
                job = self._parse_api_job(job_data)
                if job:
                    jobs.append(job)

            return jobs

        except ImportError:
            return self._get_sample_jobs(query, location, limit)
        except Exception as e:
            self.logger.error(f"Glassdoor API error: {e}")
            return self._get_sample_jobs(query, location, limit)

    def _parse_api_job(self, data: dict) -> Optional[Job]:
        """Parse Glassdoor API response into Job object."""
        try:
            employer = data.get("employer", {})

            return Job(
                id=f"glassdoor_{data.get('jobListingId', '')}",
                title=data.get("jobTitle", ""),
                company=employer.get("name", ""),
                location=data.get("location", ""),
                description=data.get("descriptionFragment", ""),
                salary_min=data.get("payCurrency", {}).get("minPay"),
                salary_max=data.get("payCurrency", {}).get("maxPay"),
                posted_date=datetime.now(),
                source="glassdoor",
                source_url=data.get("jobViewUrl", ""),
                company_size=employer.get("size", ""),
                industry=employer.get("industry", ""),
            )
        except Exception as e:
            self.logger.error(f"Error parsing Glassdoor job: {e}")
            return None

    def get_job_details(self, job_id: str) -> Optional[Job]:
        """Get detailed job information from Glassdoor."""
        # Would require additional API call
        return None

    def _get_sample_jobs(
        self,
        query: str,
        location: Optional[str],
        limit: int,
    ) -> list[Job]:
        """Return sample Glassdoor-style jobs."""
        sample_jobs = [
            Job(
                id="glassdoor_sample_1",
                title=f"{query} Engineer",
                company="Salesforce",
                location=location or "San Francisco, CA",
                description=f"Build cloud solutions using {query}. "
                           "Great company culture with 4.2 rating on Glassdoor.",
                salary_min=145000,
                salary_max=195000,
                source="glassdoor",
                source_url="https://glassdoor.com/jobs/sample1",
                remote_option=True,
                company_size="10000+",
                industry="Cloud Computing",
                required_skills=[query, "Java", "Salesforce Platform"],
                experience_level="mid",
            ),
            Job(
                id="glassdoor_sample_2",
                title=f"Senior {query} Developer",
                company="Adobe",
                location=location or "San Jose, CA",
                description=f"Join Adobe's creative tools team. Apply {query} skills "
                           "to build products used by millions of creatives.",
                salary_min=165000,
                salary_max=220000,
                source="glassdoor",
                source_url="https://glassdoor.com/jobs/sample2",
                remote_option=True,
                company_size="10000+",
                industry="Software",
                required_skills=[query, "C++", "Creative Cloud"],
                experience_level="senior",
            ),
            Job(
                id="glassdoor_sample_3",
                title=f"{query} Software Engineer",
                company="Airbnb",
                location=location or "San Francisco, CA",
                description=f"Help millions find their perfect stay. Use {query} "
                           "to build the future of travel technology.",
                salary_min=155000,
                salary_max=210000,
                source="glassdoor",
                source_url="https://glassdoor.com/jobs/sample3",
                remote_option=True,
                company_size="5000-10000",
                industry="Travel Tech",
                required_skills=[query, "Ruby", "React", "GraphQL"],
                experience_level="mid",
            ),
        ]
        return sample_jobs[:limit]
