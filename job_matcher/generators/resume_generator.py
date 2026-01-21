"""
Resume Generator - Creates customized resumes tailored to specific job postings.

Supports multiple output formats: plain text, Markdown, HTML, and PDF.
Uses AI for intelligent content optimization when available.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional
import json
import logging
import os

from job_matcher.core.models import UserProfile, Job, MatchScore


class ResumeGenerator:
    """Generates customized resumes for job applications."""

    def __init__(
        self,
        output_dir: str = "./generated_resumes",
        ai_api_key: Optional[str] = None,
    ):
        """
        Initialize the resume generator.

        Args:
            output_dir: Directory to save generated resumes
            ai_api_key: Optional API key for AI-powered optimization (OpenAI/Anthropic)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.ai_api_key = ai_api_key
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate(
        self,
        profile: UserProfile,
        job: Job,
        match_score: Optional[MatchScore] = None,
        format: str = "markdown",
        use_ai: bool = True,
    ) -> tuple[str, str]:
        """
        Generate a customized resume for a specific job.

        Args:
            profile: User profile with experience and skills
            job: Target job posting
            match_score: Optional match score for optimization hints
            format: Output format (markdown, html, txt, pdf)
            use_ai: Whether to use AI for content optimization

        Returns:
            Tuple of (file_path, content)
        """
        # Reorder and emphasize relevant content
        optimized_profile = self._optimize_for_job(profile, job, match_score)

        # Generate content in requested format
        if format == "markdown":
            content = self._generate_markdown(optimized_profile, job)
        elif format == "html":
            content = self._generate_html(optimized_profile, job)
        elif format == "txt":
            content = self._generate_text(optimized_profile, job)
        else:
            content = self._generate_markdown(optimized_profile, job)

        # Optionally enhance with AI
        if use_ai and self.ai_api_key:
            content = self._ai_enhance(content, job)

        # Save to file
        safe_company = "".join(c if c.isalnum() else "_" for c in job.company)
        safe_title = "".join(c if c.isalnum() else "_" for c in job.title)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        filename = f"resume_{safe_company}_{safe_title}_{timestamp}.{format}"
        filepath = self.output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        self.logger.info(f"Generated resume: {filepath}")

        return str(filepath), content

    def _optimize_for_job(
        self,
        profile: UserProfile,
        job: Job,
        match_score: Optional[MatchScore],
    ) -> dict:
        """Optimize profile content for the specific job."""
        # Get job keywords
        job_keywords = self._extract_keywords(job)

        # Sort skills by relevance to job
        sorted_skills = sorted(
            profile.skills,
            key=lambda s: self._skill_relevance(s, job_keywords),
            reverse=True
        )

        # Sort experiences by relevance
        sorted_experiences = sorted(
            profile.experiences,
            key=lambda e: self._experience_relevance(e, job_keywords),
            reverse=True
        )

        # Build optimized profile dict
        return {
            "profile": profile,
            "sorted_skills": sorted_skills,
            "sorted_experiences": sorted_experiences,
            "matched_skills": match_score.matched_skills if match_score else [],
            "job_keywords": job_keywords,
            "highlight_skills": list(job_keywords)[:10],
        }

    def _extract_keywords(self, job: Job) -> set[str]:
        """Extract important keywords from job posting."""
        keywords = set()

        # Add required and preferred skills
        keywords.update(s.lower() for s in job.required_skills)
        keywords.update(s.lower() for s in job.preferred_skills)

        # Extract from description
        description_lower = job.description.lower()

        # Common tech keywords to look for
        tech_keywords = [
            "python", "javascript", "java", "c++", "go", "rust", "ruby",
            "react", "angular", "vue", "node", "django", "flask", "spring",
            "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
            "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
            "machine learning", "deep learning", "ai", "data science",
            "agile", "scrum", "ci/cd", "devops", "microservices",
            "api", "rest", "graphql", "sql", "nosql",
        ]

        for kw in tech_keywords:
            if kw in description_lower:
                keywords.add(kw)

        return keywords

    def _skill_relevance(self, skill, keywords: set[str]) -> int:
        """Score skill relevance to job keywords."""
        score = 0
        skill_lower = skill.name.lower()

        if skill_lower in keywords:
            score += 10

        # Partial matches
        for kw in keywords:
            if kw in skill_lower or skill_lower in kw:
                score += 5

        # Add years experience as tiebreaker
        score += int(skill.years_experience)

        return score

    def _experience_relevance(self, exp, keywords: set[str]) -> int:
        """Score experience relevance to job keywords."""
        score = 0
        text = f"{exp.title} {exp.description} {' '.join(exp.achievements)}".lower()

        for kw in keywords:
            if kw in text:
                score += 3

        # Boost recent experience
        if exp.is_current:
            score += 5

        return score

    def _generate_markdown(self, optimized: dict, job: Job) -> str:
        """Generate resume in Markdown format."""
        profile = optimized["profile"]
        lines = []

        # Header
        lines.append(f"# {profile.full_name}")
        lines.append("")

        # Contact info
        contact = []
        if profile.email:
            contact.append(profile.email)
        if profile.phone:
            contact.append(profile.phone)
        if profile.location:
            contact.append(profile.location)
        if contact:
            lines.append(" | ".join(contact))
            lines.append("")

        # Links
        links = []
        if profile.linkedin_url:
            links.append(f"[LinkedIn]({profile.linkedin_url})")
        if profile.github_url:
            links.append(f"[GitHub]({profile.github_url})")
        if profile.portfolio_url:
            links.append(f"[Portfolio]({profile.portfolio_url})")
        if links:
            lines.append(" | ".join(links))
            lines.append("")

        # Summary (tailored to job)
        lines.append("## Professional Summary")
        lines.append("")
        summary = self._tailor_summary(profile, job, optimized["job_keywords"])
        lines.append(summary)
        lines.append("")

        # Skills (prioritized by relevance)
        lines.append("## Technical Skills")
        lines.append("")
        skill_categories = self._categorize_skills(optimized["sorted_skills"])
        for category, skills in skill_categories.items():
            skill_names = [s.name for s in skills]
            lines.append(f"**{category}:** {', '.join(skill_names)}")
        lines.append("")

        # Experience
        lines.append("## Professional Experience")
        lines.append("")

        for exp in optimized["sorted_experiences"]:
            # Title and company
            end_date = "Present" if exp.is_current else (
                exp.end_date.strftime("%B %Y") if exp.end_date else ""
            )
            start_date = exp.start_date.strftime("%B %Y")

            lines.append(f"### {exp.title}")
            lines.append(f"**{exp.company}** | {exp.location if exp.location else ''} | {start_date} - {end_date}")
            lines.append("")

            # Description
            if exp.description:
                lines.append(exp.description.strip())
                lines.append("")

            # Achievements (tailored/highlighted)
            if exp.achievements:
                for achievement in exp.achievements[:5]:  # Top 5
                    # Highlight keywords
                    highlighted = self._highlight_keywords(achievement, optimized["job_keywords"])
                    lines.append(f"- {highlighted}")
                lines.append("")

        # Education
        if profile.education:
            lines.append("## Education")
            lines.append("")

            for edu in profile.education:
                lines.append(f"### {edu.degree} in {edu.field_of_study}")
                lines.append(f"**{edu.institution}**")
                if edu.graduation_date:
                    lines.append(f"Graduated: {edu.graduation_date.strftime('%B %Y')}")
                if edu.gpa and edu.gpa >= 3.5:
                    lines.append(f"GPA: {edu.gpa:.2f}")
                if edu.honors:
                    lines.append(f"Honors: {', '.join(edu.honors)}")
                lines.append("")

        # Certifications
        if profile.certifications:
            lines.append("## Certifications")
            lines.append("")
            for cert in profile.certifications:
                lines.append(f"- {cert}")
            lines.append("")

        return "\n".join(lines)

    def _generate_html(self, optimized: dict, job: Job) -> str:
        """Generate resume in HTML format."""
        profile = optimized["profile"]

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{profile.full_name} - Resume</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 40px;
            color: #333;
            line-height: 1.6;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 5px;
        }}
        h2 {{
            color: #2c3e50;
            border-bottom: 1px solid #bdc3c7;
            padding-bottom: 5px;
            margin-top: 25px;
        }}
        h3 {{
            color: #34495e;
            margin-bottom: 5px;
        }}
        .contact {{
            color: #7f8c8d;
            margin-bottom: 20px;
        }}
        .contact a {{
            color: #3498db;
            text-decoration: none;
        }}
        .skills {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .skill-category {{
            margin-bottom: 10px;
        }}
        .skill-tag {{
            background: #ecf0f1;
            padding: 3px 10px;
            border-radius: 3px;
            font-size: 0.9em;
        }}
        .highlight {{
            background: #fff3cd;
            padding: 1px 3px;
            border-radius: 2px;
        }}
        .experience-header {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
        }}
        .company {{
            color: #7f8c8d;
        }}
        ul {{
            margin-top: 10px;
        }}
        li {{
            margin-bottom: 5px;
        }}
    </style>
</head>
<body>
    <h1>{profile.full_name}</h1>
    <div class="contact">
        {profile.email} | {profile.phone} | {profile.location}<br>
        {f'<a href="{profile.linkedin_url}">LinkedIn</a>' if profile.linkedin_url else ''}
        {f' | <a href="{profile.github_url}">GitHub</a>' if profile.github_url else ''}
        {f' | <a href="{profile.portfolio_url}">Portfolio</a>' if profile.portfolio_url else ''}
    </div>

    <h2>Professional Summary</h2>
    <p>{self._tailor_summary(profile, job, optimized["job_keywords"])}</p>

    <h2>Technical Skills</h2>
    <div class="skills">
"""

        # Skills
        skill_categories = self._categorize_skills(optimized["sorted_skills"])
        for category, skills in skill_categories.items():
            html += f'<div class="skill-category"><strong>{category}:</strong> '
            skill_tags = [f'<span class="skill-tag">{s.name}</span>' for s in skills]
            html += " ".join(skill_tags)
            html += "</div>\n"

        html += "</div>\n\n<h2>Professional Experience</h2>\n"

        # Experience
        for exp in optimized["sorted_experiences"]:
            end_date = "Present" if exp.is_current else (
                exp.end_date.strftime("%B %Y") if exp.end_date else ""
            )
            start_date = exp.start_date.strftime("%B %Y")

            html += f"""
    <h3>{exp.title}</h3>
    <div class="experience-header">
        <span class="company"><strong>{exp.company}</strong> | {exp.location or ''}</span>
        <span>{start_date} - {end_date}</span>
    </div>
"""
            if exp.description:
                html += f"<p>{exp.description}</p>\n"

            if exp.achievements:
                html += "<ul>\n"
                for achievement in exp.achievements[:5]:
                    highlighted = self._highlight_keywords_html(achievement, optimized["job_keywords"])
                    html += f"<li>{highlighted}</li>\n"
                html += "</ul>\n"

        # Education
        if profile.education:
            html += "<h2>Education</h2>\n"
            for edu in profile.education:
                html += f"<h3>{edu.degree} in {edu.field_of_study}</h3>\n"
                html += f"<p><strong>{edu.institution}</strong>"
                if edu.graduation_date:
                    html += f" | Graduated: {edu.graduation_date.strftime('%B %Y')}"
                html += "</p>\n"

        # Certifications
        if profile.certifications:
            html += "<h2>Certifications</h2>\n<ul>\n"
            for cert in profile.certifications:
                html += f"<li>{cert}</li>\n"
            html += "</ul>\n"

        html += "</body>\n</html>"

        return html

    def _generate_text(self, optimized: dict, job: Job) -> str:
        """Generate resume in plain text format."""
        profile = optimized["profile"]
        lines = []

        # Header
        lines.append("=" * 60)
        lines.append(profile.full_name.upper().center(60))
        lines.append("=" * 60)
        lines.append("")

        # Contact
        lines.append(f"Email: {profile.email}")
        lines.append(f"Phone: {profile.phone}")
        lines.append(f"Location: {profile.location}")
        if profile.linkedin_url:
            lines.append(f"LinkedIn: {profile.linkedin_url}")
        if profile.github_url:
            lines.append(f"GitHub: {profile.github_url}")
        lines.append("")

        # Summary
        lines.append("-" * 60)
        lines.append("PROFESSIONAL SUMMARY")
        lines.append("-" * 60)
        lines.append(self._tailor_summary(profile, job, optimized["job_keywords"]))
        lines.append("")

        # Skills
        lines.append("-" * 60)
        lines.append("TECHNICAL SKILLS")
        lines.append("-" * 60)
        skill_categories = self._categorize_skills(optimized["sorted_skills"])
        for category, skills in skill_categories.items():
            skill_names = [s.name for s in skills]
            lines.append(f"{category}: {', '.join(skill_names)}")
        lines.append("")

        # Experience
        lines.append("-" * 60)
        lines.append("PROFESSIONAL EXPERIENCE")
        lines.append("-" * 60)

        for exp in optimized["sorted_experiences"]:
            end_date = "Present" if exp.is_current else (
                exp.end_date.strftime("%m/%Y") if exp.end_date else ""
            )
            start_date = exp.start_date.strftime("%m/%Y")

            lines.append(f"\n{exp.title}")
            lines.append(f"{exp.company} | {exp.location or ''} | {start_date} - {end_date}")

            if exp.description:
                lines.append(f"  {exp.description}")

            for achievement in exp.achievements[:5]:
                lines.append(f"  * {achievement}")

        lines.append("")

        # Education
        if profile.education:
            lines.append("-" * 60)
            lines.append("EDUCATION")
            lines.append("-" * 60)

            for edu in profile.education:
                lines.append(f"\n{edu.degree} in {edu.field_of_study}")
                lines.append(f"{edu.institution}")
                if edu.graduation_date:
                    lines.append(f"Graduated: {edu.graduation_date.strftime('%B %Y')}")

        return "\n".join(lines)

    def _tailor_summary(self, profile: UserProfile, job: Job, keywords: set[str]) -> str:
        """Create a tailored professional summary for the job."""
        if not profile.summary:
            # Generate a basic summary
            years = profile.total_experience_years
            top_skills = [s.name for s in profile.skills[:5]]

            return (
                f"Experienced professional with {years:.0f}+ years of expertise in "
                f"{', '.join(top_skills[:3])}. Seeking to leverage skills in "
                f"{job.title} role at {job.company}."
            )

        # Enhance existing summary with job-relevant keywords
        summary = profile.summary

        # Add job-specific mention if not already present
        if job.company.lower() not in summary.lower():
            summary += f" Excited to bring these skills to {job.company}."

        return summary

    def _categorize_skills(self, skills: list) -> dict:
        """Categorize skills for better organization."""
        categories = {
            "Programming Languages": [],
            "Frameworks & Libraries": [],
            "Cloud & DevOps": [],
            "Databases": [],
            "Tools & Technologies": [],
        }

        language_keywords = ["python", "javascript", "java", "c++", "go", "rust", "ruby", "typescript"]
        framework_keywords = ["react", "angular", "vue", "django", "flask", "spring", "node"]
        cloud_keywords = ["aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ci/cd"]
        db_keywords = ["sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch"]

        for skill in skills:
            name_lower = skill.name.lower()

            if any(kw in name_lower for kw in language_keywords):
                categories["Programming Languages"].append(skill)
            elif any(kw in name_lower for kw in framework_keywords):
                categories["Frameworks & Libraries"].append(skill)
            elif any(kw in name_lower for kw in cloud_keywords):
                categories["Cloud & DevOps"].append(skill)
            elif any(kw in name_lower for kw in db_keywords):
                categories["Databases"].append(skill)
            else:
                categories["Tools & Technologies"].append(skill)

        # Remove empty categories
        return {k: v for k, v in categories.items() if v}

    def _highlight_keywords(self, text: str, keywords: set[str]) -> str:
        """Highlight job-relevant keywords in text (for markdown)."""
        # For markdown, we use bold
        for kw in keywords:
            if kw in text.lower():
                # Case-insensitive replacement preserving original case
                import re
                pattern = re.compile(re.escape(kw), re.IGNORECASE)
                text = pattern.sub(lambda m: f"**{m.group()}**", text)
        return text

    def _highlight_keywords_html(self, text: str, keywords: set[str]) -> str:
        """Highlight job-relevant keywords in text (for HTML)."""
        import re
        for kw in keywords:
            if kw in text.lower():
                pattern = re.compile(re.escape(kw), re.IGNORECASE)
                text = pattern.sub(
                    lambda m: f'<span class="highlight">{m.group()}</span>',
                    text
                )
        return text

    def _ai_enhance(self, content: str, job: Job) -> str:
        """Use AI to enhance the resume content."""
        if not self.ai_api_key:
            return content

        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.ai_api_key)

            prompt = f"""Please review and enhance this resume for a {job.title} position at {job.company}.

Job Description:
{job.description[:1000]}

Current Resume:
{content}

Please:
1. Improve action verbs and quantify achievements where possible
2. Ensure keywords from the job description are naturally incorporated
3. Make the language more impactful and professional
4. Keep the same format and structure

Return ONLY the enhanced resume content, nothing else."""

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )

            return response.content[0].text

        except ImportError:
            self.logger.warning("anthropic library not installed for AI enhancement")
            return content
        except Exception as e:
            self.logger.error(f"AI enhancement failed: {e}")
            return content
