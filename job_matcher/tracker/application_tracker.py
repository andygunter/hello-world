"""
Application Tracker - Manages job application lifecycle and status tracking.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional
import json
import logging

from job_matcher.core.models import Application, ApplicationStatus, Job, MatchScore, UserProfile


class ApplicationTracker:
    """Tracks and manages job applications throughout their lifecycle."""

    def __init__(self, storage_path: str = "./application_data"):
        """
        Initialize the application tracker.

        Args:
            storage_path: Directory for storing application data
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.applications: dict[str, Application] = {}
        self.logger = logging.getLogger(self.__class__.__name__)

        # Load existing applications
        self._load_applications()

    def add_application(self, application: Application) -> str:
        """
        Add a new application to track.

        Args:
            application: Application to track

        Returns:
            Application ID
        """
        self.applications[application.id] = application
        self._save_application(application)
        self.logger.info(f"Added application: {application.job.title} at {application.job.company}")
        return application.id

    def create_application(
        self,
        job: Job,
        profile: UserProfile,
        match_score: MatchScore,
    ) -> Application:
        """
        Create and track a new application.

        Args:
            job: Job being applied to
            profile: User profile
            match_score: Match analysis

        Returns:
            Created Application
        """
        application = Application(
            job=job,
            profile=profile,
            match_score=match_score,
            status=ApplicationStatus.IDENTIFIED,
        )

        self.add_application(application)
        return application

    def update_status(
        self,
        application_id: str,
        status: ApplicationStatus,
        note: Optional[str] = None,
    ) -> Optional[Application]:
        """
        Update the status of an application.

        Args:
            application_id: ID of the application
            status: New status
            note: Optional note to add

        Returns:
            Updated Application or None if not found
        """
        if application_id not in self.applications:
            self.logger.warning(f"Application not found: {application_id}")
            return None

        application = self.applications[application_id]
        old_status = application.status
        application.status = status
        application.last_updated = datetime.now()

        if note:
            application.notes.append(f"[{datetime.now().isoformat()}] {note}")

        # Track specific status changes
        if status == ApplicationStatus.APPLIED and old_status != ApplicationStatus.APPLIED:
            application.applied_at = datetime.now()

        if status in [ApplicationStatus.UNDER_REVIEW, ApplicationStatus.INTERVIEW_SCHEDULED]:
            application.response_received = True
            application.response_date = datetime.now()

        self._save_application(application)
        self.logger.info(f"Updated {application.job.company}: {old_status.value} -> {status.value}")

        return application

    def add_interview(
        self,
        application_id: str,
        interview_date: datetime,
        note: Optional[str] = None,
    ) -> Optional[Application]:
        """
        Add an interview date to an application.

        Args:
            application_id: ID of the application
            interview_date: Date/time of the interview
            note: Optional note

        Returns:
            Updated Application or None if not found
        """
        if application_id not in self.applications:
            return None

        application = self.applications[application_id]
        application.interview_dates.append(interview_date)
        application.status = ApplicationStatus.INTERVIEW_SCHEDULED
        application.response_received = True

        if note:
            application.notes.append(f"[{datetime.now().isoformat()}] Interview: {note}")

        self._save_application(application)
        return application

    def get_application(self, application_id: str) -> Optional[Application]:
        """Get an application by ID."""
        return self.applications.get(application_id)

    def get_applications_by_status(self, status: ApplicationStatus) -> list[Application]:
        """Get all applications with a specific status."""
        return [app for app in self.applications.values() if app.status == status]

    def get_all_applications(self) -> list[Application]:
        """Get all tracked applications."""
        return list(self.applications.values())

    def get_active_applications(self) -> list[Application]:
        """Get applications that are still in progress."""
        inactive_statuses = [
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
            ApplicationStatus.OFFER_RECEIVED,
        ]
        return [app for app in self.applications.values() if app.status not in inactive_statuses]

    def get_statistics(self) -> dict:
        """Get statistics about tracked applications."""
        total = len(self.applications)

        if total == 0:
            return {
                "total": 0,
                "by_status": {},
                "average_match_score": 0,
                "average_hiring_likelihood": 0,
                "response_rate": 0,
            }

        by_status = {}
        for status in ApplicationStatus:
            count = len(self.get_applications_by_status(status))
            if count > 0:
                by_status[status.value] = count

        # Calculate averages
        match_scores = [app.match_score.overall_score for app in self.applications.values()]
        hiring_likelihoods = [app.match_score.hiring_likelihood for app in self.applications.values()]

        # Response rate
        responded = len([app for app in self.applications.values() if app.response_received])
        applied = len([app for app in self.applications.values()
                      if app.status != ApplicationStatus.IDENTIFIED])

        return {
            "total": total,
            "by_status": by_status,
            "average_match_score": sum(match_scores) / total if match_scores else 0,
            "average_hiring_likelihood": sum(hiring_likelihoods) / total if hiring_likelihoods else 0,
            "response_rate": (responded / applied * 100) if applied > 0 else 0,
            "active_applications": len(self.get_active_applications()),
        }

    def search_applications(
        self,
        company: Optional[str] = None,
        title: Optional[str] = None,
        min_score: Optional[float] = None,
        status: Optional[ApplicationStatus] = None,
    ) -> list[Application]:
        """
        Search applications by various criteria.

        Args:
            company: Company name filter
            title: Job title filter
            min_score: Minimum match score
            status: Status filter

        Returns:
            List of matching applications
        """
        results = list(self.applications.values())

        if company:
            company_lower = company.lower()
            results = [app for app in results if company_lower in app.job.company.lower()]

        if title:
            title_lower = title.lower()
            results = [app for app in results if title_lower in app.job.title.lower()]

        if min_score is not None:
            results = [app for app in results if app.match_score.overall_score >= min_score]

        if status:
            results = [app for app in results if app.status == status]

        return results

    def get_top_opportunities(self, limit: int = 10, sort_by: str = "hiring_likelihood") -> list[Application]:
        """
        Get top opportunities sorted by specified criteria.

        Args:
            limit: Maximum number to return
            sort_by: Sort criteria (hiring_likelihood, overall_score, compensation)

        Returns:
            List of top applications
        """
        active = self.get_active_applications()

        sort_keys = {
            "hiring_likelihood": lambda a: a.match_score.hiring_likelihood,
            "overall_score": lambda a: a.match_score.overall_score,
            "compensation": lambda a: a.match_score.compensation_score,
            "skill_match": lambda a: a.match_score.skill_match_score,
        }

        key_func = sort_keys.get(sort_by, sort_keys["hiring_likelihood"])
        sorted_apps = sorted(active, key=key_func, reverse=True)

        return sorted_apps[:limit]

    def remove_application(self, application_id: str) -> bool:
        """
        Remove an application from tracking.

        Args:
            application_id: ID of the application to remove

        Returns:
            True if removed, False if not found
        """
        if application_id not in self.applications:
            return False

        del self.applications[application_id]

        # Remove file
        filepath = self.storage_path / f"{application_id}.json"
        if filepath.exists():
            filepath.unlink()

        return True

    def _save_application(self, application: Application) -> None:
        """Save an application to disk."""
        filepath = self.storage_path / f"{application.id}.json"

        data = application.to_dict()
        # Add profile ID reference instead of full profile
        data["profile_id"] = application.profile.id

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def _load_applications(self) -> None:
        """Load all saved applications from disk."""
        for filepath in self.storage_path.glob("*.json"):
            if filepath.name == "index.json":
                continue

            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)

                application = self._dict_to_application(data)
                self.applications[application.id] = application

            except Exception as e:
                self.logger.error(f"Error loading {filepath}: {e}")

        self.logger.info(f"Loaded {len(self.applications)} applications")

    def _dict_to_application(self, data: dict) -> Application:
        """Convert a dictionary to an Application object."""
        # Parse job
        job_data = data.get("job", {})
        job = Job(
            id=job_data.get("id", ""),
            title=job_data.get("title", ""),
            company=job_data.get("company", ""),
            location=job_data.get("location", ""),
            description=job_data.get("description", ""),
            required_skills=job_data.get("required_skills", []),
            preferred_skills=job_data.get("preferred_skills", []),
            salary_min=job_data.get("salary_min"),
            salary_max=job_data.get("salary_max"),
            source=job_data.get("source", ""),
            source_url=job_data.get("source_url", ""),
        )

        # Parse match score
        score_data = data.get("match_score", {})
        match_score = MatchScore(
            overall_score=score_data.get("overall_score", 0),
            skill_match_score=score_data.get("skill_match_score", 0),
            experience_match_score=score_data.get("experience_match_score", 0),
            education_match_score=score_data.get("education_match_score", 0),
            location_match_score=score_data.get("location_match_score", 0),
            salary_match_score=score_data.get("salary_match_score", 0),
            hiring_likelihood=score_data.get("hiring_likelihood", 0),
            compensation_score=score_data.get("compensation_score", 0),
            matched_skills=score_data.get("matched_skills", []),
            missing_skills=score_data.get("missing_skills", []),
            bonus_skills=score_data.get("bonus_skills", []),
        )

        # Parse dates
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        else:
            created_at = datetime.now()

        applied_at = data.get("applied_at")
        if isinstance(applied_at, str):
            applied_at = datetime.fromisoformat(applied_at)

        return Application(
            id=data.get("id", ""),
            job=job,
            profile=UserProfile(),  # Profile loaded separately
            match_score=match_score,
            status=ApplicationStatus(data.get("status", "identified")),
            customized_resume_path=data.get("customized_resume_path", ""),
            customized_cover_letter_path=data.get("customized_cover_letter_path", ""),
            created_at=created_at,
            applied_at=applied_at,
            notes=data.get("notes", []),
            response_received=data.get("response_received", False),
        )

    def export_to_csv(self, filepath: Optional[str] = None) -> str:
        """
        Export all applications to CSV format.

        Args:
            filepath: Optional custom path for the CSV file

        Returns:
            Path to the exported CSV file
        """
        if filepath is None:
            filepath = str(self.storage_path / "applications_export.csv")

        import csv

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                "ID", "Company", "Title", "Location", "Status",
                "Match Score", "Hiring Likelihood", "Compensation Score",
                "Applied Date", "Response Received", "Source", "URL",
                "Matched Skills", "Missing Skills",
            ])

            # Data rows
            for app in self.applications.values():
                writer.writerow([
                    app.id,
                    app.job.company,
                    app.job.title,
                    app.job.location,
                    app.status.value,
                    f"{app.match_score.overall_score:.1f}",
                    f"{app.match_score.hiring_likelihood:.1f}%",
                    f"{app.match_score.compensation_score:.1f}",
                    app.applied_at.isoformat() if app.applied_at else "",
                    "Yes" if app.response_received else "No",
                    app.job.source,
                    app.job.source_url,
                    ", ".join(app.match_score.matched_skills),
                    ", ".join(app.match_score.missing_skills),
                ])

        self.logger.info(f"Exported {len(self.applications)} applications to {filepath}")
        return filepath
