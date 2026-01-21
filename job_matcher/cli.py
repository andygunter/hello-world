"""
Job Matcher CLI - Command line interface for the job matching application.

Usage:
    python -m job_matcher.cli [command] [options]

Commands:
    search      Search for jobs matching your profile
    match       Analyze how well you match specific jobs
    generate    Generate customized resume and cover letter
    apply       Apply to jobs (with safeguards)
    track       View and manage application tracking
    matrix      Generate application tracking matrix
    config      Manage configuration
    profile     Manage your profile

Examples:
    python -m job_matcher.cli search --role "Software Engineer" --location "Remote"
    python -m job_matcher.cli generate --job-id "greenhouse_airbnb_12345"
    python -m job_matcher.cli matrix --format html
    python -m job_matcher.cli track --status applied
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from job_matcher.core import ProfileParser, JobMatcher, UserProfile
from job_matcher.integrations import JobAggregator
from job_matcher.generators import DocumentManager
from job_matcher.tracker import ApplicationTracker, MatrixGenerator
from job_matcher.utils import AutoApplicant, Config


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Job Matcher - Automated job search, matching, and application system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search for jobs")
    search_parser.add_argument("--role", "-r", help="Job role/title to search for")
    search_parser.add_argument("--location", "-l", help="Location filter")
    search_parser.add_argument("--remote", action="store_true", help="Remote jobs only")
    search_parser.add_argument("--limit", "-n", type=int, default=50, help="Max results")
    search_parser.add_argument("--providers", help="Comma-separated list of providers")
    search_parser.add_argument("--profile", "-p", help="Path to profile file")
    search_parser.add_argument("--min-salary", type=int, help="Minimum salary")
    search_parser.add_argument("--output", "-o", help="Output file (JSON)")

    # Match command
    match_parser = subparsers.add_parser("match", help="Match profile against jobs")
    match_parser.add_argument("--profile", "-p", required=True, help="Path to profile file")
    match_parser.add_argument("--jobs", "-j", help="Path to jobs file (JSON)")
    match_parser.add_argument("--search", "-s", help="Search query for jobs")
    match_parser.add_argument("--top", "-t", type=int, default=10, help="Show top N matches")
    match_parser.add_argument("--sort", choices=["overall", "likelihood", "compensation"], default="likelihood")

    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate resume and cover letter")
    gen_parser.add_argument("--profile", "-p", required=True, help="Path to profile file")
    gen_parser.add_argument("--job-id", "-j", help="Job ID to generate documents for")
    gen_parser.add_argument("--job-file", help="Job data file (JSON)")
    gen_parser.add_argument("--format", "-f", choices=["markdown", "html", "txt"], default="markdown")
    gen_parser.add_argument("--no-ai", action="store_true", help="Disable AI enhancement")
    gen_parser.add_argument("--output-dir", "-o", help="Output directory")

    # Apply command
    apply_parser = subparsers.add_parser("apply", help="Apply to jobs")
    apply_parser.add_argument("--profile", "-p", required=True, help="Path to profile file")
    apply_parser.add_argument("--application-id", "-a", help="Specific application ID")
    apply_parser.add_argument("--top", "-t", type=int, help="Apply to top N matches")
    apply_parser.add_argument("--dry-run", action="store_true", help="Simulate applications")
    apply_parser.add_argument("--no-confirm", action="store_true", help="Skip confirmation prompts")

    # Track command
    track_parser = subparsers.add_parser("track", help="Track applications")
    track_parser.add_argument("--list", "-l", action="store_true", help="List all applications")
    track_parser.add_argument("--status", "-s", help="Filter by status")
    track_parser.add_argument("--update", "-u", help="Application ID to update")
    track_parser.add_argument("--new-status", help="New status for update")
    track_parser.add_argument("--stats", action="store_true", help="Show statistics")
    track_parser.add_argument("--export", "-e", help="Export to CSV file")

    # Matrix command
    matrix_parser = subparsers.add_parser("matrix", help="Generate tracking matrix")
    matrix_parser.add_argument("--format", "-f", choices=["html", "markdown", "json", "csv"], default="html")
    matrix_parser.add_argument("--sort", "-s", choices=["likelihood", "score", "company", "date"], default="likelihood")
    matrix_parser.add_argument("--output", "-o", help="Output file path")

    # Config command
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_parser.add_argument("--show", action="store_true", help="Show current config")
    config_parser.add_argument("--set", nargs=2, metavar=("KEY", "VALUE"), help="Set a config value")
    config_parser.add_argument("--set-api-key", nargs=2, metavar=("PROVIDER", "KEY"), help="Set API key")
    config_parser.add_argument("--init", action="store_true", help="Initialize default config")

    # Profile command
    profile_parser = subparsers.add_parser("profile", help="Manage profile")
    profile_parser.add_argument("--parse", help="Parse resume file into profile")
    profile_parser.add_argument("--show", help="Show profile from file")
    profile_parser.add_argument("--create-sample", action="store_true", help="Create sample profile")
    profile_parser.add_argument("--output", "-o", help="Output file for profile")

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Load configuration
    config = Config()

    # Execute command
    try:
        if args.command == "search":
            cmd_search(args, config)
        elif args.command == "match":
            cmd_match(args, config)
        elif args.command == "generate":
            cmd_generate(args, config)
        elif args.command == "apply":
            cmd_apply(args, config)
        elif args.command == "track":
            cmd_track(args, config)
        elif args.command == "matrix":
            cmd_matrix(args, config)
        elif args.command == "config":
            cmd_config(args, config)
        elif args.command == "profile":
            cmd_profile(args, config)
        else:
            parser.print_help()

    except KeyboardInterrupt:
        print("\n\nOperation cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


def cmd_search(args, config: Config):
    """Execute search command."""
    print("🔍 Searching for jobs...")

    # Load profile if provided
    profile = None
    if args.profile:
        parser = ProfileParser()
        profile = parser.parse_file(args.profile)
        print(f"   Loaded profile: {profile.full_name}")

    # Initialize aggregator
    aggregator = JobAggregator(config.get_providers_config())

    # Parse providers
    providers = None
    if args.providers:
        providers = [p.strip() for p in args.providers.split(",")]

    # Search
    if profile and not args.role:
        # Search based on profile
        jobs = aggregator.search_for_profile(
            profile=profile,
            limit=args.limit,
            providers=providers,
        )
    else:
        # Search based on query
        jobs = aggregator.search_jobs(
            query=args.role or "Software Engineer",
            location=args.location,
            remote=args.remote,
            salary_min=args.min_salary,
            limit=args.limit,
            providers=providers,
        )

    print(f"\n✅ Found {len(jobs)} jobs\n")

    # Display results
    for i, job in enumerate(jobs[:20], 1):
        salary = ""
        if job.salary_min or job.salary_max:
            salary = f" | ${job.salary_min or '?'}k-${job.salary_max or '?'}k"

        print(f"{i:2}. {job.title}")
        print(f"    {job.company} | {job.location}{salary}")
        print(f"    Source: {job.source} | ID: {job.id}")
        print()

    # Save to file if requested
    if args.output:
        output_data = [job.to_dict() for job in jobs]
        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2, default=str)
        print(f"💾 Saved {len(jobs)} jobs to {args.output}")


def cmd_match(args, config: Config):
    """Execute match command."""
    print("🎯 Matching profile against jobs...")

    # Load profile
    parser = ProfileParser()
    profile = parser.parse_file(args.profile)
    print(f"   Profile: {profile.full_name}")
    print(f"   Skills: {len(profile.skills)} | Experience: {profile.total_experience_years:.1f} years")

    # Get jobs
    jobs = []

    if args.jobs:
        with open(args.jobs, 'r') as f:
            jobs_data = json.load(f)
        from job_matcher.core.models import Job
        jobs = [Job(**j) if isinstance(j, dict) else j for j in jobs_data]
    elif args.search:
        aggregator = JobAggregator(config.get_providers_config())
        jobs = aggregator.search_jobs(query=args.search, limit=50)
    else:
        print("Error: Provide --jobs file or --search query")
        return

    print(f"   Jobs to match: {len(jobs)}")

    # Match jobs
    matcher = JobMatcher(profile)

    sort_map = {
        "overall": "overall",
        "likelihood": "hiring_likelihood",
        "compensation": "compensation",
    }

    ranked = matcher.rank_jobs(jobs, sort_by=sort_map[args.sort])

    print(f"\n📊 Top {args.top} Matches (sorted by {args.sort}):\n")
    print("-" * 80)

    for i, (job, score) in enumerate(ranked[:args.top], 1):
        print(f"\n{i}. {job.title} @ {job.company}")
        print(f"   Location: {job.location}")
        print(f"   📈 Overall Match: {score.overall_score:.0f}%")
        print(f"   🎲 Hiring Likelihood: {score.hiring_likelihood:.0f}%")
        print(f"   💰 Compensation Score: {score.compensation_score:.0f}")
        print(f"   ✅ Matched Skills: {', '.join(score.matched_skills[:5])}")
        if score.missing_skills:
            print(f"   ❌ Missing Skills: {', '.join(score.missing_skills[:3])}")


def cmd_generate(args, config: Config):
    """Execute generate command."""
    print("📝 Generating application documents...")

    # Load profile
    parser = ProfileParser()
    profile = parser.parse_file(args.profile)
    print(f"   Profile: {profile.full_name}")

    # Get job
    job = None

    if args.job_file:
        with open(args.job_file, 'r') as f:
            job_data = json.load(f)
        from job_matcher.core.models import Job
        job = Job(**job_data)
    elif args.job_id:
        aggregator = JobAggregator(config.get_providers_config())
        job = aggregator.get_job_details(args.job_id)

    if not job:
        print("Error: Could not load job. Provide --job-file or valid --job-id")
        return

    print(f"   Job: {job.title} @ {job.company}")

    # Match first
    matcher = JobMatcher(profile)
    match_score = matcher.match_job(job)
    print(f"   Match Score: {match_score.overall_score:.0f}%")

    # Generate documents
    output_dir = args.output_dir or config.get_output_dir()
    ai_key = config.get_api_key("anthropic") or config.get_api_key("openai")

    doc_manager = DocumentManager(
        output_dir=output_dir,
        ai_api_key=ai_key if not args.no_ai else None,
    )

    from job_matcher.core.models import Application
    application = Application(
        job=job,
        profile=profile,
        match_score=match_score,
    )

    application = doc_manager.generate_application_documents(
        application=application,
        formats=[args.format],
        use_ai=not args.no_ai and bool(ai_key),
    )

    print(f"\n✅ Documents generated:")
    print(f"   📄 Resume: {application.customized_resume_path}")
    print(f"   📄 Cover Letter: {application.customized_cover_letter_path}")


def cmd_apply(args, config: Config):
    """Execute apply command."""
    print("📨 Preparing job applications...")

    # Load profile
    parser = ProfileParser()
    profile = parser.parse_file(args.profile)

    # Initialize components
    tracker = ApplicationTracker(config.get_data_dir())

    dry_run = args.dry_run or config.is_dry_run()
    applicant = AutoApplicant(
        profile=profile,
        dry_run=dry_run,
        require_confirmation=not args.no_confirm,
    )

    if dry_run:
        print("   ⚠️  DRY RUN MODE - No actual applications will be submitted")

    if args.application_id:
        # Apply to specific application
        application = tracker.get_application(args.application_id)
        if not application:
            print(f"Error: Application {args.application_id} not found")
            return

        success, message = applicant.apply(
            application=application,
            resume_content=application.customized_resume_content,
            cover_letter_content=application.customized_cover_letter_content,
        )

        print(f"\n{'✅' if success else '❌'} {message}")

    elif args.top:
        # Apply to top matches
        applications = tracker.get_top_opportunities(limit=args.top)

        if not applications:
            print("No applications found. Run 'search' and 'generate' first.")
            return

        print(f"   Found {len(applications)} applications to process")

        for app in applications:
            success, message = applicant.apply(
                application=app,
                resume_content=app.customized_resume_content,
                cover_letter_content=app.customized_cover_letter_content,
            )
            print(f"   {'✅' if success else '❌'} {app.job.company}: {message}")

    else:
        print("Error: Specify --application-id or --top N")


def cmd_track(args, config: Config):
    """Execute track command."""
    tracker = ApplicationTracker(config.get_data_dir())

    if args.stats:
        stats = tracker.get_statistics()
        print("\n📊 Application Statistics")
        print("=" * 40)
        print(f"Total Applications: {stats['total']}")
        print(f"Active Applications: {stats.get('active_applications', 0)}")
        print(f"Average Match Score: {stats['average_match_score']:.1f}%")
        print(f"Average Hiring Likelihood: {stats['average_hiring_likelihood']:.1f}%")
        print(f"Response Rate: {stats['response_rate']:.1f}%")
        print("\nBy Status:")
        for status, count in stats.get('by_status', {}).items():
            print(f"  {status.replace('_', ' ').title()}: {count}")

    elif args.update and args.new_status:
        from job_matcher.core.models import ApplicationStatus
        try:
            status = ApplicationStatus(args.new_status)
            app = tracker.update_status(args.update, status)
            if app:
                print(f"✅ Updated {app.job.company} to '{args.new_status}'")
            else:
                print(f"❌ Application {args.update} not found")
        except ValueError:
            print(f"❌ Invalid status: {args.new_status}")
            print(f"   Valid statuses: {[s.value for s in ApplicationStatus]}")

    elif args.export:
        path = tracker.export_to_csv(args.export)
        print(f"✅ Exported to {path}")

    elif args.list or args.status:
        if args.status:
            from job_matcher.core.models import ApplicationStatus
            try:
                status = ApplicationStatus(args.status)
                applications = tracker.get_applications_by_status(status)
            except ValueError:
                print(f"Invalid status: {args.status}")
                return
        else:
            applications = tracker.get_all_applications()

        print(f"\n📋 Applications ({len(applications)} total)\n")
        print("-" * 80)

        for app in applications:
            print(f"\n{app.job.company} - {app.job.title}")
            print(f"   Status: {app.status.value.replace('_', ' ').title()}")
            print(f"   Match: {app.match_score.overall_score:.0f}% | Likelihood: {app.match_score.hiring_likelihood:.0f}%")
            print(f"   ID: {app.id[:8]}...")

    else:
        # Default: show summary
        stats = tracker.get_statistics()
        print(f"\n📋 Tracking {stats['total']} applications")
        print(f"   Run 'track --list' to see all")
        print(f"   Run 'track --stats' for statistics")


def cmd_matrix(args, config: Config):
    """Execute matrix command."""
    print("📊 Generating application matrix...")

    tracker = ApplicationTracker(config.get_data_dir())
    applications = tracker.get_all_applications()

    if not applications:
        print("No applications found. Run 'search' and 'track' first.")
        return

    generator = MatrixGenerator(output_dir="./matrices")

    sort_map = {
        "likelihood": "hiring_likelihood",
        "score": "overall_score",
        "company": "company",
        "date": "applied_date",
    }

    filepath = generator.generate_matrix(
        applications=applications,
        sort_by=sort_map.get(args.sort, "hiring_likelihood"),
        format=args.format,
    )

    print(f"\n✅ Matrix generated: {filepath}")

    if args.format == "html":
        print(f"   Open in browser to view interactive matrix")


def cmd_config(args, config: Config):
    """Execute config command."""
    if args.init:
        config.save()
        print(f"✅ Created config at: {config.config_path}")

    elif args.show:
        print("\n📋 Current Configuration\n")
        config.print_config()

    elif args.set:
        key, value = args.set
        # Try to parse as JSON for complex values
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            pass

        config.set(key, value)
        config.save()
        print(f"✅ Set {key} = {value}")

    elif args.set_api_key:
        provider, key = args.set_api_key
        config.set_api_key(provider, key)
        print(f"✅ Set API key for {provider}")

    else:
        print("Use --show, --set, --set-api-key, or --init")


def cmd_profile(args, config: Config):
    """Execute profile command."""
    parser = ProfileParser()

    if args.create_sample:
        profile = parser.create_sample_profile()
        output = args.output or "sample_profile.json"
        with open(output, 'w') as f:
            json.dump(profile.to_dict(), f, indent=2, default=str)
        print(f"✅ Created sample profile: {output}")

    elif args.parse:
        profile = parser.parse_file(args.parse)
        print("\n📋 Parsed Profile\n")
        print(f"Name: {profile.full_name}")
        print(f"Email: {profile.email}")
        print(f"Phone: {profile.phone}")
        print(f"Location: {profile.location}")
        print(f"\nSkills ({len(profile.skills)}):")
        for skill in profile.skills[:10]:
            print(f"  - {skill.name} ({skill.level.name})")

        print(f"\nExperience ({len(profile.experiences)} positions):")
        for exp in profile.experiences[:3]:
            print(f"  - {exp.title} @ {exp.company}")

        if args.output:
            with open(args.output, 'w') as f:
                json.dump(profile.to_dict(), f, indent=2, default=str)
            print(f"\n💾 Saved profile to: {args.output}")

    elif args.show:
        with open(args.show, 'r') as f:
            data = json.load(f)
        print(json.dumps(data, indent=2))

    else:
        print("Use --parse, --show, or --create-sample")


if __name__ == "__main__":
    main()
