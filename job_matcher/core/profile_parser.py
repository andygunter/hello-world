"""
Profile Parser - Extracts user profile information from various sources.
Supports PDF, DOCX, JSON, and plain text resumes.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import (
    UserProfile,
    Skill,
    SkillLevel,
    Experience,
    Education,
)


class ProfileParser:
    """Parses user profiles from various document formats."""

    # Common skill keywords for detection
    SKILL_CATEGORIES = {
        "programming_languages": [
            "python", "javascript", "typescript", "java", "c++", "c#", "ruby",
            "go", "rust", "swift", "kotlin", "php", "scala", "r", "matlab",
        ],
        "frameworks": [
            "react", "angular", "vue", "django", "flask", "fastapi", "spring",
            "node.js", "express", "rails", "laravel", ".net", "next.js",
        ],
        "databases": [
            "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
            "dynamodb", "cassandra", "sqlite", "oracle", "sql server",
        ],
        "cloud_devops": [
            "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
            "jenkins", "github actions", "ci/cd", "ansible", "linux",
        ],
        "data_science": [
            "machine learning", "deep learning", "tensorflow", "pytorch",
            "pandas", "numpy", "scikit-learn", "nlp", "computer vision",
        ],
        "soft_skills": [
            "leadership", "communication", "project management", "agile",
            "scrum", "team collaboration", "problem solving", "mentoring",
        ],
    }

    # Experience level keywords
    EXPERIENCE_LEVELS = {
        "entry": ["junior", "entry", "associate", "intern", "graduate"],
        "mid": ["mid", "intermediate", "engineer", "developer", "analyst"],
        "senior": ["senior", "lead", "principal", "staff", "architect"],
        "executive": ["director", "vp", "cto", "ceo", "head of", "chief"],
    }

    def __init__(self):
        self.profile = UserProfile()

    def parse_file(self, file_path: str) -> UserProfile:
        """Parse a file and extract profile information."""
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        extension = path.suffix.lower()

        if extension == ".json":
            return self._parse_json(path)
        elif extension == ".pdf":
            return self._parse_pdf(path)
        elif extension in [".docx", ".doc"]:
            return self._parse_docx(path)
        elif extension in [".txt", ".md"]:
            return self._parse_text(path)
        else:
            raise ValueError(f"Unsupported file format: {extension}")

    def _parse_json(self, path: Path) -> UserProfile:
        """Parse a JSON profile file."""
        with open(path, 'r') as f:
            data = json.load(f)
        return self._dict_to_profile(data)

    def _parse_pdf(self, path: Path) -> UserProfile:
        """Parse a PDF resume. Requires pypdf2 or pdfplumber."""
        try:
            import pdfplumber

            text = ""
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""

            return self._parse_text_content(text)
        except ImportError:
            try:
                from PyPDF2 import PdfReader

                reader = PdfReader(str(path))
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""

                return self._parse_text_content(text)
            except ImportError:
                raise ImportError(
                    "PDF parsing requires 'pdfplumber' or 'PyPDF2'. "
                    "Install with: pip install pdfplumber"
                )

    def _parse_docx(self, path: Path) -> UserProfile:
        """Parse a DOCX resume."""
        try:
            from docx import Document

            doc = Document(str(path))
            text = "\n".join([para.text for para in doc.paragraphs])
            return self._parse_text_content(text)
        except ImportError:
            raise ImportError(
                "DOCX parsing requires 'python-docx'. "
                "Install with: pip install python-docx"
            )

    def _parse_text(self, path: Path) -> UserProfile:
        """Parse a plain text resume."""
        with open(path, 'r', encoding='utf-8') as f:
            text = f.read()
        return self._parse_text_content(text)

    def _parse_text_content(self, text: str) -> UserProfile:
        """Extract profile information from raw text."""
        profile = UserProfile()

        # Extract contact information
        profile.email = self._extract_email(text)
        profile.phone = self._extract_phone(text)
        profile.linkedin_url = self._extract_linkedin(text)
        profile.github_url = self._extract_github(text)

        # Extract name (usually first line or after "Name:")
        profile.full_name = self._extract_name(text)

        # Extract skills
        profile.skills = self._extract_skills(text)

        # Extract experiences
        profile.experiences = self._extract_experiences(text)

        # Extract education
        profile.education = self._extract_education(text)

        # Extract summary/objective
        profile.summary = self._extract_summary(text)

        return profile

    def _extract_email(self, text: str) -> str:
        """Extract email address from text."""
        pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        match = re.search(pattern, text)
        return match.group(0) if match else ""

    def _extract_phone(self, text: str) -> str:
        """Extract phone number from text."""
        patterns = [
            r'\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}',
            r'\d{3}[-.\s]\d{3}[-.\s]\d{4}',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return ""

    def _extract_linkedin(self, text: str) -> str:
        """Extract LinkedIn URL from text."""
        pattern = r'(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]+'
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(0) if match else ""

    def _extract_github(self, text: str) -> str:
        """Extract GitHub URL from text."""
        pattern = r'(?:https?://)?(?:www\.)?github\.com/[\w-]+'
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(0) if match else ""

    def _extract_name(self, text: str) -> str:
        """Extract name from text."""
        lines = text.strip().split('\n')

        # Check for "Name:" pattern
        for line in lines[:10]:
            if line.lower().startswith('name:'):
                return line.split(':', 1)[1].strip()

        # Usually the first non-empty line is the name
        for line in lines:
            line = line.strip()
            if line and not re.search(r'@|\.com|resume|cv', line.lower()):
                # Check if it looks like a name (2-4 words, no special chars)
                words = line.split()
                if 1 <= len(words) <= 4 and all(w.isalpha() or w == '.' for w in words):
                    return line

        return ""

    def _extract_skills(self, text: str) -> list[Skill]:
        """Extract skills from text."""
        skills = []
        text_lower = text.lower()

        for category, skill_list in self.SKILL_CATEGORIES.items():
            for skill_name in skill_list:
                if skill_name in text_lower:
                    # Estimate level based on context
                    level = self._estimate_skill_level(text_lower, skill_name)
                    years = self._estimate_years(text_lower, skill_name)

                    skills.append(Skill(
                        name=skill_name.title(),
                        level=level,
                        years_experience=years,
                        keywords=[category],
                    ))

        return skills

    def _estimate_skill_level(self, text: str, skill: str) -> SkillLevel:
        """Estimate skill level based on context clues."""
        # Look for level indicators near the skill mention
        expert_indicators = ["expert", "advanced", "extensive", "mastery", "lead"]
        intermediate_indicators = ["proficient", "experienced", "working knowledge"]
        beginner_indicators = ["basic", "familiar", "learning", "exposure"]

        # Check context around skill mention
        skill_index = text.find(skill)
        if skill_index == -1:
            return SkillLevel.INTERMEDIATE

        context = text[max(0, skill_index - 100):skill_index + 100]

        for indicator in expert_indicators:
            if indicator in context:
                return SkillLevel.EXPERT

        for indicator in intermediate_indicators:
            if indicator in context:
                return SkillLevel.ADVANCED

        for indicator in beginner_indicators:
            if indicator in context:
                return SkillLevel.BEGINNER

        return SkillLevel.INTERMEDIATE

    def _estimate_years(self, text: str, skill: str) -> float:
        """Estimate years of experience with a skill."""
        # Look for patterns like "5 years of Python" or "Python (3 years)"
        patterns = [
            rf'(\d+)\+?\s*years?\s*(?:of\s+)?{skill}',
            rf'{skill}\s*\(?(\d+)\+?\s*years?\)?',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1))

        return 0.0

    def _extract_experiences(self, text: str) -> list[Experience]:
        """Extract work experiences from text."""
        experiences = []

        # Look for experience section
        exp_patterns = [
            r'(?:work\s+)?experience',
            r'employment\s+history',
            r'professional\s+experience',
        ]

        lines = text.split('\n')
        in_experience_section = False
        current_exp = None

        for i, line in enumerate(lines):
            line_lower = line.lower().strip()

            # Check if entering experience section
            for pattern in exp_patterns:
                if re.search(pattern, line_lower):
                    in_experience_section = True
                    break

            # Check if leaving experience section
            if in_experience_section and re.search(
                r'^(education|skills|certifications|projects|references)',
                line_lower
            ):
                if current_exp:
                    experiences.append(current_exp)
                break

            if in_experience_section and line.strip():
                # Try to detect job title and company
                date_match = re.search(
                    r'(\d{4})\s*[-–]\s*(\d{4}|present|current)',
                    line,
                    re.IGNORECASE
                )

                if date_match or self._looks_like_job_title(line):
                    if current_exp:
                        experiences.append(current_exp)

                    current_exp = Experience(
                        title=self._extract_job_title(line),
                        company=self._extract_company(line, lines, i),
                        start_date=self._parse_date(date_match.group(1) if date_match else ""),
                        end_date=self._parse_date(date_match.group(2) if date_match else ""),
                        is_current="present" in line.lower() or "current" in line.lower(),
                    )
                elif current_exp:
                    # Add to description/achievements
                    if line.strip().startswith(('•', '-', '*', '–')):
                        current_exp.achievements.append(line.strip().lstrip('•-*– '))
                    else:
                        current_exp.description += " " + line.strip()

        if current_exp:
            experiences.append(current_exp)

        return experiences

    def _looks_like_job_title(self, line: str) -> bool:
        """Check if a line looks like a job title."""
        title_keywords = [
            'engineer', 'developer', 'manager', 'analyst', 'designer',
            'director', 'lead', 'architect', 'consultant', 'specialist',
            'coordinator', 'administrator', 'scientist', 'intern',
        ]
        return any(keyword in line.lower() for keyword in title_keywords)

    def _extract_job_title(self, line: str) -> str:
        """Extract job title from a line."""
        # Remove dates
        line = re.sub(r'\d{4}\s*[-–]\s*(\d{4}|present|current)', '', line, flags=re.IGNORECASE)
        # Remove common separators
        parts = re.split(r'\s*[|@,]\s*', line)
        if parts:
            return parts[0].strip()
        return line.strip()

    def _extract_company(self, line: str, lines: list[str], index: int) -> str:
        """Extract company name from context."""
        # Try to find company in the same line after separator
        parts = re.split(r'\s*[|@]\s*', line)
        if len(parts) > 1:
            return parts[1].strip()

        # Try next line
        if index + 1 < len(lines):
            next_line = lines[index + 1].strip()
            if next_line and not next_line.startswith(('•', '-', '*')):
                return next_line

        return ""

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse a date string."""
        if not date_str or date_str.lower() in ['present', 'current']:
            return None

        try:
            if len(date_str) == 4:  # Year only
                return datetime(int(date_str), 1, 1)
            return datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            return None

    def _extract_education(self, text: str) -> list[Education]:
        """Extract education from text."""
        education = []

        # Degree patterns
        degree_patterns = [
            r"(bachelor'?s?|b\.?s\.?|b\.?a\.?)\s+(?:of\s+)?(?:science|arts)?\s*(?:in\s+)?(\w[\w\s]+)",
            r"(master'?s?|m\.?s\.?|m\.?a\.?|mba)\s+(?:of\s+)?(?:science|arts|business)?\s*(?:in\s+)?(\w[\w\s]+)",
            r"(ph\.?d\.?|doctorate)\s*(?:in\s+)?(\w[\w\s]+)",
            r"(associate'?s?)\s+(?:degree\s+)?(?:in\s+)?(\w[\w\s]+)",
        ]

        for pattern in degree_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                degree = match.group(1).strip()
                field = match.group(2).strip() if len(match.groups()) > 1 else ""

                education.append(Education(
                    institution="",  # Would need more context
                    degree=degree,
                    field_of_study=field,
                ))

        return education

    def _extract_summary(self, text: str) -> str:
        """Extract professional summary from text."""
        summary_patterns = [
            r'(?:professional\s+)?summary[:\s]+(.+?)(?=\n\n|\n[A-Z])',
            r'(?:career\s+)?objective[:\s]+(.+?)(?=\n\n|\n[A-Z])',
            r'about\s+me[:\s]+(.+?)(?=\n\n|\n[A-Z])',
        ]

        for pattern in summary_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()[:500]

        return ""

    def _dict_to_profile(self, data: dict) -> UserProfile:
        """Convert a dictionary to a UserProfile object."""
        profile = UserProfile(
            full_name=data.get("full_name", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            location=data.get("location", ""),
            linkedin_url=data.get("linkedin_url", ""),
            github_url=data.get("github_url", ""),
            portfolio_url=data.get("portfolio_url", ""),
            summary=data.get("summary", ""),
            certifications=data.get("certifications", []),
            languages=data.get("languages", []),
            desired_roles=data.get("desired_roles", []),
            desired_locations=data.get("desired_locations", []),
            min_salary=data.get("min_salary"),
            max_commute_minutes=data.get("max_commute_minutes"),
            remote_preference=data.get("remote_preference", "flexible"),
        )

        # Parse skills
        for skill_data in data.get("skills", []):
            if isinstance(skill_data, str):
                profile.skills.append(Skill(name=skill_data))
            elif isinstance(skill_data, dict):
                profile.skills.append(Skill(
                    name=skill_data.get("name", ""),
                    level=SkillLevel[skill_data.get("level", "INTERMEDIATE")],
                    years_experience=skill_data.get("years_experience", 0),
                    keywords=skill_data.get("keywords", []),
                ))

        # Parse experiences
        for exp_data in data.get("experiences", []):
            profile.experiences.append(Experience(
                title=exp_data.get("title", ""),
                company=exp_data.get("company", ""),
                start_date=datetime.fromisoformat(exp_data["start_date"]) if exp_data.get("start_date") else datetime.now(),
                end_date=datetime.fromisoformat(exp_data["end_date"]) if exp_data.get("end_date") else None,
                description=exp_data.get("description", ""),
                achievements=exp_data.get("achievements", []),
                skills_used=exp_data.get("skills_used", []),
                location=exp_data.get("location", ""),
                is_current=exp_data.get("is_current", False),
            ))

        # Parse education
        for edu_data in data.get("education", []):
            profile.education.append(Education(
                institution=edu_data.get("institution", ""),
                degree=edu_data.get("degree", ""),
                field_of_study=edu_data.get("field_of_study", ""),
                graduation_date=datetime.fromisoformat(edu_data["graduation_date"]) if edu_data.get("graduation_date") else None,
                gpa=edu_data.get("gpa"),
                honors=edu_data.get("honors", []),
                relevant_coursework=edu_data.get("relevant_coursework", []),
            ))

        return profile

    def create_sample_profile(self) -> UserProfile:
        """Create a sample profile for testing."""
        return UserProfile(
            full_name="Sample User",
            email="sample@example.com",
            phone="555-123-4567",
            location="San Francisco, CA",
            summary="Experienced software engineer with expertise in Python and cloud technologies.",
            skills=[
                Skill(name="Python", level=SkillLevel.EXPERT, years_experience=5),
                Skill(name="JavaScript", level=SkillLevel.ADVANCED, years_experience=4),
                Skill(name="AWS", level=SkillLevel.ADVANCED, years_experience=3),
                Skill(name="Docker", level=SkillLevel.INTERMEDIATE, years_experience=2),
            ],
            experiences=[
                Experience(
                    title="Senior Software Engineer",
                    company="Tech Corp",
                    start_date=datetime(2020, 1, 1),
                    is_current=True,
                    description="Leading backend development team",
                    achievements=[
                        "Reduced API latency by 40%",
                        "Implemented CI/CD pipeline",
                    ],
                ),
            ],
            education=[
                Education(
                    institution="State University",
                    degree="Bachelor's",
                    field_of_study="Computer Science",
                    graduation_date=datetime(2018, 5, 1),
                ),
            ],
            desired_roles=["Senior Software Engineer", "Staff Engineer", "Tech Lead"],
            desired_locations=["San Francisco", "Remote"],
            min_salary=150000,
            remote_preference="flexible",
        )
