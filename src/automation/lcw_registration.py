"""Browser automation for LC Waikiki registration form."""

import base64
import logging
import random
import string
import time

from playwright.sync_api import Page

from src.browser import BrowserManager
from src.captcha import DdddocrSolver, solve_via_ollama
from src.config.browser import browser_settings
from src.config.lcw import lcw_settings

logger = logging.getLogger(__name__)


def generate_user_data() -> tuple[str, str]:
    """Generate a random email and password for the new account."""
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    email = f"user_{int(time.time())}_{suffix}@gmail.com"
    password = f"Pass{suffix.capitalize()}9#!"
    return email, password


class LCWRegistrationAutomation:
    """Automates user registration flow on LC Waikiki website."""

    def __init__(
        self,
        domain: str | None = None,
        register_url: str | None = None,
    ) -> None:
        self.domain = (domain or lcw_settings.domain).strip()
        self.register_url = (register_url or lcw_settings.register_url).strip()

        self._browser_manager = BrowserManager()
        self._ddddocr_solver = DdddocrSolver()
        self.page: Page | None = None

    def start(self) -> None:
        """Launch browser and set up the active page."""
        self.page = self._browser_manager.start()

    def close(self) -> None:
        """Release browser resources."""
        self._browser_manager.close()
        self.page = None

    def _accept_cookies(self) -> None:
        """Dismiss the cookie consent banner if present."""
        if not self.page:
            return

        selectors = [
            "button:has-text('Anladım')",
            "button:has-text('Accept')",
            "button:has-text('I agree')",
            "button:has-text('Принять')",
            ".cookie-policy__button",
            "#cookieseal-banner-accept",
        ]
        for sel in selectors:
            try:
                btn = self.page.locator(sel)
                if btn.count() > 0 and btn.is_visible():
                    logger.info("Dismissing cookie banner: %r", sel)
                    btn.click()
                    self.page.wait_for_timeout(400)
                    break
            except Exception:
                pass

    def _solve_captcha(self) -> str | None:
        """Extract captcha image from page and resolve via Ollama or ddddocr."""
        if not self.page:
            return None

        try:
            captcha_field = self.page.locator(".register__captchaField")
            if captcha_field.count() == 0:
                return None

            img_locator = captcha_field.locator("..").locator("img")
            if img_locator.count() == 0:
                return None

            src = img_locator.get_attribute("src") or ""
            if "base64," not in src:
                return None

            raw_bytes = base64.b64decode(src.split("base64,")[1])

            code = solve_via_ollama(raw_bytes)
            if code and len(code) == 6:
                return code

            code = self._ddddocr_solver.solve(raw_bytes)
            logger.info("ddddocr result (length %d): %r", len(code or ""), code)
            return code

        except Exception as exc:
            logger.error("Error during captcha solving: %s", exc)
            return None

    def _refresh_captcha(self) -> None:
        """Click the captcha refresh button and wait for a new image to load."""
        if not self.page:
            return

        try:
            old_src = ""
            captcha_field = self.page.locator(".register__captchaField")
            if captcha_field.count() > 0:
                img = captcha_field.locator("..").locator("img").first
                old_src = img.get_attribute("src") or ""

            refresh_btn = self.page.locator(
                ".register__captchaBtn, button.register__captchaBtn"
            )
            if refresh_btn.count() > 0:
                logger.info("Requesting a new captcha image...")
                refresh_btn.first.click()
                for _ in range(20):
                    self.page.wait_for_timeout(150)
                    img = captcha_field.locator("..").locator("img").first
                    new_src = img.get_attribute("src") or ""
                    if new_src and new_src != old_src:
                        logger.info("New captcha image loaded.")
                        break
            else:
                self.page.wait_for_timeout(1000)
        except Exception as exc:
            logger.debug("Captcha refresh error: %s", exc)
            self.page.wait_for_timeout(1000)

    def register_and_trigger_sms(self, phone_number: str) -> bool:
        """Fill registration form, resolve captcha, and submit to trigger SMS code."""
        if not self.page:
            self.start()

        logger.info("Navigating to registration page: %s", self.register_url)
        self.page.goto(self.register_url, wait_until="domcontentloaded")
        self.page.wait_for_timeout(2000)

        self._accept_cookies()

        email, password = generate_user_data()
        logger.info("Generated credentials: email=%s", email)

        email_input = self.page.locator("input[name='email'], #form-input-email").first
        email_input.wait_for(state="visible", timeout=15_000)
        email_input.fill(email)

        password_input = self.page.locator(
            "input[name='password'], #form-input-password"
        ).first
        password_input.fill(password)

        clean = phone_number.lstrip("+").strip()
        local_phone = clean[3:] if clean.startswith("964") else clean
        logger.info("Entering phone: %r (raw: %r)", local_phone, phone_number)
        phone_input = self.page.locator(
            ".phone-field__number-input, input[placeholder*='Phone']"
        ).first
        phone_input.fill(local_phone)

        # SMS consent checkbox
        sms_checkbox = self.page.locator(
            "label:has(span.checkbox__label:has-text('SMS')),"
            " .form-checkbox:has-text('SMS') label"
        )
        if sms_checkbox.count() > 0:
            sms_btn = self.page.locator(
                ".form-checkbox:has-text('SMS') button.checkbox__button"
            )
            if sms_btn.count() == 0 or sms_btn.get_attribute("data-state") == "unchecked":
                logger.info("Checking SMS consent checkbox...")
                sms_checkbox.first.click()
                self.page.wait_for_timeout(300)

        # Privacy Policy checkbox (mandatory)
        privacy_checkbox = self.page.locator(".privacy-checkbox label, .privacy-checkbox")
        if privacy_checkbox.count() > 0:
            privacy_btn = self.page.locator(".privacy-checkbox button.checkbox__button")
            if (
                privacy_btn.count() == 0
                or privacy_btn.get_attribute("data-state") == "unchecked"
            ):
                logger.info("Checking Privacy Policy checkbox...")
                privacy_checkbox.first.click()
                self.page.wait_for_timeout(300)

        submit_btn = self.page.locator(
            "button[data-testid='register-submit-button'],"
            " button:has-text('Sign Up'),"
            " button[type='submit']"
        ).first

        for attempt in range(1, browser_settings.max_captcha_retries + 1):
            logger.info(
                "Captcha attempt %d/%d", attempt, browser_settings.max_captcha_retries
            )

            captcha_code = self._solve_captcha()
            if not captcha_code:
                logger.warning("Captcha not resolved — refreshing image...")
                self._refresh_captcha()
                continue

            captcha_input = self.page.locator("input[name='captchaCode']")
            if captcha_input.count() > 0:
                captcha_input.fill("")
                captcha_input.fill(captcha_code)
                self.page.wait_for_timeout(200)

            prereg_response = None
            try:
                with self.page.expect_response(
                    "**/ajax/authentication/preregister**", timeout=12_000
                ) as response_info:
                    submit_btn.click()
                prereg_response = response_info.value
            except Exception as exc:
                logger.warning("Preregister response not captured: %s", exc)

            self.page.wait_for_timeout(1000)

            is_success = False
            has_error = False
            error_reason = ""

            if prereg_response and prereg_response.status == 200:
                try:
                    data = prereg_response.json()
                    errors = (
                        data.get("MessageViewModel", {}).get("ErrorMessageList", [])
                        or data.get("ErrorMessageList", [])
                    )
                    if data.get("OperationStatus") is True or (
                        not errors and data.get("Success", False)
                    ):
                        is_success = True
                    else:
                        has_error = True
                        error_reason = "; ".join(errors) if errors else str(data)
                except Exception as exc:
                    logger.debug("Could not parse preregister JSON: %s", exc)

            dom_error = self.page.locator(
                ".form-error-message, div[class*='form-error-message'], .error-message"
            )
            if dom_error.count() > 0:
                for el in dom_error.all():
                    try:
                        if el.is_visible():
                            text = el.inner_text().strip()
                            if text:
                                has_error = True
                                error_reason = text
                                break
                    except Exception:
                        pass

            otp_input = self.page.locator(
                "input[name*='code'], input[name*='otp'],"
                " input[placeholder*='code'], input[placeholder*='Code'],"
                " input[placeholder*='SMS'], .otp-input"
            )
            if otp_input.count() > 0 and otp_input.first.is_visible():
                is_success = True

            if is_success and not has_error:
                logger.info("Form accepted — SMS dispatched.")
                self.page.wait_for_timeout(2000)
                return True

            logger.warning(
                "Form rejected (attempt %d/%d): %r (captcha: %r)",
                attempt,
                browser_settings.max_captcha_retries,
                error_reason or "Invalid form!",
                captcha_code,
            )

            if attempt < browser_settings.max_captcha_retries:
                if captcha_input.count() > 0:
                    captcha_input.fill("")
                self._refresh_captcha()
                self.page.wait_for_timeout(500)

        logger.error(
            "All %d captcha attempts exhausted. Form was not accepted.",
            browser_settings.max_captcha_retries,
        )
        return False

    def enter_sms_code(self, sms_code: str) -> bool:
        """Enter SMS verification code into the OTP input field and confirm."""
        if not self.page:
            logger.error("No active page.")
            return False

        logger.info("Entering SMS code %r...", sms_code)
        otp_selectors = [
            "input[name*='code']",
            "input[name*='otp']",
            "input[placeholder*='Code']",
            "input[placeholder*='code']",
            ".otp-input",
            "input[type='number']",
            "input[type='tel']",
        ]
        try:
            for sel in otp_selectors:
                field = self.page.locator(sel)
                if field.count() > 0 and field.first.is_visible():
                    field.first.fill(sms_code)
                    self.page.wait_for_timeout(500)
                    logger.info("Code entered via selector %r.", sel)

                    verify_btn = self.page.locator(
                        "button:has-text('Verify'), button:has-text('Confirm'),"
                        " button:has-text('Submit'), button[type='submit']"
                    )
                    if verify_btn.count() > 0 and verify_btn.first.is_visible():
                        verify_btn.first.click()
                        self.page.wait_for_timeout(2000)
                        logger.info("Verification button clicked.")
                    return True

            logger.warning("OTP input field not found via any known selector.")
            return False
        except Exception as exc:
            logger.error("Error entering SMS code: %s", exc)
            return False
