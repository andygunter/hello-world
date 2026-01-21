"""
Auto Apply Module - Automated job application submission with safeguards.

IMPORTANT: This module is designed for use with job boards that explicitly
allow automated applications through their API. Always review terms of service
before using automated application features.

The module includes multiple safeguards:
1. Rate limiting to prevent spam
2. User confirmation before submission
3. Dry-run mode for testing
4. Logging of all actions
5. Easy-apply API preference (Greenhouse, Lever, etc.)
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Callable
import json
import logging
import time

from job_matcher.core.models import Application, ApplicationStatus, UserProfile


class AutoApplicant:
    """
    Handles automated job application submission with safety controls.

    This class prioritizes API-based applications (Greenhouse, Lever) which
    explicitly support programmatic submissions.
    """

    # Rate limits (applications per time period)
    DEFAULT_RATE_LIMIT = 10  # applications per hour
    COOLDOWN_SECONDS = 60  # minimum time between applications

    def __init__(
        self,
        profile: UserProfile,
        dry_run: bool = True,
        rate_limit: int = None,
        require_confirmation: bool = True,
        log_dir: str = "./application_logs",
    ):
        """
        Initialize the auto applicant.

        Args:
            profile: User profile for applications
            dry_run: If True, simulates applications without submitting
            rate_limit: Max applications per hour
            require_confirmation: If True, requires user confirmation
            log_dir: Directory for application logs
        """
        self.profile = profile
        self.dry_run = dry_run
        self.rate_limit = rate_limit or self.DEFAULT_RATE_LIMIT
        self.require_confirmation = require_confirmation

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(self.__class__.__name__)

        # Track applications for rate limiting
        self._application_times: list[datetime] = []
        self._last_application: Optional[datetime] = None

        # Confirmation callback (can be overridden)
        self._confirmation_callback: Optional[Callable] = None

    def set_confirmation_callback(self, callback: Callable[[Application], bool]) -> None:
        """Set a custom confirmation callback function."""
        self._confirmation_callback = callback

    def apply(
        self,
        application: Application,
        resume_content: str,
        cover_letter_content: str,
    ) -> tuple[bool, str]:
        """
        Submit a job application.

        Args:
            application: Application to submit
            resume_content: Resume content
            cover_letter_content: Cover letter content

        Returns:
            Tuple of (success, message)
        """
        # Check rate limits
        if not self._check_rate_limit():
            return False, "Rate limit exceeded. Please wait before applying to more jobs."

        # Check cooldown
        if not self._check_cooldown():
            wait_time = self.COOLDOWN_SECONDS - (datetime.now() - self._last_application).seconds
            return False, f"Please wait {wait_time} seconds before the next application."

        # Require confirmation if enabled
        if self.require_confirmation:
            if not self._get_confirmation(application):
                return False, "Application cancelled by user."

        # Log the application attempt
        self._log_application_attempt(application)

        # Dry run mode
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would apply to: {application.job.title} at {application.job.company}")
            self._record_application()
            return True, f"[DRY RUN] Application simulated for {application.job.company}"

        # Attempt to apply based on source
        source = application.job.source.lower()

        if source == "greenhouse":
            success, message = self._apply_greenhouse(application, resume_content, cover_letter_content)
        elif source == "lever":
            success, message = self._apply_lever(application, resume_content, cover_letter_content)
        elif source in ["indeed", "linkedin", "glassdoor"]:
            # These typically don't allow direct API applications
            success, message = self._prepare_manual_application(application)
        else:
            success, message = self._prepare_manual_application(application)

        if success:
            self._record_application()
            application.status = ApplicationStatus.APPLIED
            application.applied_at = datetime.now()

        return success, message

    def _apply_greenhouse(
        self,
        application: Application,
        resume_content: str,
        cover_letter_content: str,
    ) -> tuple[bool, str]:
        """
        Apply via Greenhouse API.

        Greenhouse allows applications through their API when companies enable it.
        """
        try:
            import requests

            # Parse job ID from our format
            job_id = application.job.id.replace("greenhouse_", "")
            parts = job_id.split("_", 1)
            if len(parts) != 2:
                return False, "Invalid Greenhouse job ID format"

            company_id, gh_job_id = parts

            # Greenhouse application endpoint
            url = f"https://boards-api.greenhouse.io/v1/boards/{company_id}/jobs/{gh_job_id}/applications"

            # Prepare application data
            data = {
                "first_name": self.profile.full_name.split()[0],
                "last_name": " ".join(self.profile.full_name.split()[1:]) or self.profile.full_name,
                "email": self.profile.email,
                "phone": self.profile.phone,
                "resume_text": resume_content,
                "cover_letter": cover_letter_content,
                "location": self.profile.location,
            }

            # Add social links if available
            if self.profile.linkedin_url:
                data["linkedin_profile_url"] = self.profile.linkedin_url
            if self.profile.github_url:
                data["website_url"] = self.profile.github_url

            headers = {
                "Content-Type": "application/json",
            }

            response = requests.post(url, json=data, headers=headers, timeout=30)

            if response.status_code in [200, 201]:
                return True, f"Successfully applied to {application.job.company} via Greenhouse"
            elif response.status_code == 400:
                return False, f"Application rejected: {response.text}"
            else:
                return False, f"Greenhouse API error: {response.status_code}"

        except ImportError:
            return self._prepare_manual_application(application)
        except Exception as e:
            self.logger.error(f"Greenhouse application error: {e}")
            return False, f"Application failed: {str(e)}"

    def _apply_lever(
        self,
        application: Application,
        resume_content: str,
        cover_letter_content: str,
    ) -> tuple[bool, str]:
        """
        Apply via Lever API.

        Lever provides a postings API that can accept applications.
        """
        try:
            import requests

            # Parse job ID
            job_id = application.job.id.replace("lever_", "")
            parts = job_id.split("_", 1)
            if len(parts) != 2:
                return False, "Invalid Lever job ID format"

            company_id, lever_job_id = parts

            # Lever apply endpoint
            url = f"https://api.lever.co/v0/postings/{company_id}/{lever_job_id}/apply"

            # Prepare form data
            data = {
                "name": self.profile.full_name,
                "email": self.profile.email,
                "phone": self.profile.phone,
                "org": application.job.company,  # Current employer
                "resume": resume_content,
                "comments": cover_letter_content,
            }

            # Add URLs
            urls = {}
            if self.profile.linkedin_url:
                urls["LinkedIn"] = self.profile.linkedin_url
            if self.profile.github_url:
                urls["GitHub"] = self.profile.github_url
            if self.profile.portfolio_url:
                urls["Portfolio"] = self.profile.portfolio_url

            if urls:
                data["urls"] = urls

            response = requests.post(url, data=data, timeout=30)

            if response.status_code in [200, 201]:
                return True, f"Successfully applied to {application.job.company} via Lever"
            else:
                return False, f"Lever API error: {response.status_code}"

        except ImportError:
            return self._prepare_manual_application(application)
        except Exception as e:
            self.logger.error(f"Lever application error: {e}")
            return False, f"Application failed: {str(e)}"

    def _prepare_manual_application(
        self,
        application: Application,
    ) -> tuple[bool, str]:
        """
        Prepare materials for manual application.

        For job boards that don't support API applications, we prepare
        the materials and provide the user with instructions.
        """
        # Save application materials to a folder
        job_folder = self.log_dir / f"{application.job.company}_{application.job.id}"
        job_folder.mkdir(parents=True, exist_ok=True)

        # Create application instructions
        instructions = f"""
# Manual Application Required

**Company:** {application.job.company}
**Position:** {application.job.title}
**Location:** {application.job.location}

## Application URL
{application.job.source_url}

## Your Match Analysis
- Overall Match: {application.match_score.overall_score:.0f}%
- Hiring Likelihood: {application.match_score.hiring_likelihood:.0f}%
- Matched Skills: {', '.join(application.match_score.matched_skills)}

## Documents Prepared
- Resume: {application.customized_resume_path}
- Cover Letter: {application.customized_cover_letter_path}

## Instructions
1. Open the application URL above
2. Create an account or log in if required
3. Upload or paste your customized resume
4. Upload or paste your customized cover letter
5. Fill in any additional required fields
6. Submit your application
7. Update the status in Job Matcher after applying

---
Prepared by Job Matcher on {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""

        instructions_path = job_folder / "APPLICATION_INSTRUCTIONS.md"
        with open(instructions_path, 'w') as f:
            f.write(instructions)

        self.logger.info(f"Prepared manual application for {application.job.company}")

        return True, f"Manual application prepared. See: {instructions_path}"

    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        # Remove applications older than 1 hour
        one_hour_ago = datetime.now() - timedelta(hours=1)
        self._application_times = [
            t for t in self._application_times if t > one_hour_ago
        ]

        return len(self._application_times) < self.rate_limit

    def _check_cooldown(self) -> bool:
        """Check if cooldown period has passed."""
        if self._last_application is None:
            return True

        elapsed = (datetime.now() - self._last_application).total_seconds()
        return elapsed >= self.COOLDOWN_SECONDS

    def _record_application(self) -> None:
        """Record an application for rate limiting."""
        now = datetime.now()
        self._application_times.append(now)
        self._last_application = now

    def _get_confirmation(self, application: Application) -> bool:
        """Get user confirmation before applying."""
        if self._confirmation_callback:
            return self._confirmation_callback(application)

        # Default console confirmation
        print(f"\n{'='*60}")
        print(f"CONFIRM APPLICATION")
        print(f"{'='*60}")
        print(f"Company: {application.job.company}")
        print(f"Position: {application.job.title}")
        print(f"Location: {application.job.location}")
        print(f"Match Score: {application.match_score.overall_score:.0f}%")
        print(f"Hiring Likelihood: {application.match_score.hiring_likelihood:.0f}%")
        print(f"{'='*60}")

        response = input("Proceed with application? (y/n): ").strip().lower()
        return response in ['y', 'yes']

    def _log_application_attempt(self, application: Application) -> None:
        """Log application attempt for audit trail."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "job_id": application.job.id,
            "company": application.job.company,
            "title": application.job.title,
            "source": application.job.source,
            "dry_run": self.dry_run,
            "match_score": application.match_score.overall_score,
        }

        log_file = self.log_dir / "application_log.jsonl"
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + "\n")

    def apply_batch(
        self,
        applications: list[Application],
        resume_contents: dict[str, str],
        cover_letter_contents: dict[str, str],
        max_applications: int = 10,
    ) -> list[tuple[Application, bool, str]]:
        """
        Apply to multiple jobs with rate limiting.

        Args:
            applications: List of applications
            resume_contents: Dict mapping application ID to resume content
            cover_letter_contents: Dict mapping application ID to cover letter content
            max_applications: Maximum applications in this batch

        Returns:
            List of (application, success, message) tuples
        """
        results = []

        # Sort by hiring likelihood (best first)
        sorted_apps = sorted(
            applications,
            key=lambda a: a.match_score.hiring_likelihood,
            reverse=True
        )

        for app in sorted_apps[:max_applications]:
            resume = resume_contents.get(app.id, "")
            cover_letter = cover_letter_contents.get(app.id, "")

            success, message = self.apply(app, resume, cover_letter)
            results.append((app, success, message))

            # Wait between applications
            if not self.dry_run:
                time.sleep(5)  # 5 second delay between real applications

        return results

    def get_application_stats(self) -> dict:
        """Get statistics about application attempts."""
        log_file = self.log_dir / "application_log.jsonl"

        if not log_file.exists():
            return {"total_attempts": 0}

        attempts = []
        with open(log_file, 'r') as f:
            for line in f:
                if line.strip():
                    attempts.append(json.loads(line))

        return {
            "total_attempts": len(attempts),
            "dry_run_attempts": len([a for a in attempts if a.get("dry_run")]),
            "real_attempts": len([a for a in attempts if not a.get("dry_run")]),
            "by_source": self._count_by_field(attempts, "source"),
            "recent_attempts": attempts[-10:] if attempts else [],
        }

    def _count_by_field(self, items: list[dict], field: str) -> dict:
        """Count items by a specific field."""
        counts = {}
        for item in items:
            value = item.get(field, "unknown")
            counts[value] = counts.get(value, 0) + 1
        return counts
