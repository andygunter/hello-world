"""
Core data models for the job matching system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class ApplicationStatus(Enum):
    """Status of a job application."""
    IDENTIFIED = "identified"
    RESUME_GENERATED = "resume_generated"
    COVER_LETTER_GENERATED = "cover_letter_generated"
    READY_TO_APPLY = "ready_to_apply"
    APPLIED = "applied"
    UNDER_REVIEW = "under_review"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    REJECTED = "rejected"
    OFFER_RECEIVED = "offer_received"
    WITHDRAWN = "withdrawn"


class SkillLevel(Enum):
    """Proficiency level for a skill."""
    BEGINNER = 1
    INTERMEDIATE = 2
    ADVANCED = 3
    EXPERT = 4


class JobType(Enum):
    """Type of employment."""
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    FREELANCE = "freelance"
    INTERNSHIP = "internship"
    REMOTE = "remote"
    HYBRID = "hybrid"
    ON_SITE = "on_site"


@dataclass
class Skill:
    """Represents a professional skill."""
    name: str
    level: SkillLevel = SkillLevel.INTERMEDIATE
    years_experience: float = 0.0
    keywords: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "level": self.level.name,
            "years_experience": self.years_experience,
            "keywords": self.keywords,
        }


@dataclass
class Experience:
    """Represents a work experience entry."""
    title: str
    company: str
    start_date: datetime
    end_date: Optional[datetime] = None
    description: str = ""
    achievements: list[str] = field(default_factory=list)
    skills_used: list[str] = field(default_factory=list)
    location: str = ""
    is_current: bool = False

    @property
    def duration_years(self) -> float:
        end = self.end_date or datetime.now()
        return (end - self.start_date).days / 365.25

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "company": self.company,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "description": self.description,
            "achievements": self.achievements,
            "skills_used": self.skills_used,
            "location": self.location,
            "is_current": self.is_current,
            "duration_years": self.duration_years,
        }


@dataclass
class Education:
    """Represents an educational credential."""
    institution: str
    degree: str
    field_of_study: str
    graduation_date: Optional[datetime] = None
    gpa: Optional[float] = None
    honors: list[str] = field(default_factory=list)
    relevant_coursework: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "institution": self.institution,
            "degree": self.degree,
            "field_of_study": self.field_of_study,
            "graduation_date": self.graduation_date.isoformat() if self.graduation_date else None,
            "gpa": self.gpa,
            "honors": self.honors,
            "relevant_coursework": self.relevant_coursework,
        }


@dataclass
class UserProfile:
    """Complete user profile for job matching."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""
    summary: str = ""
    skills: list[Skill] = field(default_factory=list)
    experiences: list[Experience] = field(default_factory=list)
    education: list[Education] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    desired_roles: list[str] = field(default_factory=list)
    desired_locations: list[str] = field(default_factory=list)
    min_salary: Optional[int] = None
    max_commute_minutes: Optional[int] = None
    remote_preference: str = "flexible"  # remote, hybrid, on_site, flexible

    @property
    def total_experience_years(self) -> float:
        return sum(exp.duration_years for exp in self.experiences)

    @property
    def skill_names(self) -> list[str]:
        return [skill.name.lower() for skill in self.skills]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "location": self.location,
            "linkedin_url": self.linkedin_url,
            "github_url": self.github_url,
            "portfolio_url": self.portfolio_url,
            "summary": self.summary,
            "skills": [s.to_dict() for s in self.skills],
            "experiences": [e.to_dict() for e in self.experiences],
            "education": [e.to_dict() for e in self.education],
            "certifications": self.certifications,
            "languages": self.languages,
            "desired_roles": self.desired_roles,
            "desired_locations": self.desired_locations,
            "min_salary": self.min_salary,
            "max_commute_minutes": self.max_commute_minutes,
            "remote_preference": self.remote_preference,
            "total_experience_years": self.total_experience_years,
        }


@dataclass
class Job:
    """Represents a job posting."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    company: str = ""
    location: str = ""
    description: str = ""
    requirements: list[str] = field(default_factory=list)
    required_skills: list[str] = field(default_factory=list)
    preferred_skills: list[str] = field(default_factory=list)
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    job_type: JobType = JobType.FULL_TIME
    remote_option: bool = False
    posted_date: Optional[datetime] = None
    application_deadline: Optional[datetime] = None
    source: str = ""  # indeed, linkedin, glassdoor, etc.
    source_url: str = ""
    company_size: str = ""
    industry: str = ""
    experience_level: str = ""  # entry, mid, senior, executive
    benefits: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "description": self.description,
            "requirements": self.requirements,
            "required_skills": self.required_skills,
            "preferred_skills": self.preferred_skills,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "job_type": self.job_type.value,
            "remote_option": self.remote_option,
            "posted_date": self.posted_date.isoformat() if self.posted_date else None,
            "application_deadline": self.application_deadline.isoformat() if self.application_deadline else None,
            "source": self.source,
            "source_url": self.source_url,
            "company_size": self.company_size,
            "industry": self.industry,
            "experience_level": self.experience_level,
            "benefits": self.benefits,
        }


@dataclass
class MatchScore:
    """Scoring breakdown for a job match."""
    overall_score: float = 0.0  # 0-100
    skill_match_score: float = 0.0  # 0-100
    experience_match_score: float = 0.0  # 0-100
    education_match_score: float = 0.0  # 0-100
    location_match_score: float = 0.0  # 0-100
    salary_match_score: float = 0.0  # 0-100
    culture_fit_score: float = 0.0  # 0-100
    hiring_likelihood: float = 0.0  # 0-100 (estimated chance of getting hired)
    compensation_score: float = 0.0  # 0-100 (relative to market/expectations)

    # Detailed breakdowns
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    bonus_skills: list[str] = field(default_factory=list)  # skills you have beyond requirements

    def to_dict(self) -> dict:
        return {
            "overall_score": round(self.overall_score, 2),
            "skill_match_score": round(self.skill_match_score, 2),
            "experience_match_score": round(self.experience_match_score, 2),
            "education_match_score": round(self.education_match_score, 2),
            "location_match_score": round(self.location_match_score, 2),
            "salary_match_score": round(self.salary_match_score, 2),
            "culture_fit_score": round(self.culture_fit_score, 2),
            "hiring_likelihood": round(self.hiring_likelihood, 2),
            "compensation_score": round(self.compensation_score, 2),
            "matched_skills": self.matched_skills,
            "missing_skills": self.missing_skills,
            "bonus_skills": self.bonus_skills,
        }


@dataclass
class Application:
    """Represents a job application and its tracking data."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    job: Job = field(default_factory=Job)
    profile: UserProfile = field(default_factory=UserProfile)
    match_score: MatchScore = field(default_factory=MatchScore)
    status: ApplicationStatus = ApplicationStatus.IDENTIFIED

    # Generated documents
    customized_resume_path: str = ""
    customized_cover_letter_path: str = ""
    customized_resume_content: str = ""
    customized_cover_letter_content: str = ""

    # Tracking
    created_at: datetime = field(default_factory=datetime.now)
    applied_at: Optional[datetime] = None
    last_updated: datetime = field(default_factory=datetime.now)
    notes: list[str] = field(default_factory=list)

    # Response tracking
    response_received: bool = False
    response_date: Optional[datetime] = None
    interview_dates: list[datetime] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "job": self.job.to_dict(),
            "match_score": self.match_score.to_dict(),
            "status": self.status.value,
            "customized_resume_path": self.customized_resume_path,
            "customized_cover_letter_path": self.customized_cover_letter_path,
            "created_at": self.created_at.isoformat(),
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "last_updated": self.last_updated.isoformat(),
            "notes": self.notes,
            "response_received": self.response_received,
            "response_date": self.response_date.isoformat() if self.response_date else None,
            "interview_dates": [d.isoformat() for d in self.interview_dates],
            "hiring_likelihood_percent": f"{self.match_score.hiring_likelihood:.1f}%",
        }
