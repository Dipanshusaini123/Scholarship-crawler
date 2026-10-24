"""Verify discovered URLs by checking the actual HTML page content.

Input:
    data/discovered_urls.csv

Outputs (saved next to the input CSV):
    filtered_urls.csv  - pages with scholarship-specific details
    rejected_urls.csv  - pages rejected or not verifiable, with a reason

Install dependencies if needed:
    pip install requests beautifulsoup4

Run from the Assignment 2 project folder:
    python 02_filter_fixed.py
Or pass an explicit input:
    python 02_filter_fixed.py --input data/discovered_urls.csv
"""

import argparse
import csv
import re
import time
from pathlib import Path
from urllib.parse import urlparse, urldefrag
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup


# Keep the default input stable even if the command is run from another folder.
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_FOLDER = SCRIPT_DIR / "data"
DEFAULT_INPUT = DEFAULT_DATA_FOLDER / "discovered_urls.csv"

USER_AGENT = "ScholarshipResearchBot/1.0 (polite educational research crawler)"
REQUEST_TIMEOUT = 15
DELAY_SECONDS = 1.0
MIN_TEXT_LENGTH = 250

EXCLUDE_WORDS = [
    "terms", "privacy", "cookie", "disclaimer", "hyperlink",
    "login", "register", "signup", "contact-us", "helpdesk",
    "sitemap", "accessibility", "copyright-policy", "nodelofficerdetails",
]

BLOCKED_DOMAINS = [
    "facebook.com", "instagram.com", "linkedin.com", "youtube.com",
    "twitter.com", "x.com", "play.google.com", "apps.apple.com",
]

NON_HTML_EXTENSIONS = (
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".zip",
    ".rar", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".mp3", ".mp4", ".css", ".js",
)

# A scholarship-related term must occur in the actual page body/title.
SCHOLARSHIP_TERM_RE = re.compile(
    r"\b(scholarships?|fellowships?|bursaries|bursary|financial aid|"
    r"education grants?|student grants?|fee reimbursement|student funding|"
    r"post[- ]matric|pre[- ]matric)\b",
    re.IGNORECASE,
)

# These are different kinds of specific detail, not just generic keywords.
DETAIL_CATEGORIES = {
    "eligibility": re.compile(
        r"\b(eligibility|eligible candidates?|who can apply|eligibility criteria|"
        r"family income|annual income|minimum marks|minimum percentage|domicile|"
        r"pursuing (a|an|the)? ?(course|degree|class)|enrolled students?)\b",
        re.IGNORECASE,
    ),
    "financial_benefit": re.compile(
        r"\b(scholarship amount|award amount|financial assistance|tuition fees?|"
        r"maintenance allowance|stipend|fee reimbursement|per annum|per month|"
        r"amount of scholarship|funding amount)\b|₹\s?\d|\bINR\s?\d|\bRs\.?\s?\d",
        re.IGNORECASE,
    ),
    "application_process": re.compile(
        r"\b(how to apply|apply online|application process|application form|"
        r"submit (an? )?application|apply now|registration process|"
        r"applications? (are )?invited|application procedure)\b",
        re.IGNORECASE,
    ),
    "deadline": re.compile(
        r"\b(last date|deadline|closing date|application deadline|apply before|"
        r"applications? close|application start date|last date to apply|"
        r"extended date)\b",
        re.IGNORECASE,
    ),
    "selection_or_documents": re.compile(
        r"\b(selection process|selection criteria|merit list|documents required|"
        r"required documents|renewal criteria|shortlisting|verification of documents)\b",
        re.IGNORECASE,
    ),
}


def clean_url(url):
    """Remove URL fragments and reject malformed/non-web URLs."""
    if not url:
        return ""
    url = url.strip()
    url, _ = urldefrag(url)
    parts = urlparse(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return ""
    return url


def basic_rejection_reason(url):
    """Reject obviously unsuitable URLs before requesting their content."""
    if not url:
        return "Missing or invalid URL"

    parts = urlparse(url)
    domain = (parts.hostname or "").lower()
    if domain.startswith("www."):
        domain = domain[4:]

    for blocked in BLOCKED_DOMAINS:
        if domain == blocked or domain.endswith("." + blocked):
            return "Social media or app-store website"

    if parts.path.lower().endswith(NON_HTML_EXTENSIONS):
        return "Non-HTML document or asset; not checked in this stage"

    path_text = (parts.path + " " + parts.query).lower().replace("_", "-")
    for word in EXCLUDE_WORDS:
        if word in path_text:
            return "Irrelevant URL pattern: " + word

    return ""


def robots_allowed(url, session, cache):
    """Check robots.txt. Return True, False, or None if the check failed."""
    parts = urlparse(url)
    origin = f"{parts.scheme}://{parts.netloc}"

    if origin not in cache:
        robots_url = origin + "/robots.txt"
        parser = RobotFileParser()
        try:
            response = session.get(robots_url, timeout=REQUEST_TIMEOUT)
            if response.status_code == 404:
                parser.parse([])  # No robots.txt rules published.
            elif 200 <= response.status_code < 300:
                parser.parse(response.text.splitlines())
            else:
                cache[origin] = None
                return None
            cache[origin] = parser
        except requests.RequestException:
            cache[origin] = None
            return None

    parser = cache[origin]
    if parser is None:
        return None
    return parser.can_fetch(USER_AGENT, url)


def fetch_and_verify(url, session, robots_cache):
    """Fetch a URL and confirm that its body contains scholarship details."""
    result = {
        "final_url": url,
        "page_title": "",
        "http_status": "",
        "content_length": 0,
        "evidence_categories": "",
        "verification_result": "rejected",
        "filter_reason": "",
    }

    allowed = robots_allowed(url, session, robots_cache)
    if allowed is False:
        result["filter_reason"] = "Blocked by the website's robots.txt"
        return result
    if allowed is None:
        result["filter_reason"] = "Could not verify robots.txt; skipped fetch"
        return result

    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        result["http_status"] = response.status_code
        result["final_url"] = clean_url(response.url) or response.url

        if response.status_code < 200 or response.status_code >= 300:
            result["filter_reason"] = f"HTTP status {response.status_code}"
            return result

        content_type = response.headers.get("Content-Type", "").lower()
        if "html" not in content_type and "xhtml" not in content_type:
            result["filter_reason"] = "Response is not HTML"
            return result

        # A redirect may land on a login, policy, or unrelated page.
        redirect_reason = basic_rejection_reason(result["final_url"])
        if redirect_reason:
            result["filter_reason"] = "Redirected to an excluded page: " + redirect_reason
            return result

        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        result["page_title"] = title

        # Remove common site-wide elements so navigation/footer words do not
        # make an otherwise irrelevant page look like a scholarship page.
        for element in soup.find_all(["script", "style", "noscript", "svg", "nav", "footer"]):
            element.decompose()

        body = soup.body if soup.body else soup
        body_text = " ".join(body.get_text(" ", strip=True).split())
        content = (title + " " + body_text).lower()
        result["content_length"] = len(body_text)

        if len(body_text) < MIN_TEXT_LENGTH:
            result["filter_reason"] = (
                f"Too little readable page text ({len(body_text)} characters); "
                "scholarship details could not be verified"
            )
            return result

        if not SCHOLARSHIP_TERM_RE.search(content):
            result["filter_reason"] = "No scholarship-specific topic found in page content"
            return result

        matched_categories = [
            category
            for category, pattern in DETAIL_CATEGORIES.items()
            if pattern.search(content)
        ]
        result["evidence_categories"] = ";".join(matched_categories)

        # Require at least two distinct kinds of detail. This avoids passing a
        # page just because the word 'scholarship' appears in its URL or menu.
        if len(matched_categories) < 2:
            result["filter_reason"] = (
                "Scholarship is mentioned, but fewer than two types of "
                "specific details were found"
            )
            return result

        result["verification_result"] = "verified_scholarship_information"
        result["filter_reason"] = (
            "Verified from page content; evidence: " + ", ".join(matched_categories)
        )
        return result

    except requests.RequestException as exc:
        result["filter_reason"] = "Request failed: " + exc.__class__.__name__
        return result
    except Exception as exc:
        result["filter_reason"] = "Could not parse page: " + exc.__class__.__name__
        return result


def main():
    parser = argparse.ArgumentParser(
        description="Verify scholarship URLs using the actual page content."
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
        help="Input CSV (default: data/discovered_urls.csv beside this script)",
    )
    args = parser.parse_args()

    input_file = Path(args.input).expanduser().resolve()
    if not input_file.exists():
        print("Input CSV not found:", input_file)
        print("Pass the correct path using --input.")
        return

    print("Reading discovered URLs from:", input_file)

    with input_file.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames or "url" not in reader.fieldnames:
            print("Error: input CSV must contain a column named 'url'.")
            return
        original_columns = list(reader.fieldnames)
        rows = list(reader)

    # Output to the same folder as the input so the paths cannot silently diverge.
    output_folder = input_file.parent
    output_file = output_folder / "filtered_urls.csv"
    rejected_file = output_folder / "rejected_urls.csv"

    extra_columns = [
        "page_title", "http_status", "content_length", "evidence_categories",
        "verification_result", "filter_reason",
    ]
    output_columns = list(dict.fromkeys(original_columns + extra_columns))

    filtered_rows = []
    rejected_rows = []
    seen_urls = set()
    robots_cache = {}

    with requests.Session() as session:
        session.headers.update({"User-Agent": USER_AGENT})

        for index, row in enumerate(rows, start=1):
            url = clean_url(row.get("url", ""))
            row["url"] = url
            print(f"[{index}/{len(rows)}] Checking: {url or '(missing URL)'}")

            reason = basic_rejection_reason(url)
            if not reason and url in seen_urls:
                reason = "Duplicate URL"

            if reason:
                details = {
                    "page_title": "", "http_status": "", "content_length": 0,
                    "evidence_categories": "", "verification_result": "rejected",
                    "filter_reason": reason,
                }
            else:
                details = fetch_and_verify(url, session, robots_cache)
                # Also de-duplicate redirects that resolve to the same final URL.
                final_url = details.get("final_url", url)
                if details["verification_result"] == "verified_scholarship_information":
                    if final_url in seen_urls:
                        details["verification_result"] = "rejected"
                        details["filter_reason"] = "Duplicate final URL after redirect"
                    else:
                        seen_urls.add(url)
                        seen_urls.add(final_url)

            row.update(details)
            if row["verification_result"] == "verified_scholarship_information":
                filtered_rows.append(row)
            else:
                rejected_rows.append(row)

            # Be polite to websites; requests are sequential, not parallel.
            time.sleep(DELAY_SECONDS)

    for filepath, data in ((output_file, filtered_rows), (rejected_file, rejected_rows)):
        with filepath.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=output_columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(data)

    print("\nFiltering and content verification completed.")
    print("Total URLs checked:", len(rows))
    print("Verified scholarship pages:", len(filtered_rows), "->", output_file)
    print("Rejected/unverified pages:", len(rejected_rows), "->", rejected_file)
    print("Note: pages that require JavaScript rendering may be marked unverified.")


if __name__ == "__main__":
    main()
