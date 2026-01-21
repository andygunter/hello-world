"""
Document Manager - Coordinates resume and cover letter generation.
"""

from pathlib import Path
from typing import Optional
import json
import logging

from .resume_generator import ResumeGenerator
from .cover_letter_generator import CoverLetterGenerator
from job_matcher.core.models import UserProfile, Job, MatchScore, Application


class DocumentManager:
    """Manages document generation for job applications."""

    def __init__(
        self,
        output_dir: str = "./generated_documents",
        ai_api_key: Optional[str] = None,
    ):
        """
        Initialize the document manager.

        Args:
            output_dir: Base directory for all generated documents
            ai_api_key: Optional API key for AI-powered generation
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.resume_generator = ResumeGenerator(
            output_dir=str(self.output_dir / "resumes"),
            ai_api_key=ai_api_key,
        )

        self.cover_letter_generator = CoverLetterGenerator(
            output_dir=str(self.output_dir / "cover_letters"),
            ai_api_key=ai_api_key,
        )

        self.logger = logging.getLogger(self.__class__.__name__)

    def generate_application_documents(
        self,
        application: Application,
        formats: list[str] = None,
        use_ai: bool = True,
    ) -> Application:
        """
        Generate all documents for a job application.

        Args:
            application: Application with job and profile info
            formats: List of formats to generate (default: ["markdown"])
            use_ai: Whether to use AI for generation

        Returns:
            Updated Application with document paths
        """
        formats = formats or ["markdown"]
        primary_format = formats[0]

        try:
            # Generate resume
            resume_path, resume_content = self.resume_generator.generate(
                profile=application.profile,
                job=application.job,
                match_score=application.match_score,
                format=primary_format,
                use_ai=use_ai,
            )
            application.customized_resume_path = resume_path
            application.customized_resume_content = resume_content

            # Generate cover letter
            cl_path, cl_content = self.cover_letter_generator.generate(
                profile=application.profile,
                job=application.job,
                match_score=application.match_score,
                format=primary_format,
                use_ai=use_ai,
            )
            application.customized_cover_letter_path = cl_path
            application.customized_cover_letter_content = cl_content

            # Generate additional formats if requested
            for fmt in formats[1:]:
                self.resume_generator.generate(
                    profile=application.profile,
                    job=application.job,
                    match_score=application.match_score,
                    format=fmt,
                    use_ai=False,  # Don't re-run AI for alternate formats
                )
                self.cover_letter_generator.generate(
                    profile=application.profile,
                    job=application.job,
                    match_score=application.match_score,
                    format=fmt,
                    use_ai=False,
                )

            self.logger.info(
                f"Generated documents for {application.job.title} at {application.job.company}"
            )

        except Exception as e:
            self.logger.error(f"Document generation failed: {e}")
            raise

        return application

    def generate_batch_documents(
        self,
        profile: UserProfile,
        jobs_with_scores: list[tuple[Job, MatchScore]],
        use_ai: bool = True,
        format: str = "markdown",
    ) -> list[Application]:
        """
        Generate documents for multiple job applications.

        Args:
            profile: User profile
            jobs_with_scores: List of (job, match_score) tuples
            use_ai: Whether to use AI
            format: Output format

        Returns:
            List of Applications with generated documents
        """
        applications = []

        for job, match_score in jobs_with_scores:
            application = Application(
                job=job,
                profile=profile,
                match_score=match_score,
            )

            try:
                application = self.generate_application_documents(
                    application=application,
                    formats=[format],
                    use_ai=use_ai,
                )
                applications.append(application)
            except Exception as e:
                self.logger.error(
                    f"Failed to generate documents for {job.company}: {e}"
                )
                # Add with empty documents
                applications.append(application)

        return applications

    def export_documents_index(self, applications: list[Application]) -> str:
        """
        Create an index file of all generated documents.

        Args:
            applications: List of applications with documents

        Returns:
            Path to the index file
        """
        index = {
            "generated_at": str(__import__('datetime').datetime.now()),
            "total_applications": len(applications),
            "applications": [],
        }

        for app in applications:
            index["applications"].append({
                "job_id": app.job.id,
                "company": app.job.company,
                "title": app.job.title,
                "resume_path": app.customized_resume_path,
                "cover_letter_path": app.customized_cover_letter_path,
                "match_score": app.match_score.overall_score,
                "hiring_likelihood": app.match_score.hiring_likelihood,
            })

        index_path = self.output_dir / "documents_index.json"
        with open(index_path, 'w') as f:
            json.dump(index, f, indent=2)

        return str(index_path)
