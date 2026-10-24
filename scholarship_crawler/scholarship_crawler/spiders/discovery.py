
from urllib.parse import urldefrag, urlparse

import scrapy
from scrapy.linkextractors import LinkExtractor
from pathlib import Path


# 1. Websites where the crawler starts
SEED_URLS = [
    "https://scholarships.gov.in/",
    "https://www.ugc.gov.in/",
    "https://www.education.gov.in/",
]

# 2. Crawling limits
MAX_PAGES = 50
MAX_DEPTH = 2
MAX_EXTERNAL_DOMAINS = 10



DATA_FOLDER = Path("data")
DATA_FOLDER.mkdir(exist_ok=True)

DATA_FOLDER = Path(__file__).resolve().parents[3] / "data"
DATA_FOLDER.mkdir(exist_ok=True)

OUTPUT_FILE = str(DATA_FOLDER / "discovered_urls.csv")

# 3. Words used to skip irrelevant pages
EXCLUDE_WORDS = [
    "terms", "privacy", "cookie", "disclaimer",
    "hyperlink", "login", "register", "signup",
    "contact-us", "helpdesk", "sitemap", "accessibility",
]

BLOCKED_DOMAINS = [
    "facebook.com", "instagram.com", "linkedin.com",
    "youtube.com", "twitter.com", "play.google.com",
    "apps.apple.com",
]

# Words suggesting a scholarship-related link
RELEVANT_WORDS = [
    "scholarship", "scholarships", "fellowship", "fellowships",
    "financial-aid", "financial aid", "student-funding",
    "student funding", "grant", "stipend", "bursary",
    "eligibility", "education-support", "education support",
    "student welfare", "apply now",
]

# Files not crawled as HTML pages in this stage
NON_HTML_EXTENSIONS = [
    "pdf", "jpg", "jpeg", "png", "gif", "svg",
    "zip", "rar", "doc", "docx", "xls", "xlsx",
    "ppt", "pptx", "mp3", "mp4", "css", "js",
]


# 4. Clean URLs
def clean_url(url):
    if not url:
        return None

    url, _ = urldefrag(url)
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None

    if parsed.path.strip("/").lower() in ("null", "undefined"):
        return None

    return url


# 5. Get a consistent domain name
def get_domain(url):
    domain = (urlparse(url).hostname or "").lower()

    # Treat www.example.com and example.com as the same domain
    if domain.startswith("www."):
        domain = domain[4:]

    return domain


# 6. Skip irrelevant links
def is_irrelevant(url, link_text=""):
    parsed = urlparse(url)
    domain = get_domain(url)

    text = (
        parsed.path + " " + link_text
    ).lower().replace("_", "-")

    # Skip social media websites
    for blocked in BLOCKED_DOMAINS:
        if domain == blocked or domain.endswith("." + blocked):
            return True

    # Skip documents, images and other non-HTML files
    if parsed.path.lower().endswith(
        tuple("." + ext for ext in NON_HTML_EXTENSIONS)
    ):
        return True

    # Skip unwanted pages
    for word in EXCLUDE_WORDS:
        if word in text:
            return True

    return False


# 7. Check whether a link looks relevant
def is_relevant(url, link_text=""):
    text = (url + " " + link_text).lower().replace("_", "-")

    return any(word in text for word in RELEVANT_WORDS)


# 8. Guess the page type from its URL
def page_type_for(url):
    path = urlparse(url).path.lower().replace("_", "-")

    words = [
        "scholarship", "fellowship", "financial-aid",
        "eligibility", "student-funding", "bursary", "stipend",
    ]

    if any(word in path for word in words):
        return "scholarship_page_candidate"

    return "source_page_candidate"


# 9. Main spider
class ScholarshipDiscoverySpider(scrapy.Spider):
    name = "scholarship_discovery"

    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "DOWNLOAD_DELAY": 1.5,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "DOWNLOAD_TIMEOUT": 20,
        "FEEDS": {
            OUTPUT_FILE: {
                "format": "csv",
                "overwrite": True,
                "encoding": "utf8",
                "fields": [
                    "url",
                    "domain",
                    "discovered_from",
                    "page_type",
                    "reason",
                    "status",
                ],
            }
        },
    }

    def __init__(
        self,
        max_pages=MAX_PAGES,
        max_depth=MAX_DEPTH,
        max_external_domains=MAX_EXTERNAL_DOMAINS,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.max_pages = int(max_pages)
        self.max_depth = int(max_depth)
        self.max_external_domains = int(max_external_domains)

        # URLs already scheduled or visited
        self.seen_urls = set()

        # Number of pages processed
        self.page_count = 0

        # Initially, only seed websites are allowed
        self.crawlable_domains = {
            get_domain(url) for url in SEED_URLS
        }

        # New external domains discovered during this run
        self.external_domains = set()

    # 10. Start from the seed websites
    async def start(self):
        for seed in SEED_URLS:
            url = clean_url(seed)

            if not url or is_irrelevant(url):
                continue

            if url in self.seen_urls:
                continue

            self.seen_urls.add(url)

            yield scrapy.Request(
                url,
                callback=self.parse,
                errback=self.request_failed,
                meta={
                    "depth": 0,
                    "parent": "seed",
                    "is_external_source": False,
                },
            )

    # 11. Visit pages and discover more links
    def parse(self, response):
        # Stop processing when the page limit is reached
        if self.page_count >= self.max_pages:
            return

        self.page_count += 1

        current_url = clean_url(response.url)
        if not current_url:
            return

        parent = response.meta.get("parent", "seed")
        depth = response.meta.get("depth", 0)
        is_external = response.meta.get(
            "is_external_source", False
        )

        self.logger.info("Visited: %s", current_url)

        # Record the page we visited
        if is_external:
            reason = (
                "External source candidate visited; "
                "official status not verified"
            )
            status = "visited_candidate"
        else:
            reason = (
                "Page visited; scholarship details not verified"
            )
            status = "visited"

        yield self.make_row(
            current_url,
            parent,
            page_type_for(current_url),
            reason,
            status,
        )

        # Stop following links at the depth limit
        if depth >= self.max_depth:
            return

        links = LinkExtractor(
            deny_extensions=NON_HTML_EXTENSIONS
        ).extract_links(response)

        for link in links:
            url = clean_url(link.url)
            link_text = " ".join((link.text or "").split())

            if not url or url in self.seen_urls:
                continue

            if is_irrelevant(url, link_text):
                continue

            current_domain = get_domain(current_url)
            target_domain = get_domain(url)

            # CASE A: Link is on the same website
            if target_domain == current_domain:

                if not is_relevant(url, link_text):
                    continue

                self.seen_urls.add(url)

                yield scrapy.Request(
                    url,
                    callback=self.parse,
                    errback=self.request_failed,
                    meta={
                        "depth": depth + 1,
                        "parent": current_url,
                        "is_external_source": is_external,
                    },
                )

            # CASE B: Link points to another website
            else:

                # Only consider promising external links
                if not is_relevant(url, link_text):
                    continue

                # Check whether this is a new domain
                if target_domain not in self.crawlable_domains:

                    # Stop discovering new domains at the limit
                    if len(self.external_domains) >= self.max_external_domains:
                        self.seen_urls.add(url)

                        yield self.make_row(
                            url,
                            current_url,
                            "external_source_candidate",
                            "External-domain limit reached",
                            "not_crawled_domain_limit",
                        )
                        continue

                    # Allow this domain for limited crawling.
                    # This does not verify that it is an official source.
                    self.external_domains.add(target_domain)
                    self.crawlable_domains.add(target_domain)

                    self.logger.info(
                        "New external domain candidate: %s",
                        target_domain,
                    )

                self.seen_urls.add(url)

                # Visit the external link and continue on that website
                yield scrapy.Request(
                    url,
                    callback=self.parse,
                    errback=self.request_failed,
                    meta={
                        "depth": 0,
                        "parent": current_url,
                        "is_external_source": (
                            target_domain in self.external_domains
                        ),
                    },
                )

    # 12. Create one CSV record
    def make_row(self, url, parent, page_type, reason, status):
        return {
            "url": url,
            "domain": urlparse(url).hostname or "",
            "discovered_from": parent,
            "page_type": page_type,
            "reason": reason,
            "status": status,
        }

    # 13. Handle failed requests
    def request_failed(self, failure):
        self.logger.warning(
            "Request failed: %s | %s",
            failure.request.url,
            failure.value,
        )
