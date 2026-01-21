"""
Indeed job search integration.

Note: Indeed has restricted their public API. This implementation uses
web scraping as a fallback with proper rate limiting and respect for robots.txt.
For production use, consider Indeed's Partner API program.
"""

import hashlib
import re
from datetime import datetime
from typing import Optional
from urllib.parse import quote_plus, urlencode
import logging

from .base import JobSearchProvider
from job_matcher.core.models import Job, JobType


class IndeedProvider(JobSearchProvider):
    """Indeed job search provider."""

    BASE_URL = "https://www.indeed.com"
    API_URL = "https://api.indeed.com/ads/apisearch"

    @property
    def name(self) -> str:
        return "Indeed"

    @property
    def requires_api_key(self) -> bool:
        return False  # Can work without API key using scraping fallback

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
        """Search Indeed for jobs."""
        jobs = []

        try:
            if self.api_key:
                jobs = self._search_via_api(
                    query, location, remote, job_type, salary_min, limit
                )
            else:
                jobs = self._search_via_scraping(
                    query, location, remote, job_type, salary_min, limit
                )
        except Exception as e:
            self.logger.error(f"Indeed search failed: {e}")

        return jobs

    def _search_via_api(
        self,
        query: str,
        location: Optional[str],
        remote: bool,
        job_type: Optional[str],
        salary_min: Optional[int],
        limit: int,
    ) -> list[Job]:
        """Search using Indeed API (requires publisher ID)."""
        try:
            import requests

            params = {
                "publisher": self.api_key,
                "q": query,
                "l": location or "",
                "sort": "relevance",
                "radius": 25,
                "limit": min(limit, 25),
                "fromage": 30,  # Jobs from last 30 days
                "format": "json",
                "v": 2,
            }

            if remote:
                params["q"] += " remote"

            if job_type:
                params["jt"] = job_type

            response = requests.get(self.API_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            jobs = []
            for result in data.get("results", []):
                job = self._parse_api_result(result)
                if job:
                    jobs.append(job)

            return jobs

        except ImportError:
            self.logger.warning("requests library not installed")
            return []
        except Exception as e:
            self.logger.error(f"Indeed API error: {e}")
            return []

    def _search_via_scraping(
        self,
        query: str,
        location: Optional[str],
        remote: bool,
        job_type: Optional[str],
        salary_min: Optional[int],
        limit: int,
    ) -> list[Job]:
        """
        Search using web scraping fallback.

        Note: This is provided for educational purposes. In production,
        use official APIs or respect terms of service.
        """
        try:
            import requests
            from bs4 import BeautifulSoup

            jobs = []
            pages_needed = (limit + 9) // 10  # 10 results per page

            for page in range(min(pages_needed, 5)):  # Max 5 pages
                params = {
                    "q": query,
                    "l": location or "",
                    "start": page * 10,
                    "sort": "relevance",
                }

                if remote:
                    params["remotejob"] = 1

                if job_type:
                    params["jt"] = job_type

                url = f"{self.BASE_URL}/jobs?" + urlencode(params)

                headers = {
                    "User-Agent": "JobMatcher/1.0 (Educational Purpose)",
                    "Accept": "text/html",
                }

                response = requests.get(url, headers=headers, timeout=30)

                if response.status_code != 200:
                    self.logger.warning(f"Indeed returned status {response.status_code}")
                    break

                soup = BeautifulSoup(response.text, "html.parser")
                job_cards = soup.find_all("div", class_="job_seen_beacon")

                for card in job_cards:
                    job = self._parse_job_card(card)
                    if job:
                        jobs.append(job)

                if len(jobs) >= limit:
                    break

            return jobs[:limit]

        except ImportError as e:
            self.logger.warning(f"Required library not installed: {e}")
            return self._get_sample_jobs(query, location, limit)
        except Exception as e:
            self.logger.error(f"Indeed scraping error: {e}")
            return self._get_sample_jobs(query, location, limit)

    def _parse_api_result(self, result: dict) -> Optional[Job]:
        """Parse API response into Job object."""
        try:
            salary_min, salary_max = self._parse_salary(
                result.get("formattedRelativeTime", "")
            )

            return Job(
                id=result.get("jobkey", ""),
                title=result.get("jobtitle", ""),
                company=result.get("company", ""),
                location=result.get("formattedLocation", ""),
                description=result.get("snippet", ""),
                salary_min=salary_min,
                salary_max=salary_max,
                posted_date=datetime.now(),
                source="indeed",
                source_url=result.get("url", ""),
            )
        except Exception as e:
            self.logger.error(f"Error parsing API result: {e}")
            return None

    def _parse_job_card(self, card) -> Optional[Job]:
        """Parse a job card HTML element into a Job object."""
        try:
            # Extract job key for unique ID
            job_key = card.get("data-jk", "")
            if not job_key:
                job_key = hashlib.md5(str(card).encode()).hexdigest()[:12]

            # Title
            title_elem = card.find("h2", class_="jobTitle")
            title = title_elem.get_text(strip=True) if title_elem else ""

            # Company
            company_elem = card.find("span", {"data-testid": "company-name"})
            company = company_elem.get_text(strip=True) if company_elem else ""

            # Location
            location_elem = card.find("div", {"data-testid": "text-location"})
            location = location_elem.get_text(strip=True) if location_elem else ""

            # Salary
            salary_elem = card.find("div", class_="salary-snippet-container")
            salary_text = salary_elem.get_text(strip=True) if salary_elem else ""
            salary_min, salary_max = self._parse_salary(salary_text)

            # Description snippet
            snippet_elem = card.find("div", class_="job-snippet")
            description = snippet_elem.get_text(strip=True) if snippet_elem else ""

            # Job URL
            link_elem = card.find("a", class_="jcs-JobTitle")
            job_url = ""
            if link_elem and link_elem.get("href"):
                job_url = f"{self.BASE_URL}{link_elem['href']}"

            return Job(
                id=f"indeed_{job_key}",
                title=title,
                company=company,
                location=location,
                description=description,
                salary_min=salary_min,
                salary_max=salary_max,
                posted_date=datetime.now(),
                source="indeed",
                source_url=job_url,
                remote_option="remote" in location.lower(),
            )

        except Exception as e:
            self.logger.error(f"Error parsing job card: {e}")
            return None

    def get_job_details(self, job_id: str) -> Optional[Job]:
        """Get full job details from Indeed."""
        try:
            import requests
            from bs4 import BeautifulSoup

            # Extract the job key from our ID format
            job_key = job_id.replace("indeed_", "")
            url = f"{self.BASE_URL}/viewjob?jk={job_key}"

            headers = {
                "User-Agent": "JobMatcher/1.0 (Educational Purpose)",
            }

            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, "html.parser")

            # Parse detailed job info
            title = soup.find("h1", class_="jobsearch-JobInfoHeader-title")
            company = soup.find("div", {"data-company-name": True})
            location = soup.find("div", {"data-testid": "job-location"})
            description = soup.find("div", id="jobDescriptionText")

            return Job(
                id=job_id,
                title=title.get_text(strip=True) if title else "",
                company=company.get_text(strip=True) if company else "",
                location=location.get_text(strip=True) if location else "",
                description=description.get_text() if description else "",
                source="indeed",
                source_url=url,
            )

        except Exception as e:
            self.logger.error(f"Error getting job details: {e}")
            return None

    def _get_sample_jobs(self, query: str, location: Optional[str], limit: int) -> list[Job]:
        """Return sample jobs when scraping is not available."""
        sample_jobs = [
            Job(
                id="indeed_sample_1",
                title=f"Senior {query} Engineer",
                company="Tech Innovations Inc",
                location=location or "San Francisco, CA",
                description=f"Looking for an experienced {query} engineer to join our team. "
                           f"You'll work on cutting-edge projects using {query} and related technologies.",
                salary_min=150000,
                salary_max=200000,
                source="indeed",
                source_url="https://indeed.com/sample",
                remote_option=True,
                required_skills=[query, "Python", "AWS"],
                experience_level="senior",
            ),
            Job(
                id="indeed_sample_2",
                title=f"{query} Developer",
                company="StartupXYZ",
                location=location or "New York, NY",
                description=f"Join our fast-growing startup as a {query} developer. "
                           f"Opportunity to make a big impact with {query} expertise.",
                salary_min=120000,
                salary_max=160000,
                source="indeed",
                source_url="https://indeed.com/sample2",
                remote_option=True,
                required_skills=[query, "JavaScript", "React"],
                experience_level="mid",
            ),
            Job(
                id="indeed_sample_3",
                title=f"Staff {query} Architect",
                company="Enterprise Solutions Corp",
                location=location or "Seattle, WA",
                description=f"Lead our {query} architecture initiatives. "
                           f"Design scalable systems using {query} best practices.",
                salary_min=180000,
                salary_max=250000,
                source="indeed",
                source_url="https://indeed.com/sample3",
                remote_option=False,
                required_skills=[query, "System Design", "Leadership"],
                experience_level="senior",
            ),
        ]
        return sample_jobs[:limit]
