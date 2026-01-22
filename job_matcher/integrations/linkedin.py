"""
LinkedIn job search integration.

Note: LinkedIn's official API requires OAuth and partnership.
This implementation provides structure for API integration and
a sample data fallback for development/testing.
"""

from datetime import datetime
from typing import Optional
import hashlib
import logging

from .base import JobSearchProvider
from job_matcher.core.models import Job, JobType


class LinkedInProvider(JobSearchProvider):
    """LinkedIn job search provider."""

    BASE_URL = "https://www.linkedin.com"
    API_URL = "https://api.linkedin.com/v2"

    @property
    def name(self) -> str:
        return "LinkedIn"

    @property
    def requires_api_key(self) -> bool:
        return True

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
        """Search LinkedIn for jobs."""
        if self.api_key:
            return self._search_via_api(
                query, location, remote, job_type, experience_level, salary_min, limit
            )
        else:
            self.logger.info("No LinkedIn API key, returning sample data")
            return self._get_sample_jobs(query, location, experience_level, limit)

    def _search_via_api(
        self,
        query: str,
        location: Optional[str],
        remote: bool,
        job_type: Optional[str],
        experience_level: Optional[str],
        salary_min: Optional[int],
        limit: int,
    ) -> list[Job]:
        """
        Search using LinkedIn API.

        Requires OAuth 2.0 access token with r_liteprofile and r_jobs_guest permissions.
        """
        try:
            import requests

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            }

            # LinkedIn Jobs API endpoint
            params = {
                "keywords": query,
                "locationId": self._get_location_id(location),
                "count": min(limit, 50),
            }

            if remote:
                params["workRemoteAllowed"] = "true"

            if job_type:
                params["jobType"] = self._map_job_type(job_type)

            if experience_level:
                params["experienceLevel"] = self._map_experience_level(experience_level)

            response = requests.get(
                f"{self.API_URL}/jobSearch",
                headers=headers,
                params=params,
                timeout=30,
            )

            if response.status_code == 401:
                self.logger.error("LinkedIn API authentication failed")
                return self._get_sample_jobs(query, location, experience_level, limit)

            if response.status_code != 200:
                self.logger.error(f"LinkedIn API error: {response.status_code}")
                return self._get_sample_jobs(query, location, experience_level, limit)

            data = response.json()
            jobs = []

            for element in data.get("elements", []):
                job = self._parse_api_job(element)
                if job:
                    jobs.append(job)

            return jobs

        except ImportError:
            self.logger.warning("requests library not installed")
            return self._get_sample_jobs(query, location, experience_level, limit)
        except Exception as e:
            self.logger.error(f"LinkedIn API error: {e}")
            return self._get_sample_jobs(query, location, experience_level, limit)

    def _parse_api_job(self, data: dict) -> Optional[Job]:
        """Parse LinkedIn API job data into Job object."""
        try:
            company_data = data.get("companyDetails", {})
            location_data = data.get("formattedLocation", "")

            salary_data = data.get("salaryInsights", {})
            salary_min = salary_data.get("minSalary")
            salary_max = salary_data.get("maxSalary")

            return Job(
                id=f"linkedin_{data.get('trackingUrn', '')}",
                title=data.get("title", ""),
                company=company_data.get("companyName", ""),
                location=location_data,
                description=data.get("description", {}).get("text", ""),
                salary_min=salary_min,
                salary_max=salary_max,
                posted_date=datetime.fromtimestamp(
                    data.get("listedAt", 0) / 1000
                ) if data.get("listedAt") else None,
                source="linkedin",
                source_url=f"{self.BASE_URL}/jobs/view/{data.get('trackingUrn', '')}",
                remote_option=data.get("workRemoteAllowed", False),
                company_size=company_data.get("companySize", ""),
                industry=company_data.get("industry", ""),
            )
        except Exception as e:
            self.logger.error(f"Error parsing LinkedIn job: {e}")
            return None

    def _get_location_id(self, location: Optional[str]) -> str:
        """Convert location string to LinkedIn location ID."""
        # In production, this would use LinkedIn's location autocomplete API
        location_map = {
            "san francisco": "102277331",
            "new york": "102571732",
            "seattle": "104116203",
            "austin": "104472866",
            "remote": "92000000",
        }

        if location:
            for key, loc_id in location_map.items():
                if key in location.lower():
                    return loc_id

        return ""

    def _map_job_type(self, job_type: str) -> str:
        """Map job type to LinkedIn API format."""
        mapping = {
            "full_time": "F",
            "part_time": "P",
            "contract": "C",
            "internship": "I",
            "temporary": "T",
        }
        return mapping.get(job_type.lower(), "F")

    def _map_experience_level(self, level: str) -> str:
        """Map experience level to LinkedIn API format."""
        mapping = {
            "entry": "1",
            "associate": "2",
            "mid": "3",
            "senior": "4",
            "director": "5",
            "executive": "6",
        }
        return mapping.get(level.lower(), "3")

    def get_job_details(self, job_id: str) -> Optional[Job]:
        """Get detailed job information from LinkedIn."""
        if not self.api_key:
            self.logger.warning("LinkedIn API key required for job details")
            return None

        try:
            import requests

            job_urn = job_id.replace("linkedin_", "")

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "X-Restli-Protocol-Version": "2.0.0",
            }

            response = requests.get(
                f"{self.API_URL}/jobs/{job_urn}",
                headers=headers,
                timeout=30,
            )

            if response.status_code != 200:
                return None

            return self._parse_api_job(response.json())

        except Exception as e:
            self.logger.error(f"Error getting LinkedIn job details: {e}")
            return None

    def _get_sample_jobs(
        self,
        query: str,
        location: Optional[str],
        experience_level: Optional[str],
        limit: int,
    ) -> list[Job]:
        """Return sample LinkedIn-style jobs for development/testing."""
        sample_jobs = [
            Job(
                id="linkedin_sample_1",
                title=f"Senior {query} Engineer",
                company="Google",
                location=location or "Mountain View, CA",
                description=f"Join Google as a {query} Engineer! "
                           f"Work on world-scale systems and cutting-edge {query} projects. "
                           "Benefits include competitive salary, stock options, and amazing perks.",
                salary_min=180000,
                salary_max=280000,
                source="linkedin",
                source_url="https://linkedin.com/jobs/sample1",
                remote_option=True,
                company_size="10000+",
                industry="Technology",
                required_skills=[query, "Distributed Systems", "Python", "Go"],
                preferred_skills=["Machine Learning", "Kubernetes"],
                experience_level=experience_level or "senior",
                benefits=["Health Insurance", "401k Match", "Stock Options", "Unlimited PTO"],
            ),
            Job(
                id="linkedin_sample_2",
                title=f"{query} Team Lead",
                company="Meta",
                location=location or "Menlo Park, CA",
                description=f"Lead a team of {query} engineers building products used by billions. "
                           "Drive technical direction and mentor team members.",
                salary_min=200000,
                salary_max=320000,
                source="linkedin",
                source_url="https://linkedin.com/jobs/sample2",
                remote_option=True,
                company_size="10000+",
                industry="Technology",
                required_skills=[query, "Leadership", "System Design"],
                experience_level="senior",
            ),
            Job(
                id="linkedin_sample_3",
                title=f"{query} Developer",
                company="Stripe",
                location=location or "San Francisco, CA",
                description=f"Build the economic infrastructure of the internet with {query}. "
                           "Work on payments, fraud detection, and financial APIs.",
                salary_min=160000,
                salary_max=240000,
                source="linkedin",
                source_url="https://linkedin.com/jobs/sample3",
                remote_option=True,
                company_size="1000-5000",
                industry="FinTech",
                required_skills=[query, "Ruby", "AWS", "PostgreSQL"],
                experience_level="mid",
            ),
            Job(
                id="linkedin_sample_4",
                title=f"Principal {query} Architect",
                company="Amazon",
                location=location or "Seattle, WA",
                description=f"Define the future of {query} at scale. "
                           "Architect systems that serve millions of customers.",
                salary_min=220000,
                salary_max=350000,
                source="linkedin",
                source_url="https://linkedin.com/jobs/sample4",
                remote_option=False,
                company_size="10000+",
                industry="Technology",
                required_skills=[query, "AWS", "Architecture", "Leadership"],
                experience_level="senior",
            ),
            Job(
                id="linkedin_sample_5",
                title=f"{query} Engineer - Early Stage Startup",
                company="Innovative AI Labs",
                location=location or "Remote",
                description=f"Join our Series A startup as an early {query} engineer. "
                           "Significant equity and opportunity to shape the company.",
                salary_min=140000,
                salary_max=180000,
                source="linkedin",
                source_url="https://linkedin.com/jobs/sample5",
                remote_option=True,
                company_size="10-50",
                industry="AI/ML",
                required_skills=[query, "Python", "Fast Learner"],
                experience_level="mid",
            ),
        ]
        return sample_jobs[:limit]
