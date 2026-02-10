"""Email notifications for pipeline completion."""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional

from rich.console import Console

from amsterdam_rent_scraper.config.settings import SMTP_CONFIG, is_email_configured

console = Console()


def send_pipeline_notification(
    stats_summary: str,
    listings_count: int,
    city: str,
    excel_path: str = None,
    html_path: str = None,
    failed_count: int = 0,
    duration_seconds: float = None,
) -> bool:
    """Send email notification when pipeline completes.

    Args:
        stats_summary: Text summary of pipeline statistics
        listings_count: Number of listings processed
        city: City that was scraped
        excel_path: Path to Excel output file
        html_path: Path to HTML output file
        failed_count: Number of failed operations
        duration_seconds: Pipeline duration in seconds

    Returns:
        True if email sent successfully, False otherwise
    """
    if not is_email_configured():
        console.print("[dim]Email notifications not configured (set SMTP_* env vars)[/]")
        return False

    try:
        # Build email content
        subject = f"Rental Scraper Complete: {city.title()} - {listings_count} listings"

        # Format duration
        duration_str = ""
        if duration_seconds:
            hours, remainder = divmod(int(duration_seconds), 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours > 0:
                duration_str = f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                duration_str = f"{minutes}m {seconds}s"
            else:
                duration_str = f"{seconds}s"

        # Build HTML email body
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #2c3e50; }}
                .stats {{ background: #f8f9fa; padding: 15px; border-radius: 5px; }}
                .success {{ color: #27ae60; }}
                .warning {{ color: #f39c12; }}
                .error {{ color: #e74c3c; }}
                pre {{ background: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 5px; overflow-x: auto; }}
                .footer {{ margin-top: 20px; color: #7f8c8d; font-size: 12px; }}
            </style>
        </head>
        <body>
            <h1>Rental Scraper Pipeline Complete</h1>

            <p><strong>City:</strong> {city.title()}</p>
            <p><strong>Listings:</strong> <span class="success">{listings_count}</span></p>
            {f'<p><strong>Duration:</strong> {duration_str}</p>' if duration_str else ''}
            {f'<p><strong>Failed operations:</strong> <span class="error">{failed_count}</span></p>' if failed_count > 0 else ''}

            <h2>Statistics</h2>
            <pre>{stats_summary}</pre>

            <h2>Output Files</h2>
            <ul>
                {f'<li>Excel: {excel_path}</li>' if excel_path else ''}
                {f'<li>HTML Report: {html_path}</li>' if html_path else ''}
            </ul>

            <div class="footer">
                <p>Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </body>
        </html>
        """

        # Plain text version
        text_body = f"""
Rental Scraper Pipeline Complete

City: {city.title()}
Listings: {listings_count}
{f'Duration: {duration_str}' if duration_str else ''}
{f'Failed operations: {failed_count}' if failed_count > 0 else ''}

Statistics:
{stats_summary}

Output Files:
- Excel: {excel_path or 'N/A'}
- HTML: {html_path or 'N/A'}

Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """

        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_CONFIG["from_email"] or SMTP_CONFIG["user"]
        msg["To"] = SMTP_CONFIG["to_email"]

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        # Send email
        with smtplib.SMTP(SMTP_CONFIG["host"], SMTP_CONFIG["port"]) as server:
            if SMTP_CONFIG["use_tls"]:
                server.starttls()
            server.login(SMTP_CONFIG["user"], SMTP_CONFIG["password"])
            server.send_message(msg)

        console.print(f"[green]Email notification sent to {SMTP_CONFIG['to_email']}[/]")
        return True

    except Exception as e:
        console.print(f"[red]Failed to send email notification: {e}[/]")
        return False


def send_error_notification(
    error_message: str,
    city: str,
    stage: str,
) -> bool:
    """Send email notification when pipeline fails.

    Args:
        error_message: Error description
        city: City that was being scraped
        stage: Pipeline stage where error occurred

    Returns:
        True if email sent successfully, False otherwise
    """
    if not is_email_configured():
        return False

    try:
        subject = f"Rental Scraper FAILED: {city.title()} at {stage}"

        text_body = f"""
Rental Scraper Pipeline Failed

City: {city.title()}
Stage: {stage}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Error:
{error_message}
        """

        msg = MIMEText(text_body)
        msg["Subject"] = subject
        msg["From"] = SMTP_CONFIG["from_email"] or SMTP_CONFIG["user"]
        msg["To"] = SMTP_CONFIG["to_email"]

        with smtplib.SMTP(SMTP_CONFIG["host"], SMTP_CONFIG["port"]) as server:
            if SMTP_CONFIG["use_tls"]:
                server.starttls()
            server.login(SMTP_CONFIG["user"], SMTP_CONFIG["password"])
            server.send_message(msg)

        return True

    except Exception:
        return False
