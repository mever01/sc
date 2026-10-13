"""Playwright browser lifecycle and anti-detection setup."""

import logging

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from src.config.browser import browser_settings

logger = logging.getLogger(__name__)

LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-infobars",
    "--window-size=1280,900",
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)

ERROR_SUPPRESSION_SCRIPT = """
    window.addEventListener('error', function(e) {
        if (e.message && (
            e.message.includes('not a function') ||
            e.message.includes('J0') ||
            e.message.includes('undefined')
        )) {
            e.preventDefault();
            e.stopImmediatePropagation();
            return true;
        }
    }, true);
"""

BLOCKED_PATTERNS = ("**/*google*/**", "**/*clarity*/**", "**/*facebook*/**")


class BrowserManager:
    """Manages Playwright browser lifecycle and anti-detection configuration."""

    def __init__(self) -> None:
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self.page: Page | None = None

    def start(self) -> Page:
        """Launch the browser with stealth options and return the active Page."""
        logger.info(
            "Launching browser: channel=%r, headless=%s",
            browser_settings.browser_channel,
            browser_settings.headless,
        )
        self._playwright = sync_playwright().start()

        try:
            self._browser = self._playwright.chromium.launch(
                channel=browser_settings.browser_channel,
                headless=browser_settings.headless,
                slow_mo=browser_settings.slow_mo,
                args=LAUNCH_ARGS,
            )
        except Exception as exc:
            logger.warning(
                "Could not launch via channel=%r: %s. Falling back to plain Chromium.",
                browser_settings.browser_channel,
                exc,
            )
            self._browser = self._playwright.chromium.launch(
                headless=browser_settings.headless,
                slow_mo=browser_settings.slow_mo,
                args=LAUNCH_ARGS,
            )

        self._context = self._browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=USER_AGENT,
            locale="en-US",
        )
        self.page = self._context.new_page()
        self.page.set_default_timeout(browser_settings.browser_timeout)

        for pattern in BLOCKED_PATTERNS:
            self.page.route(pattern, lambda route: route.abort())

        self.page.add_init_script(ERROR_SUPPRESSION_SCRIPT)
        return self.page

    def close(self) -> None:
        """Release browser and Playwright resources."""
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
        self.page = None
        logger.info("Browser closed.")
