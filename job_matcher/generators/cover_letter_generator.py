"""
Cover Letter Generator - Creates customized cover letters for job applications.

Generates personalized cover letters based on user profile, job requirements,
and match analysis. Supports AI-powered content generation.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional
import logging

from job_matcher.core.models import UserProfile, Job, MatchScore


class CoverLetterGenerator:
    """Generates customized cover letters for job applications."""

    def __init__(
        self,
        output_dir: str = "./generated_cover_letters",
        ai_api_key: Optional[str] = None,
    ):
        """
        Initialize the cover letter generator.

        Args:
            output_dir: Directory to save generated cover letters
            ai_api_key: Optional API key for AI-powered generation
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
        tone: str = "professional",
        format: str = "markdown",
        use_ai: bool = True,
    ) -> tuple[str, str]:
        """
        Generate a customized cover letter for a specific job.

        Args:
            profile: User profile with experience and skills
            job: Target job posting
            match_score: Optional match score for content hints
            tone: Writing tone (professional, enthusiastic, conversational)
            format: Output format (markdown, html, txt)
            use_ai: Whether to use AI for content generation

        Returns:
            Tuple of (file_path, content)
        """
        # Use AI if available and requested
        if use_ai and self.ai_api_key:
            content = self._generate_with_ai(profile, job, match_score, tone)
        else:
            content = self._generate_template(profile, job, match_score, tone)

        # Format conversion
        if format == "html":
            content = self._convert_to_html(content, profile)
        elif format == "txt":
            content = self._convert_to_text(content)

        # Save to file
        safe_company = "".join(c if c.isalnum() else "_" for c in job.company)
        safe_title = "".join(c if c.isalnum() else "_" for c in job.title)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        filename = f"cover_letter_{safe_company}_{safe_title}_{timestamp}.{format}"
        filepath = self.output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        self.logger.info(f"Generated cover letter: {filepath}")

        return str(filepath), content

    def _generate_with_ai(
        self,
        profile: UserProfile,
        job: Job,
        match_score: Optional[MatchScore],
        tone: str,
    ) -> str:
        """Generate cover letter using AI."""
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.ai_api_key)

            # Prepare context
            skills_str = ", ".join(s.name for s in profile.skills[:10])
            recent_exp = profile.experiences[0] if profile.experiences else None

            exp_context = ""
            if recent_exp:
                exp_context = f"""
Most Recent Role: {recent_exp.title} at {recent_exp.company}
Key Achievements:
{chr(10).join('- ' + a for a in recent_exp.achievements[:3])}
"""

            match_context = ""
            if match_score:
                match_context = f"""
Match Analysis:
- Matching Skills: {', '.join(match_score.matched_skills[:5])}
- Skills to Emphasize: {', '.join(match_score.bonus_skills[:3])}
- Fit Score: {match_score.overall_score:.0f}%
"""

            prompt = f"""Write a compelling cover letter for the following job application.

APPLICANT PROFILE:
Name: {profile.full_name}
Location: {profile.location}
Summary: {profile.summary}
Key Skills: {skills_str}
Total Experience: {profile.total_experience_years:.0f} years
{exp_context}

JOB DETAILS:
Title: {job.title}
Company: {job.company}
Location: {job.location}
Description: {job.description[:1500]}

Required Skills: {', '.join(job.required_skills[:8])}
Preferred Skills: {', '.join(job.preferred_skills[:5])}
{match_context}

INSTRUCTIONS:
1. Write a {tone} cover letter (3-4 paragraphs)
2. Opening: Hook with enthusiasm for the specific role and company
3. Body: Connect 2-3 specific achievements/skills to job requirements
4. Include specific examples with quantified results where possible
5. Closing: Express interest in discussing further, include call to action
6. Keep it concise (under 400 words)
7. Don't use generic phrases like "I am writing to apply" or "Please find attached"
8. Make it specific to {job.company} and the {job.title} role

Return ONLY the cover letter content in markdown format, ready to use."""

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )

            return response.content[0].text

        except ImportError:
            self.logger.warning("anthropic library not installed, using template")
            return self._generate_template(profile, job, match_score, tone)
        except Exception as e:
            self.logger.error(f"AI generation failed: {e}, using template")
            return self._generate_template(profile, job, match_score, tone)

    def _generate_template(
        self,
        profile: UserProfile,
        job: Job,
        match_score: Optional[MatchScore],
        tone: str,
    ) -> str:
        """Generate cover letter using templates."""
        today = datetime.now().strftime("%B %d, %Y")

        # Get relevant skills
        matched_skills = []
        if match_score:
            matched_skills = match_score.matched_skills[:5]
        else:
            matched_skills = [s.name for s in profile.skills[:5]]

        # Get best achievement
        best_achievement = ""
        if profile.experiences and profile.experiences[0].achievements:
            best_achievement = profile.experiences[0].achievements[0]

        # Tone-specific openers
        openers = {
            "professional": f"I am excited to apply for the {job.title} position at {job.company}.",
            "enthusiastic": f"When I discovered the {job.title} opening at {job.company}, I knew I had to reach out immediately!",
            "conversational": f"I've been following {job.company}'s work for some time, and the {job.title} role seems like a perfect match.",
        }

        opener = openers.get(tone, openers["professional"])

        # Build the letter
        letter = f"""**{profile.full_name}**
{profile.email} | {profile.phone}
{profile.location}

{today}

**{job.company}**
{job.location}

**Re: {job.title} Position**

Dear Hiring Manager,

{opener} With {profile.total_experience_years:.0f}+ years of experience in {matched_skills[0] if matched_skills else 'technology'} and a proven track record of delivering impactful results, I am confident I can make a significant contribution to your team.

"""

        # Body paragraph - skills and experience
        if matched_skills:
            skills_text = ", ".join(matched_skills[:4])
            letter += f"""My expertise spans {skills_text}, which directly aligns with your requirements for this role. """

        if profile.experiences:
            recent = profile.experiences[0]
            letter += f"""In my current role as {recent.title} at {recent.company}, """

            if best_achievement:
                letter += f"""I have {best_achievement.lower() if best_achievement[0].isupper() else best_achievement} """

        letter += "\n\n"

        # Why this company
        letter += f"""What excites me most about {job.company} is the opportunity to {self._get_company_hook(job)}. """

        # Additional value
        if len(profile.experiences) > 1:
            prev = profile.experiences[1]
            letter += f"""Prior to my current role, I gained valuable experience at {prev.company} where I developed strong foundations in {prev.skills_used[0] if prev.skills_used else 'my field'}. """

        letter += "\n\n"

        # Closing
        letter += f"""I would welcome the opportunity to discuss how my background and skills would benefit {job.company}. I am available for an interview at your convenience and can be reached at {profile.phone} or {profile.email}.

Thank you for considering my application. I look forward to hearing from you.

Best regards,

**{profile.full_name}**
"""

        return letter

    def _get_company_hook(self, job: Job) -> str:
        """Generate a hook about why the company is interesting."""
        hooks = {
            "startup": "be part of a fast-growing team shaping the future of the industry",
            "enterprise": "contribute to large-scale systems that impact millions of users",
            "fintech": "work at the intersection of finance and technology",
            "healthcare": "make a meaningful impact on people's health and wellbeing",
            "ai": "work on cutting-edge artificial intelligence and machine learning",
            "remote": "collaborate with a distributed team of talented professionals",
        }

        job_text = f"{job.description} {job.industry}".lower()

        for keyword, hook in hooks.items():
            if keyword in job_text:
                return hook

        return f"contribute to {job.company}'s mission and growth"

    def _convert_to_html(self, content: str, profile: UserProfile) -> str:
        """Convert markdown cover letter to HTML."""
        import re

        # Basic markdown to HTML conversion
        html = content

        # Bold
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)

        # Paragraphs
        paragraphs = html.split('\n\n')
        html = '\n'.join(f'<p>{p}</p>' if not p.startswith('<') else p for p in paragraphs)

        # Wrap in HTML document
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cover Letter - {profile.full_name}</title>
    <style>
        body {{
            font-family: 'Georgia', serif;
            max-width: 700px;
            margin: 0 auto;
            padding: 50px;
            color: #333;
            line-height: 1.8;
        }}
        p {{
            margin-bottom: 1em;
        }}
        strong {{
            font-weight: 600;
        }}
    </style>
</head>
<body>
{html}
</body>
</html>"""

    def _convert_to_text(self, content: str) -> str:
        """Convert markdown cover letter to plain text."""
        import re

        # Remove markdown formatting
        text = content

        # Remove bold markers
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)

        return text

    def generate_batch(
        self,
        profile: UserProfile,
        jobs: list[tuple[Job, MatchScore]],
        tone: str = "professional",
        format: str = "markdown",
        use_ai: bool = True,
    ) -> list[tuple[str, str, Job]]:
        """
        Generate cover letters for multiple jobs.

        Args:
            profile: User profile
            jobs: List of (job, match_score) tuples
            tone: Writing tone
            format: Output format
            use_ai: Whether to use AI

        Returns:
            List of (file_path, content, job) tuples
        """
        results = []

        for job, match_score in jobs:
            try:
                filepath, content = self.generate(
                    profile=profile,
                    job=job,
                    match_score=match_score,
                    tone=tone,
                    format=format,
                    use_ai=use_ai,
                )
                results.append((filepath, content, job))
            except Exception as e:
                self.logger.error(f"Failed to generate cover letter for {job.company}: {e}")

        return results
