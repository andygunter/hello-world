"""
Matrix Generator - Creates visual application tracking matrices.

Generates comprehensive views of all job applications with:
- Hiring likelihood percentages
- Match scores
- Status tracking
- Sortable/filterable data
"""

from datetime import datetime
from pathlib import Path
from typing import Optional
import json
import logging

from job_matcher.core.models import Application, ApplicationStatus


class MatrixGenerator:
    """Generates application tracking matrices in various formats."""

    # Status colors for visual display
    STATUS_COLORS = {
        ApplicationStatus.IDENTIFIED: "#e3f2fd",  # Light blue
        ApplicationStatus.RESUME_GENERATED: "#e8f5e9",  # Light green
        ApplicationStatus.COVER_LETTER_GENERATED: "#e8f5e9",
        ApplicationStatus.READY_TO_APPLY: "#fff3e0",  # Light orange
        ApplicationStatus.APPLIED: "#fff9c4",  # Light yellow
        ApplicationStatus.UNDER_REVIEW: "#f3e5f5",  # Light purple
        ApplicationStatus.INTERVIEW_SCHEDULED: "#e1f5fe",  # Cyan
        ApplicationStatus.REJECTED: "#ffebee",  # Light red
        ApplicationStatus.OFFER_RECEIVED: "#c8e6c9",  # Green
        ApplicationStatus.WITHDRAWN: "#eceff1",  # Grey
    }

    # Likelihood rating thresholds
    LIKELIHOOD_RATINGS = {
        90: ("Excellent", "🟢", "#4caf50"),
        75: ("High", "🟡", "#8bc34a"),
        60: ("Good", "🟠", "#ffeb3b"),
        40: ("Moderate", "🔴", "#ff9800"),
        0: ("Low", "⚫", "#f44336"),
    }

    def __init__(self, output_dir: str = "./matrices"):
        """
        Initialize the matrix generator.

        Args:
            output_dir: Directory for saving generated matrices
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate_matrix(
        self,
        applications: list[Application],
        sort_by: str = "hiring_likelihood",
        format: str = "html",
    ) -> str:
        """
        Generate an application tracking matrix.

        Args:
            applications: List of applications to include
            sort_by: Column to sort by
            format: Output format (html, markdown, json, csv)

        Returns:
            Path to the generated matrix file
        """
        # Sort applications
        sorted_apps = self._sort_applications(applications, sort_by)

        # Generate in requested format
        if format == "html":
            content = self._generate_html_matrix(sorted_apps)
            ext = "html"
        elif format == "markdown":
            content = self._generate_markdown_matrix(sorted_apps)
            ext = "md"
        elif format == "json":
            content = self._generate_json_matrix(sorted_apps)
            ext = "json"
        elif format == "csv":
            content = self._generate_csv_matrix(sorted_apps)
            ext = "csv"
        else:
            content = self._generate_markdown_matrix(sorted_apps)
            ext = "md"

        # Save file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"application_matrix_{timestamp}.{ext}"
        filepath = self.output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        self.logger.info(f"Generated matrix: {filepath}")
        return str(filepath)

    def _sort_applications(
        self,
        applications: list[Application],
        sort_by: str,
    ) -> list[Application]:
        """Sort applications by specified criteria."""
        sort_keys = {
            "hiring_likelihood": lambda a: a.match_score.hiring_likelihood,
            "overall_score": lambda a: a.match_score.overall_score,
            "compensation": lambda a: a.match_score.compensation_score,
            "company": lambda a: a.job.company.lower(),
            "title": lambda a: a.job.title.lower(),
            "status": lambda a: a.status.value,
            "applied_date": lambda a: a.applied_at or datetime.min,
            "created_date": lambda a: a.created_at,
        }

        key_func = sort_keys.get(sort_by, sort_keys["hiring_likelihood"])
        reverse = sort_by not in ["company", "title", "status"]

        return sorted(applications, key=key_func, reverse=reverse)

    def _get_likelihood_rating(self, likelihood: float) -> tuple[str, str, str]:
        """Get rating label, emoji, and color for a likelihood score."""
        for threshold, (label, emoji, color) in self.LIKELIHOOD_RATINGS.items():
            if likelihood >= threshold:
                return label, emoji, color
        return "Low", "⚫", "#f44336"

    def _generate_html_matrix(self, applications: list[Application]) -> str:
        """Generate an interactive HTML matrix."""
        rows = []

        for app in applications:
            rating, emoji, color = self._get_likelihood_rating(
                app.match_score.hiring_likelihood
            )
            status_color = self.STATUS_COLORS.get(app.status, "#ffffff")

            rows.append(f"""
            <tr>
                <td>{app.job.company}</td>
                <td>{app.job.title}</td>
                <td>{app.job.location}</td>
                <td style="background-color: {status_color}">{app.status.value.replace('_', ' ').title()}</td>
                <td style="text-align: center">{app.match_score.overall_score:.0f}%</td>
                <td style="text-align: center; background-color: {color}20">
                    {emoji} {app.match_score.hiring_likelihood:.0f}% ({rating})
                </td>
                <td style="text-align: center">{app.match_score.compensation_score:.0f}</td>
                <td>{app.applied_at.strftime('%Y-%m-%d') if app.applied_at else '-'}</td>
                <td>{'✓' if app.response_received else '-'}</td>
                <td><a href="{app.job.source_url}" target="_blank">View</a></td>
            </tr>
            """)

        # Calculate summary stats
        total = len(applications)
        avg_likelihood = sum(a.match_score.hiring_likelihood for a in applications) / total if total else 0
        applied_count = len([a for a in applications if a.status != ApplicationStatus.IDENTIFIED])
        response_count = len([a for a in applications if a.response_received])

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Job Application Matrix</title>
    <style>
        * {{
            box-sizing: border-box;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
        }}
        body {{
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        h1 {{
            color: #333;
            margin-bottom: 10px;
        }}
        .summary {{
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        .stat-card {{
            background: white;
            padding: 15px 25px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stat-card h3 {{
            margin: 0;
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
        }}
        .stat-card .value {{
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }}
        .controls {{
            margin-bottom: 15px;
        }}
        .controls input {{
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            width: 300px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }}
        th {{
            background: #2196f3;
            color: white;
            padding: 12px 15px;
            text-align: left;
            cursor: pointer;
            user-select: none;
        }}
        th:hover {{
            background: #1976d2;
        }}
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }}
        tr:hover {{
            background: #f5f5f5;
        }}
        tr:last-child td {{
            border-bottom: none;
        }}
        a {{
            color: #2196f3;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        .likelihood-bar {{
            height: 8px;
            background: #eee;
            border-radius: 4px;
            overflow: hidden;
        }}
        .likelihood-fill {{
            height: 100%;
            border-radius: 4px;
        }}
        .legend {{
            display: flex;
            gap: 15px;
            margin-top: 20px;
            flex-wrap: wrap;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 0.9em;
        }}
        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 4px;
        }}
        @media (max-width: 1200px) {{
            table {{
                display: block;
                overflow-x: auto;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Job Application Tracking Matrix</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <div class="summary">
            <div class="stat-card">
                <h3>Total Applications</h3>
                <div class="value">{total}</div>
            </div>
            <div class="stat-card">
                <h3>Applied</h3>
                <div class="value">{applied_count}</div>
            </div>
            <div class="stat-card">
                <h3>Responses</h3>
                <div class="value">{response_count}</div>
            </div>
            <div class="stat-card">
                <h3>Avg. Likelihood</h3>
                <div class="value">{avg_likelihood:.0f}%</div>
            </div>
        </div>

        <div class="controls">
            <input type="text" id="search" placeholder="Search by company or title..." onkeyup="filterTable()">
        </div>

        <table id="matrix">
            <thead>
                <tr>
                    <th onclick="sortTable(0)">Company ↕</th>
                    <th onclick="sortTable(1)">Title ↕</th>
                    <th onclick="sortTable(2)">Location ↕</th>
                    <th onclick="sortTable(3)">Status ↕</th>
                    <th onclick="sortTable(4)">Match % ↕</th>
                    <th onclick="sortTable(5)">Hiring Likelihood ↕</th>
                    <th onclick="sortTable(6)">Comp. Score ↕</th>
                    <th onclick="sortTable(7)">Applied ↕</th>
                    <th>Response</th>
                    <th>Link</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>

        <div class="legend">
            <strong>Likelihood Ratings:</strong>
            <div class="legend-item">
                <div class="legend-color" style="background: #4caf50"></div>
                🟢 Excellent (90%+)
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #8bc34a"></div>
                🟡 High (75-89%)
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #ffeb3b"></div>
                🟠 Good (60-74%)
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #ff9800"></div>
                🔴 Moderate (40-59%)
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #f44336"></div>
                ⚫ Low (&lt;40%)
            </div>
        </div>
    </div>

    <script>
        function filterTable() {{
            const input = document.getElementById('search');
            const filter = input.value.toLowerCase();
            const table = document.getElementById('matrix');
            const rows = table.getElementsByTagName('tr');

            for (let i = 1; i < rows.length; i++) {{
                const company = rows[i].cells[0].textContent.toLowerCase();
                const title = rows[i].cells[1].textContent.toLowerCase();
                if (company.includes(filter) || title.includes(filter)) {{
                    rows[i].style.display = '';
                }} else {{
                    rows[i].style.display = 'none';
                }}
            }}
        }}

        function sortTable(n) {{
            const table = document.getElementById('matrix');
            let rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
            switching = true;
            dir = 'asc';

            while (switching) {{
                switching = false;
                rows = table.rows;

                for (i = 1; i < (rows.length - 1); i++) {{
                    shouldSwitch = false;
                    x = rows[i].getElementsByTagName('td')[n];
                    y = rows[i + 1].getElementsByTagName('td')[n];

                    let xVal = x.textContent.toLowerCase();
                    let yVal = y.textContent.toLowerCase();

                    // Try to parse as number
                    const xNum = parseFloat(xVal.replace('%', ''));
                    const yNum = parseFloat(yVal.replace('%', ''));

                    if (!isNaN(xNum) && !isNaN(yNum)) {{
                        xVal = xNum;
                        yVal = yNum;
                    }}

                    if (dir === 'asc') {{
                        if (xVal > yVal) {{
                            shouldSwitch = true;
                            break;
                        }}
                    }} else if (dir === 'desc') {{
                        if (xVal < yVal) {{
                            shouldSwitch = true;
                            break;
                        }}
                    }}
                }}

                if (shouldSwitch) {{
                    rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
                    switching = true;
                    switchcount++;
                }} else {{
                    if (switchcount === 0 && dir === 'asc') {{
                        dir = 'desc';
                        switching = true;
                    }}
                }}
            }}
        }}
    </script>
</body>
</html>"""

        return html

    def _generate_markdown_matrix(self, applications: list[Application]) -> str:
        """Generate a Markdown matrix."""
        lines = [
            "# Job Application Tracking Matrix",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"**Total Applications:** {len(applications)}",
            "",
            "## Applications",
            "",
            "| Company | Title | Location | Status | Match | Likelihood | Applied |",
            "|---------|-------|----------|--------|-------|------------|---------|",
        ]

        for app in applications:
            rating, emoji, _ = self._get_likelihood_rating(app.match_score.hiring_likelihood)
            applied = app.applied_at.strftime('%Y-%m-%d') if app.applied_at else '-'
            status = app.status.value.replace('_', ' ').title()

            lines.append(
                f"| {app.job.company} | {app.job.title} | {app.job.location} | "
                f"{status} | {app.match_score.overall_score:.0f}% | "
                f"{emoji} {app.match_score.hiring_likelihood:.0f}% | {applied} |"
            )

        # Add summary
        lines.extend([
            "",
            "## Summary",
            "",
            "### By Status",
            "",
        ])

        status_counts = {}
        for app in applications:
            status = app.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        for status, count in sorted(status_counts.items()):
            lines.append(f"- **{status.replace('_', ' ').title()}:** {count}")

        # Likelihood distribution
        lines.extend([
            "",
            "### Likelihood Distribution",
            "",
        ])

        for threshold, (label, emoji, _) in self.LIKELIHOOD_RATINGS.items():
            count = len([a for a in applications
                        if a.match_score.hiring_likelihood >= threshold and
                        (threshold == 0 or a.match_score.hiring_likelihood < list(self.LIKELIHOOD_RATINGS.keys())[
                            list(self.LIKELIHOOD_RATINGS.keys()).index(threshold) - 1
                        ] if threshold > 0 else True)])
            # Simplified count for each bracket
            if threshold == 90:
                count = len([a for a in applications if a.match_score.hiring_likelihood >= 90])
            elif threshold == 75:
                count = len([a for a in applications if 75 <= a.match_score.hiring_likelihood < 90])
            elif threshold == 60:
                count = len([a for a in applications if 60 <= a.match_score.hiring_likelihood < 75])
            elif threshold == 40:
                count = len([a for a in applications if 40 <= a.match_score.hiring_likelihood < 60])
            else:
                count = len([a for a in applications if a.match_score.hiring_likelihood < 40])

            lines.append(f"- {emoji} **{label}:** {count}")

        return "\n".join(lines)

    def _generate_json_matrix(self, applications: list[Application]) -> str:
        """Generate a JSON matrix."""
        data = {
            "generated_at": datetime.now().isoformat(),
            "total_applications": len(applications),
            "summary": {
                "average_match_score": sum(a.match_score.overall_score for a in applications) / len(applications) if applications else 0,
                "average_hiring_likelihood": sum(a.match_score.hiring_likelihood for a in applications) / len(applications) if applications else 0,
                "by_status": {},
            },
            "applications": [],
        }

        # Status counts
        for app in applications:
            status = app.status.value
            data["summary"]["by_status"][status] = data["summary"]["by_status"].get(status, 0) + 1

        # Application details
        for app in applications:
            rating, _, _ = self._get_likelihood_rating(app.match_score.hiring_likelihood)

            data["applications"].append({
                "id": app.id,
                "company": app.job.company,
                "title": app.job.title,
                "location": app.job.location,
                "status": app.status.value,
                "match_score": round(app.match_score.overall_score, 1),
                "hiring_likelihood": round(app.match_score.hiring_likelihood, 1),
                "hiring_likelihood_rating": rating,
                "compensation_score": round(app.match_score.compensation_score, 1),
                "applied_date": app.applied_at.isoformat() if app.applied_at else None,
                "response_received": app.response_received,
                "source": app.job.source,
                "source_url": app.job.source_url,
                "matched_skills": app.match_score.matched_skills,
                "missing_skills": app.match_score.missing_skills,
            })

        return json.dumps(data, indent=2)

    def _generate_csv_matrix(self, applications: list[Application]) -> str:
        """Generate a CSV matrix."""
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "ID", "Company", "Title", "Location", "Status",
            "Match Score (%)", "Hiring Likelihood (%)", "Likelihood Rating",
            "Compensation Score", "Applied Date", "Response Received",
            "Source", "URL", "Matched Skills", "Missing Skills"
        ])

        # Rows
        for app in applications:
            rating, _, _ = self._get_likelihood_rating(app.match_score.hiring_likelihood)

            writer.writerow([
                app.id,
                app.job.company,
                app.job.title,
                app.job.location,
                app.status.value,
                f"{app.match_score.overall_score:.1f}",
                f"{app.match_score.hiring_likelihood:.1f}",
                rating,
                f"{app.match_score.compensation_score:.1f}",
                app.applied_at.strftime('%Y-%m-%d') if app.applied_at else "",
                "Yes" if app.response_received else "No",
                app.job.source,
                app.job.source_url,
                "; ".join(app.match_score.matched_skills),
                "; ".join(app.match_score.missing_skills),
            ])

        return output.getvalue()

    def generate_dashboard(self, applications: list[Application]) -> str:
        """
        Generate a comprehensive dashboard with multiple views.

        Args:
            applications: List of applications

        Returns:
            Path to the generated dashboard
        """
        # Generate the full HTML dashboard
        matrix_path = self.generate_matrix(applications, format="html")
        return matrix_path
