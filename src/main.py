"""Main entry point — orchestrates the LC Waikiki registration workflow."""

import logging
import sys

from src.config.lcw import lcw_settings
from src.config.ollama import ollama_settings
from src.config.simroute import simroute_settings
from src.external_apis.ollama import OllamaApiClient
from src.external_apis.simroute import (
    SimrouteApiClient,
    SimrouteBalanceError,
    SimrouteNoNumbersError,
    SimrouteTimeoutError,
)
from src.automation import LCWRegistrationAutomation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("MainWorkflow")


def run() -> None:
    logger.info("=" * 70)
    logger.info("LC Waikiki automated registration started")
    logger.info("Registration URL : %s", lcw_settings.register_url)
    logger.info("Domain           : %s", lcw_settings.domain)
    logger.info("Country (Simroute): %s (Iraq)", simroute_settings.country_id)
    logger.info("Service (Simroute): %s (LC Waikiki)", simroute_settings.service_code)
    logger.info("=" * 70)

    # Check Ollama service status if enabled
    if ollama_settings.enabled:
        try:
            ollama = OllamaApiClient()
            if ollama.is_online():
                models = [m.name for m in ollama.get_running_models()]
                logger.info("Ollama service online. Models in VRAM: %s (target: %r)", models, ollama_settings.model)
            else:
                logger.warning("Ollama service is unreachable. Will fallback to ddddocr solver.")
        except Exception as exc:
            logger.debug("Ollama status check skipped: %s", exc)

    simroute = SimrouteApiClient()
    automation = LCWRegistrationAutomation()
    activation = None

    try:
        # 1. Balance check
        try:
            balance = simroute.get_balance()
            logger.info("Simroute balance: %.2f", balance)
            if balance <= 0:
                raise SimrouteBalanceError("Simroute balance is zero or negative!")
        except SimrouteBalanceError:
            raise
        except Exception as exc:
            logger.warning("Could not retrieve balance: %s", exc)

        # 2. Acquire a phone number
        logger.info("Step 1: Requesting phone number from Simroute...")
        activation = simroute.get_phone_number()
        logger.info(
            "Number received: %s (activation_id=%s)",
            activation.phone,
            activation.activation_id,
        )

        # 3. Signal that the number is ready to receive SMS
        simroute.set_status(activation.activation_id, SimrouteApiClient.STATUS_PHONE_READY)

        # 4. Fill and submit the registration form
        logger.info("Step 2: Running browser registration on LC Waikiki...")
        automation.start()
        if not automation.register_and_trigger_sms(activation.phone):
            raise RuntimeError("Registration form submission failed on LC Waikiki")

        logger.info("Form submitted — SMS requested.")

        # 5. Wait for the SMS code
        logger.info("Step 3: Waiting for SMS from LC Waikiki...")
        sms_code = simroute.wait_for_sms(activation.activation_id)
        logger.info("SMS code received: >>> %s <<<", sms_code)

        # 6. Enter the code in the browser
        logger.info("Step 4: Entering SMS code into the verification form...")
        if automation.enter_sms_code(sms_code):
            logger.info("SMS code entered successfully.")

        # 7. Mark activation as complete
        simroute.set_status(activation.activation_id, SimrouteApiClient.STATUS_FINISH)
        logger.info("Activation marked as FINISH.")

    except SimrouteTimeoutError as exc:
        logger.error("SMS wait timed out: %s", exc)
        if activation:
            simroute.set_status(activation.activation_id, SimrouteApiClient.STATUS_CANCEL)
        sys.exit(1)

    except SimrouteNoNumbersError as exc:
        logger.error("No phone numbers available: %s", exc)
        sys.exit(1)

    except Exception as exc:
        logger.exception("Unexpected error during registration: %s", exc)
        if activation:
            simroute.set_status(activation.activation_id, SimrouteApiClient.STATUS_CANCEL)
        sys.exit(1)

    finally:
        automation.close()
        simroute.close()
        logger.info("Workflow finished.")


if __name__ == "__main__":
    run()
