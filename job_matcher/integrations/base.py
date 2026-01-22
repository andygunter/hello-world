"""
Base class for job search providers.
"""

from abc import ABC, abstractmethod
from typing import Optional
import logging

from job_matcher.core.models import Job, UserProfile


class JobSearchProvider(ABC):
    """Abstract base class for job search providers."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.logger = logging.getLogger(self.__class__.__name__)
        self._rate_limit_remaining = 100
        self._rate_limit_reset = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass

    @property
    @abstractmethod
    def requires_api_key(self) -> bool:
        """Whether this provider requires an API key."""
        pass

    @abstractmethod
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
        """
        Search for jobs matching the criteria.

        Args:
            query: Search query (job title, skills, etc.)
            location: Location filter
            remote: Filter for remote jobs only
            job_type: full_time, part_time, contract, etc.
            experience_level: entry, mid, senior, executive
            salary_min: Minimum salary filter
            limit: Maximum number of results

        Returns:
            List of matching Job objects
        """
        pass

    @abstractmethod
    def get_job_details(self, job_id: str) -> Optional[Job]:
        """
        Get detailed information about a specific job.

        Args:
            job_id: The job's unique identifier

        Returns:
            Job object with full details, or None if not found
        """
        pass

    def search_for_profile(
        self,
        profile: UserProfile,
        limit: int = 50,
    ) -> list[Job]:
        """
        Search for jobs matching a user profile.

        Args:
            profile: User profile to match against
            limit: Maximum number of results

        Returns:
            List of matching Job objects
        """
        jobs = []

        # Search by desired roles
        for role in profile.desired_roles[:3]:  # Limit to top 3 roles
            for location in profile.desired_locations[:2] or [None]:
                results = self.search_jobs(
                    query=role,
                    location=location,
                    remote=profile.remote_preference in ["remote", "flexible"],
                    salary_min=profile.min_salary,
                    limit=limit // len(profile.desired_roles or [1]),
                )
                jobs.extend(results)

        # Search by top skills if we need more results
        if len(jobs) < limit and profile.skills:
            top_skills = sorted(
                profile.skills,
                key=lambda s: s.years_experience,
                reverse=True
            )[:3]

            for skill in top_skills:
                results = self.search_jobs(
                    query=skill.name,
                    location=profile.desired_locations[0] if profile.desired_locations else None,
                    remote=profile.remote_preference in ["remote", "flexible"],
                    limit=10,
                )
                jobs.extend(results)

        # Deduplicate by job ID
        seen_ids = set()
        unique_jobs = []
        for job in jobs:
            if job.id not in seen_ids:
                seen_ids.add(job.id)
                unique_jobs.append(job)

        return unique_jobs[:limit]

    def is_available(self) -> bool:
        """Check if the provider is properly configured and available."""
        if self.requires_api_key and not self.api_key:
            return False
        return True

    def _handle_rate_limit(self, response) -> None:
        """Handle rate limit information from API response."""
        pass

    def _parse_salary(self, salary_text: str) -> tuple[Optional[int], Optional[int]]:
        """Parse salary range from text."""
        import re

        if not salary_text:
            return None, None

        # Remove currency symbols and commas
        clean = salary_text.replace('$', '').replace(',', '').replace('K', '000')

        # Find numbers
        numbers = re.findall(r'\d+', clean)

        if len(numbers) >= 2:
            return int(numbers[0]), int(numbers[1])
        elif len(numbers) == 1:
            return int(numbers[0]), int(numbers[0])

        return None, None
