"""
Job Aggregator - Combines results from multiple job search providers.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional
import logging

from .base import JobSearchProvider
from .indeed import IndeedProvider
from .linkedin import LinkedInProvider
from .glassdoor import GlassdoorProvider
from .greenhouse import GreenhouseProvider
from .lever import LeverProvider
from job_matcher.core.models import Job, UserProfile


class JobAggregator:
    """Aggregates job listings from multiple providers."""

    def __init__(self, config: Optional[dict] = None):
        """
        Initialize the job aggregator with optional API keys.

        Args:
            config: Dictionary containing API keys for providers
                   e.g., {"linkedin_api_key": "...", "indeed_api_key": "..."}
        """
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)

        # Initialize providers
        self.providers: list[JobSearchProvider] = [
            IndeedProvider(api_key=self.config.get("indeed_api_key")),
            LinkedInProvider(api_key=self.config.get("linkedin_api_key")),
            GlassdoorProvider(api_key=self.config.get("glassdoor_api_key")),
            GreenhouseProvider(),
            LeverProvider(),
        ]

    def add_provider(self, provider: JobSearchProvider) -> None:
        """Add a custom job search provider."""
        self.providers.append(provider)

    def remove_provider(self, name: str) -> bool:
        """Remove a provider by name."""
        for i, provider in enumerate(self.providers):
            if provider.name.lower() == name.lower():
                self.providers.pop(i)
                return True
        return False

    def get_available_providers(self) -> list[str]:
        """Get list of available (properly configured) providers."""
        return [p.name for p in self.providers if p.is_available()]

    def search_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        remote: bool = False,
        job_type: Optional[str] = None,
        experience_level: Optional[str] = None,
        salary_min: Optional[int] = None,
        limit: int = 100,
        providers: Optional[list[str]] = None,
        parallel: bool = True,
    ) -> list[Job]:
        """
        Search for jobs across all (or specified) providers.

        Args:
            query: Search query
            location: Location filter
            remote: Remote jobs only
            job_type: Type of employment
            experience_level: Required experience level
            salary_min: Minimum salary
            limit: Max total results
            providers: Specific providers to use (None = all)
            parallel: Whether to search providers in parallel

        Returns:
            Combined list of jobs from all providers
        """
        # Filter providers
        active_providers = self.providers
        if providers:
            providers_lower = [p.lower() for p in providers]
            active_providers = [
                p for p in self.providers
                if p.name.lower() in providers_lower and p.is_available()
            ]

        if not active_providers:
            self.logger.warning("No active providers available")
            return []

        # Calculate limit per provider
        limit_per_provider = max(10, limit // len(active_providers))

        all_jobs = []

        if parallel:
            all_jobs = self._search_parallel(
                active_providers, query, location, remote,
                job_type, experience_level, salary_min, limit_per_provider
            )
        else:
            all_jobs = self._search_sequential(
                active_providers, query, location, remote,
                job_type, experience_level, salary_min, limit_per_provider
            )

        # Deduplicate by title + company
        seen = set()
        unique_jobs = []
        for job in all_jobs:
            key = f"{job.title.lower()}_{job.company.lower()}"
            if key not in seen:
                seen.add(key)
                unique_jobs.append(job)

        self.logger.info(f"Found {len(unique_jobs)} unique jobs from {len(active_providers)} providers")

        return unique_jobs[:limit]

    def _search_parallel(
        self,
        providers: list[JobSearchProvider],
        query: str,
        location: Optional[str],
        remote: bool,
        job_type: Optional[str],
        experience_level: Optional[str],
        salary_min: Optional[int],
        limit: int,
    ) -> list[Job]:
        """Search providers in parallel using thread pool."""
        all_jobs = []

        with ThreadPoolExecutor(max_workers=len(providers)) as executor:
            futures = {
                executor.submit(
                    self._search_provider,
                    provider, query, location, remote,
                    job_type, experience_level, salary_min, limit
                ): provider
                for provider in providers
            }

            for future in as_completed(futures):
                provider = futures[future]
                try:
                    jobs = future.result()
                    all_jobs.extend(jobs)
                    self.logger.debug(f"{provider.name}: Found {len(jobs)} jobs")
                except Exception as e:
                    self.logger.error(f"{provider.name} search failed: {e}")

        return all_jobs

    def _search_sequential(
        self,
        providers: list[JobSearchProvider],
        query: str,
        location: Optional[str],
        remote: bool,
        job_type: Optional[str],
        experience_level: Optional[str],
        salary_min: Optional[int],
        limit: int,
    ) -> list[Job]:
        """Search providers sequentially."""
        all_jobs = []

        for provider in providers:
            try:
                jobs = self._search_provider(
                    provider, query, location, remote,
                    job_type, experience_level, salary_min, limit
                )
                all_jobs.extend(jobs)
                self.logger.debug(f"{provider.name}: Found {len(jobs)} jobs")
            except Exception as e:
                self.logger.error(f"{provider.name} search failed: {e}")

        return all_jobs

    def _search_provider(
        self,
        provider: JobSearchProvider,
        query: str,
        location: Optional[str],
        remote: bool,
        job_type: Optional[str],
        experience_level: Optional[str],
        salary_min: Optional[int],
        limit: int,
    ) -> list[Job]:
        """Search a single provider."""
        return provider.search_jobs(
            query=query,
            location=location,
            remote=remote,
            job_type=job_type,
            experience_level=experience_level,
            salary_min=salary_min,
            limit=limit,
        )

    def search_for_profile(
        self,
        profile: UserProfile,
        limit: int = 100,
        providers: Optional[list[str]] = None,
    ) -> list[Job]:
        """
        Search for jobs matching a user profile across all providers.

        Args:
            profile: User profile to match
            limit: Maximum total results
            providers: Specific providers to use

        Returns:
            List of matching jobs
        """
        all_jobs = []

        # Search by desired roles
        for role in profile.desired_roles[:3]:
            results = self.search_jobs(
                query=role,
                location=profile.desired_locations[0] if profile.desired_locations else None,
                remote=profile.remote_preference in ["remote", "flexible"],
                salary_min=profile.min_salary,
                limit=limit // max(1, len(profile.desired_roles)),
                providers=providers,
            )
            all_jobs.extend(results)

        # Search by top skills if we have few results
        if len(all_jobs) < limit // 2:
            top_skills = sorted(
                profile.skills,
                key=lambda s: s.years_experience,
                reverse=True
            )[:2]

            for skill in top_skills:
                results = self.search_jobs(
                    query=skill.name,
                    location=profile.desired_locations[0] if profile.desired_locations else None,
                    remote=profile.remote_preference in ["remote", "flexible"],
                    limit=20,
                    providers=providers,
                )
                all_jobs.extend(results)

        # Deduplicate
        seen = set()
        unique_jobs = []
        for job in all_jobs:
            key = f"{job.title.lower()}_{job.company.lower()}"
            if key not in seen:
                seen.add(key)
                unique_jobs.append(job)

        return unique_jobs[:limit]

    def get_job_details(self, job_id: str) -> Optional[Job]:
        """
        Get detailed job information.

        Args:
            job_id: Job ID (includes provider prefix)

        Returns:
            Job with full details or None
        """
        # Determine provider from job ID prefix
        for provider in self.providers:
            prefix = provider.name.lower()
            if job_id.startswith(prefix):
                return provider.get_job_details(job_id)

        return None

    def get_stats(self) -> dict:
        """Get statistics about available providers."""
        return {
            "total_providers": len(self.providers),
            "available_providers": len(self.get_available_providers()),
            "providers": {
                p.name: {
                    "available": p.is_available(),
                    "requires_api_key": p.requires_api_key,
                }
                for p in self.providers
            },
        }
