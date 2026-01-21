"""
Job Matcher - Scoring algorithm for matching jobs to user profiles.

Calculates multiple scores:
- Skill match: How well user skills match job requirements
- Experience match: Does user experience meet job requirements
- Education match: Does user education meet requirements
- Location match: Geographic compatibility
- Salary match: Does compensation meet expectations
- Hiring likelihood: Estimated probability of getting an offer
"""

from typing import Optional
import re

from .models import (
    UserProfile,
    Job,
    MatchScore,
    SkillLevel,
)


class JobMatcher:
    """Matches user profiles to job postings and calculates fit scores."""

    # Weights for overall score calculation
    WEIGHTS = {
        "skill_match": 0.35,
        "experience_match": 0.20,
        "education_match": 0.10,
        "location_match": 0.15,
        "salary_match": 0.20,
    }

    # Hiring likelihood factors
    HIRING_FACTORS = {
        "skill_match_weight": 0.40,
        "experience_weight": 0.25,
        "market_demand_weight": 0.15,
        "application_timing_weight": 0.10,
        "company_culture_weight": 0.10,
    }

    def __init__(self, profile: UserProfile):
        self.profile = profile

    def match_job(self, job: Job) -> MatchScore:
        """Calculate comprehensive match scores for a job."""
        score = MatchScore()

        # Calculate individual scores
        score.skill_match_score = self._calculate_skill_match(job)
        score.experience_match_score = self._calculate_experience_match(job)
        score.education_match_score = self._calculate_education_match(job)
        score.location_match_score = self._calculate_location_match(job)
        score.salary_match_score = self._calculate_salary_match(job)

        # Calculate overall score
        score.overall_score = (
            score.skill_match_score * self.WEIGHTS["skill_match"] +
            score.experience_match_score * self.WEIGHTS["experience_match"] +
            score.education_match_score * self.WEIGHTS["education_match"] +
            score.location_match_score * self.WEIGHTS["location_match"] +
            score.salary_match_score * self.WEIGHTS["salary_match"]
        )

        # Calculate hiring likelihood
        score.hiring_likelihood = self._calculate_hiring_likelihood(job, score)

        # Calculate compensation score
        score.compensation_score = self._calculate_compensation_score(job)

        # Get skill details
        score.matched_skills, score.missing_skills, score.bonus_skills = \
            self._get_skill_details(job)

        return score

    def _calculate_skill_match(self, job: Job) -> float:
        """Calculate skill match score (0-100)."""
        if not job.required_skills and not job.preferred_skills:
            # If no skills listed, do keyword matching on description
            return self._fuzzy_skill_match(job.description)

        required_matches = 0
        preferred_matches = 0

        user_skills_lower = {s.name.lower() for s in self.profile.skills}
        user_skill_keywords = set()
        for skill in self.profile.skills:
            user_skill_keywords.add(skill.name.lower())
            user_skill_keywords.update(kw.lower() for kw in skill.keywords)

        # Check required skills
        for req_skill in job.required_skills:
            req_lower = req_skill.lower()
            if req_lower in user_skills_lower or any(
                self._skills_match(req_lower, us) for us in user_skills_lower
            ):
                required_matches += 1

        # Check preferred skills
        for pref_skill in job.preferred_skills:
            pref_lower = pref_skill.lower()
            if pref_lower in user_skills_lower or any(
                self._skills_match(pref_lower, us) for us in user_skills_lower
            ):
                preferred_matches += 1

        # Calculate score
        req_total = len(job.required_skills) or 1
        pref_total = len(job.preferred_skills) or 1

        required_score = (required_matches / req_total) * 70
        preferred_score = (preferred_matches / pref_total) * 30

        return min(100, required_score + preferred_score)

    def _skills_match(self, skill1: str, skill2: str) -> bool:
        """Check if two skill names match (including variants)."""
        # Exact match
        if skill1 == skill2:
            return True

        # Common variations
        variations = {
            "javascript": ["js", "ecmascript"],
            "typescript": ["ts"],
            "python": ["py"],
            "kubernetes": ["k8s"],
            "postgresql": ["postgres", "psql"],
            "mongodb": ["mongo"],
            "react": ["reactjs", "react.js"],
            "node.js": ["nodejs", "node"],
            "machine learning": ["ml"],
            "artificial intelligence": ["ai"],
            "amazon web services": ["aws"],
            "google cloud platform": ["gcp"],
            "continuous integration": ["ci"],
            "continuous deployment": ["cd"],
            "ci/cd": ["cicd", "ci cd"],
        }

        for base, variants in variations.items():
            if skill1 == base and skill2 in variants:
                return True
            if skill2 == base and skill1 in variants:
                return True
            if skill1 in variants and skill2 in variants:
                return True

        # Substring match for compound skills
        if len(skill1) > 3 and len(skill2) > 3:
            if skill1 in skill2 or skill2 in skill1:
                return True

        return False

    def _fuzzy_skill_match(self, description: str) -> float:
        """Calculate skill match based on job description text."""
        if not description:
            return 50  # Default to neutral

        desc_lower = description.lower()
        matches = 0
        total_skills = len(self.profile.skills) or 1

        for skill in self.profile.skills:
            skill_lower = skill.name.lower()
            if skill_lower in desc_lower:
                matches += 1
                # Bonus for expert-level skills mentioned
                if skill.level in [SkillLevel.EXPERT, SkillLevel.ADVANCED]:
                    matches += 0.5

        # Cap at 100
        return min(100, (matches / total_skills) * 100)

    def _calculate_experience_match(self, job: Job) -> float:
        """Calculate experience match score (0-100)."""
        user_years = self.profile.total_experience_years

        # Parse required experience from job
        required_years = self._extract_required_years(job)

        if required_years is None:
            # Estimate from experience level
            level_years = {
                "entry": 0,
                "junior": 1,
                "mid": 3,
                "senior": 5,
                "lead": 7,
                "principal": 10,
                "staff": 8,
                "director": 10,
                "executive": 15,
            }
            for level, years in level_years.items():
                if level in job.experience_level.lower():
                    required_years = years
                    break

        if required_years is None:
            required_years = 2  # Default assumption

        # Calculate score
        if user_years >= required_years:
            # Full score if meeting requirement, slight bonus for exceeding
            score = 100
            if user_years > required_years * 1.5:
                # May be overqualified, slight penalty
                score = 90
        else:
            # Proportional score if under-experienced
            score = (user_years / required_years) * 80

        return max(0, min(100, score))

    def _extract_required_years(self, job: Job) -> Optional[float]:
        """Extract required years of experience from job posting."""
        text = f"{job.description} {' '.join(job.requirements)}"

        patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s+)?experience',
            r'(\d+)\+?\s*years?\s*(?:of\s+)?(?:relevant|professional)',
            r'minimum\s+(\d+)\s*years?',
            r'at\s+least\s+(\d+)\s*years?',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1))

        return None

    def _calculate_education_match(self, job: Job) -> float:
        """Calculate education match score (0-100)."""
        if not self.profile.education:
            return 50  # Neutral if no education listed

        # Check if degree is required
        text = f"{job.description} {' '.join(job.requirements)}".lower()

        degree_requirements = {
            "phd": 100,
            "doctorate": 100,
            "master": 80,
            "mba": 80,
            "bachelor": 60,
            "associate": 40,
            "degree": 50,
        }

        required_level = None
        for degree, level in degree_requirements.items():
            if degree in text:
                if "required" in text or "must have" in text:
                    required_level = level
                    break

        if required_level is None:
            return 80  # No specific requirement, good match

        # Check user's highest degree
        user_degrees = []
        for edu in self.profile.education:
            degree_lower = edu.degree.lower()
            for degree, level in degree_requirements.items():
                if degree in degree_lower:
                    user_degrees.append(level)
                    break

        if not user_degrees:
            return 40  # No recognized degree

        highest_user_degree = max(user_degrees)

        if highest_user_degree >= required_level:
            return 100
        else:
            return (highest_user_degree / required_level) * 80

    def _calculate_location_match(self, job: Job) -> float:
        """Calculate location match score (0-100)."""
        # Remote jobs are always a match for remote seekers
        if job.remote_option:
            if self.profile.remote_preference in ["remote", "flexible"]:
                return 100
            return 80

        # Check location match
        if not job.location or not self.profile.location:
            return 70  # Unknown, neutral

        job_loc = job.location.lower()
        user_loc = self.profile.location.lower()
        desired_locs = [loc.lower() for loc in self.profile.desired_locations]

        # Exact or partial match
        if user_loc in job_loc or job_loc in user_loc:
            return 100

        for desired in desired_locs:
            if desired in job_loc or job_loc in desired:
                return 100

        # Check for same city/state
        user_parts = set(user_loc.replace(',', ' ').split())
        job_parts = set(job_loc.replace(',', ' ').split())

        common = user_parts & job_parts
        if common:
            return 80

        # Different location
        if self.profile.remote_preference == "remote":
            return 40
        elif self.profile.remote_preference == "flexible":
            return 60
        else:
            return 30

    def _calculate_salary_match(self, job: Job) -> float:
        """Calculate salary match score (0-100)."""
        if not self.profile.min_salary:
            return 70  # No preference, neutral

        if not job.salary_min and not job.salary_max:
            return 60  # Unknown salary, slightly below neutral

        job_max = job.salary_max or job.salary_min
        job_min = job.salary_min or job.salary_max

        user_min = self.profile.min_salary

        if job_max and job_max >= user_min:
            if job_min and job_min >= user_min:
                # Both min and max exceed expectation
                return 100
            else:
                # Range includes expectation
                return 85
        elif job_max and job_max >= user_min * 0.9:
            # Within 10% of expectation
            return 70
        elif job_max:
            # Below expectation
            ratio = job_max / user_min
            return max(0, ratio * 60)
        else:
            return 50

    def _calculate_hiring_likelihood(self, job: Job, score: MatchScore) -> float:
        """
        Calculate estimated hiring likelihood (0-100).

        This considers:
        - How well the candidate matches the role
        - Market demand for the skills
        - Competition level (estimated)
        - Application timing
        """
        base_likelihood = score.overall_score * 0.6

        # Skill match heavily influences hiring
        skill_factor = score.skill_match_score * 0.25

        # Experience alignment
        exp_factor = score.experience_match_score * 0.15

        # Bonus for having in-demand skills
        in_demand_skills = [
            "python", "javascript", "aws", "kubernetes", "react",
            "machine learning", "data science", "golang", "rust",
        ]
        demand_bonus = 0
        for skill in self.profile.skills:
            if skill.name.lower() in in_demand_skills:
                demand_bonus += 2
        demand_bonus = min(10, demand_bonus)

        # Penalty for missing critical skills
        missing_penalty = len(score.missing_skills) * 3
        missing_penalty = min(20, missing_penalty)

        likelihood = base_likelihood + skill_factor + exp_factor + demand_bonus - missing_penalty

        return max(5, min(95, likelihood))

    def _calculate_compensation_score(self, job: Job) -> float:
        """Calculate how competitive the compensation is (0-100)."""
        if not job.salary_max and not job.salary_min:
            return 50  # Unknown

        salary = job.salary_max or job.salary_min

        # Compare to user's expectation
        if self.profile.min_salary:
            ratio = salary / self.profile.min_salary
            if ratio >= 1.3:
                return 100
            elif ratio >= 1.1:
                return 90
            elif ratio >= 1.0:
                return 80
            elif ratio >= 0.9:
                return 70
            else:
                return max(20, ratio * 60)

        # General compensation scoring based on typical ranges
        # This is a simplified heuristic
        if salary >= 200000:
            return 95
        elif salary >= 150000:
            return 85
        elif salary >= 120000:
            return 75
        elif salary >= 90000:
            return 65
        elif salary >= 60000:
            return 50
        else:
            return 40

    def _get_skill_details(self, job: Job) -> tuple[list[str], list[str], list[str]]:
        """Get detailed skill breakdown."""
        user_skills = {s.name.lower() for s in self.profile.skills}
        required = {s.lower() for s in job.required_skills}
        preferred = {s.lower() for s in job.preferred_skills}
        all_job_skills = required | preferred

        matched = []
        missing = []
        bonus = []

        for skill in user_skills:
            if skill in all_job_skills:
                matched.append(skill.title())
            elif any(self._skills_match(skill, js) for js in all_job_skills):
                matched.append(skill.title())
            else:
                bonus.append(skill.title())

        for req in required:
            if req not in user_skills and not any(
                self._skills_match(req, us) for us in user_skills
            ):
                missing.append(req.title())

        return matched, missing, bonus

    def rank_jobs(self, jobs: list[Job], sort_by: str = "overall") -> list[tuple[Job, MatchScore]]:
        """
        Rank a list of jobs by match score.

        Args:
            jobs: List of jobs to rank
            sort_by: Score to sort by - "overall", "hiring_likelihood", "compensation"

        Returns:
            List of (job, score) tuples sorted by specified score
        """
        scored_jobs = [(job, self.match_job(job)) for job in jobs]

        sort_keys = {
            "overall": lambda x: x[1].overall_score,
            "hiring_likelihood": lambda x: x[1].hiring_likelihood,
            "compensation": lambda x: x[1].compensation_score,
            "skill_match": lambda x: x[1].skill_match_score,
        }

        key_func = sort_keys.get(sort_by, sort_keys["overall"])
        scored_jobs.sort(key=key_func, reverse=True)

        return scored_jobs
