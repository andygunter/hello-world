# Job Matcher - Automated Job Search & Application System

An intelligent job matching and application automation system that analyzes your professional profile, searches for optimal positions across multiple job boards, generates customized application materials, and tracks all applications with hiring likelihood scores.

## Features

### 🔍 Smart Job Search
- **Multi-platform search**: Aggregates jobs from Indeed, LinkedIn, Glassdoor, Greenhouse, and Lever
- **Profile-based matching**: Automatically searches for jobs matching your skills and experience
- **Parallel searching**: Searches multiple providers simultaneously for faster results

### 🎯 Intelligent Matching
- **Comprehensive scoring**: Evaluates skill match, experience, education, location, and salary
- **Hiring likelihood**: Estimates your probability of getting hired based on multiple factors
- **Skills gap analysis**: Identifies matched, missing, and bonus skills for each position

### 📝 Document Generation
- **Customized resumes**: Tailors your resume for each specific job posting
- **Cover letter generation**: Creates personalized cover letters highlighting relevant experience
- **AI-powered optimization**: Uses Claude/GPT to enhance content (optional)
- **Multiple formats**: Supports Markdown, HTML, and plain text output

### 📊 Application Tracking Matrix
- **Visual dashboard**: Interactive HTML matrix of all applications
- **Likelihood ratings**: Color-coded hiring probability scores
- **Status tracking**: Track applications from identified to offer received
- **Export options**: CSV, JSON, and Markdown exports

### 🤖 Auto-Apply (with Safeguards)
- **API-based applications**: Direct submission to Greenhouse and Lever job boards
- **Rate limiting**: Prevents spam with configurable limits
- **Dry-run mode**: Test the system without submitting real applications
- **Confirmation prompts**: Review each application before submission

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/job-matcher.git
cd job-matcher

# Install dependencies
pip install -r requirements.txt

# Optional: Install with AI support
pip install anthropic  # For Claude AI
# or
pip install openai     # For GPT
```

## Quick Start

### 1. Create Your Profile

Create a profile file (`profile.json`) with your information:

```json
{
  "full_name": "John Doe",
  "email": "john.doe@example.com",
  "phone": "555-123-4567",
  "location": "San Francisco, CA",
  "summary": "Experienced software engineer with 5+ years in Python and cloud technologies.",
  "skills": [
    {"name": "Python", "level": "EXPERT", "years_experience": 5},
    {"name": "JavaScript", "level": "ADVANCED", "years_experience": 4},
    {"name": "AWS", "level": "ADVANCED", "years_experience": 3},
    {"name": "Docker", "level": "INTERMEDIATE", "years_experience": 2}
  ],
  "experiences": [
    {
      "title": "Senior Software Engineer",
      "company": "Tech Corp",
      "start_date": "2020-01-01",
      "is_current": true,
      "description": "Leading backend development team",
      "achievements": [
        "Reduced API latency by 40%",
        "Implemented CI/CD pipeline saving 10 hours/week"
      ]
    }
  ],
  "education": [
    {
      "institution": "State University",
      "degree": "Bachelor's",
      "field_of_study": "Computer Science",
      "graduation_date": "2018-05-01"
    }
  ],
  "desired_roles": ["Senior Software Engineer", "Staff Engineer", "Tech Lead"],
  "desired_locations": ["San Francisco", "Remote"],
  "min_salary": 150000,
  "remote_preference": "flexible"
}
```

Or parse an existing resume:

```bash
python -m job_matcher profile --parse resume.pdf --output profile.json
```

### 2. Search for Jobs

```bash
# Search based on your profile
python -m job_matcher search --profile profile.json --limit 50

# Or search with specific criteria
python -m job_matcher search --role "Software Engineer" --location "Remote" --remote

# Save results to file
python -m job_matcher search --profile profile.json --output jobs.json
```

### 3. Match Jobs to Your Profile

```bash
# See how well you match found jobs
python -m job_matcher match --profile profile.json --search "Python Developer" --top 10

# Match against a specific jobs file
python -m job_matcher match --profile profile.json --jobs jobs.json --sort likelihood
```

### 4. Generate Application Materials

```bash
# Generate resume and cover letter for a specific job
python -m job_matcher generate --profile profile.json --job-id "greenhouse_airbnb_12345"

# Generate with AI enhancement (requires API key)
python -m job_matcher config --set-api-key anthropic "your-api-key"
python -m job_matcher generate --profile profile.json --job-id "lever_netflix_67890"
```

### 5. Track Applications

```bash
# View all applications
python -m job_matcher track --list

# View statistics
python -m job_matcher track --stats

# Update application status
python -m job_matcher track --update "app-id" --new-status "interview_scheduled"

# Export to CSV
python -m job_matcher track --export applications.csv
```

### 6. Generate Tracking Matrix

```bash
# Create interactive HTML dashboard
python -m job_matcher matrix --format html

# Create markdown report
python -m job_matcher matrix --format markdown --sort likelihood
```

## Configuration

Configure the application via the CLI or config file:

```bash
# Initialize configuration
python -m job_matcher config --init

# Set API keys
python -m job_matcher config --set-api-key linkedin "your-key"
python -m job_matcher config --set-api-key anthropic "your-key"

# View current configuration
python -m job_matcher config --show
```

Configuration file location: `~/.job_matcher/config.json`

### Environment Variables

API keys can also be set via environment variables:

```bash
export LINKEDIN_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"
export INDEED_API_KEY="your-key"
```

## Auto-Apply Mode

**Important**: Auto-apply features should only be used with job boards that explicitly allow API submissions. Always review terms of service.

```bash
# Dry run (simulates without actually applying)
python -m job_matcher apply --profile profile.json --top 5 --dry-run

# Apply with confirmation prompts
python -m job_matcher apply --profile profile.json --application-id "app-123"

# Batch apply (use with caution)
python -m job_matcher apply --profile profile.json --top 10 --no-confirm
```

## Project Structure

```
job_matcher/
├── __init__.py          # Package initialization
├── __main__.py          # Entry point
├── cli.py               # Command-line interface
├── core/
│   ├── models.py        # Data models (Profile, Job, Application, etc.)
│   ├── profile_parser.py # Resume/profile parsing
│   └── matcher.py       # Job matching algorithm
├── integrations/
│   ├── base.py          # Base provider class
│   ├── indeed.py        # Indeed integration
│   ├── linkedin.py      # LinkedIn integration
│   ├── glassdoor.py     # Glassdoor integration
│   ├── greenhouse.py    # Greenhouse ATS integration
│   ├── lever.py         # Lever ATS integration
│   └── aggregator.py    # Multi-provider aggregator
├── generators/
│   ├── resume_generator.py    # Custom resume generation
│   ├── cover_letter_generator.py # Custom cover letter generation
│   └── document_manager.py    # Document coordination
├── tracker/
│   ├── application_tracker.py # Application lifecycle tracking
│   └── matrix_generator.py    # Visual matrix generation
└── utils/
    ├── auto_apply.py    # Auto-application with safeguards
    └── config.py        # Configuration management
```

## Application Status Flow

```
IDENTIFIED → RESUME_GENERATED → COVER_LETTER_GENERATED → READY_TO_APPLY
                                                              ↓
                                                          APPLIED
                                                              ↓
                                                       UNDER_REVIEW
                                                              ↓
                                                 INTERVIEW_SCHEDULED
                                                        ↓         ↓
                                              OFFER_RECEIVED   REJECTED
                                                        ↓
                                                   WITHDRAWN
```

## Match Score Components

| Component | Weight | Description |
|-----------|--------|-------------|
| Skill Match | 35% | How well your skills match job requirements |
| Experience | 20% | Years and relevance of experience |
| Location | 15% | Geographic compatibility |
| Salary | 20% | Compensation vs. expectations |
| Education | 10% | Degree and field alignment |

## Hiring Likelihood Factors

The hiring likelihood score considers:
- Skill match percentage (40%)
- Experience alignment (25%)
- Market demand for your skills (15%)
- Application timing (10%)
- Company culture fit indicators (10%)

## Supported Job Boards

| Provider | API Support | Features |
|----------|-------------|----------|
| Indeed | Partial | Job search, company info |
| LinkedIn | OAuth required | Job search, company insights |
| Glassdoor | Partner API | Job search, salary data, reviews |
| Greenhouse | Public API | Direct job search, application submission |
| Lever | Public API | Direct job search, application submission |

## Privacy & Security

- All data is stored locally by default
- API keys are stored in your config file (keep secure)
- No data is sent to external servers except for job searches
- Auto-apply logs all actions for audit trail

## Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests.

## License

MIT License - see LICENSE file for details.

## Disclaimer

This tool is provided for educational and personal use. Always:
- Review terms of service for each job board
- Use auto-apply features responsibly
- Verify all generated content before submission
- Keep your profile information accurate and up-to-date
