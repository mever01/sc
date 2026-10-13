"""Command-line interface (CLI) for LC Waikiki registration automation."""

import argparse
import logging
import sys

from src.config.browser import browser_settings
from src.config.lcw import lcw_settings
from src.config.ollama import ollama_settings
from src.config.simroute import simroute_settings
from src.external_apis.ollama import OllamaApiClient
from src.external_apis.simroute import SimrouteApiClient, SimrouteError

logger = logging.getLogger("sc.cli")


def _cmd_balance(args: argparse.Namespace) -> int:
    """Print current Simroute account balance."""
    client = SimrouteApiClient()
    try:
        balance = client.get_balance()
        print(f"Simroute Balance: {balance:.2f}")
        return 0
    except SimrouteError as exc:
        print(f"Error fetching balance: {exc}", file=sys.stderr)
        return 1
    finally:
        client.close()


def _cmd_check(args: argparse.Namespace) -> int:
    """Check connectivity to external services (Simroute and Ollama)."""
    print("=" * 60)
    print("Diagnostics & External Services Health Check")
    print("=" * 60)

    # 1. Simroute check
    print("\n[Simroute SMS API]")
    print(f"  Base URL    : {simroute_settings.base_url}")
    print(f"  Country ID  : {simroute_settings.country_id} (Iraq)")
    print(f"  Service     : {simroute_settings.service_code} (LC Waikiki)")
    simroute_client = SimrouteApiClient()
    try:
        balance = simroute_client.get_balance()
        print(f"  Status      : OK")
        print(f"  Balance     : {balance:.2f}")
    except Exception as exc:
        print(f"  Status      : FAILED ({exc})")
    finally:
        simroute_client.close()

    # 2. Ollama check
    print("\n[Ollama Vision AI]")
    print(f"  Enabled     : {ollama_settings.enabled}")
    print(f"  Base URL    : {ollama_settings.resolved_base_url}")
    print(f"  Model       : {ollama_settings.model}")
    if ollama_settings.enabled:
        ollama_client = OllamaApiClient()
        try:
            if ollama_client.is_online():
                models = ollama_client.get_running_models()
                model_names = [m.name for m in models] if models else ["(none currently in VRAM)"]
                print("  Status      : OK (service reachable)")
                print(f"  Loaded VRAM : {', '.join(model_names)}")
            else:
                print("  Status      : UNREACHABLE (will fallback to ddddocr)")
        except Exception as exc:
            print(f"  Status      : FAILED ({exc})")
        finally:
            ollama_client.close()
    else:
        print("  Status      : DISABLED by config")

    # 3. LC Waikiki target
    print("\n[LC Waikiki Target]")
    print(f"  Domain      : {lcw_settings.domain}")
    print(f"  Register URL: {lcw_settings.register_url}")

    print("\n" + "=" * 60)
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    """Execute the registration automation scenario."""
    # Apply CLI overrides to settings
    if args.headless is not None:
        browser_settings.headless = args.headless
    if args.no_ollama:
        ollama_settings.enabled = False
    if args.domain:
        lcw_settings.domain = args.domain

    from src.main import run

    try:
        run()
        return 0
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1
    except Exception as exc:
        logger.exception("Automation failed: %s", exc)
        return 1


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line arguments parser."""
    parser = argparse.ArgumentParser(
        prog="lcw",
        description="LC Waikiki Registration Automation CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # sc run
    run_parser = subparsers.add_parser("run", help="Run LC Waikiki registration automation")
    headless_group = run_parser.add_mutually_exclusive_group()
    headless_group.add_argument(
        "--headless",
        dest="headless",
        action="store_true",
        default=None,
        help="Run browser in headless mode (no GUI window)",
    )
    headless_group.add_argument(
        "--no-headless",
        dest="headless",
        action="store_false",
        help="Run browser with visible GUI window",
    )
    run_parser.add_argument(
        "--no-ollama",
        action="store_true",
        help="Disable Ollama solver (use ddddocr only)",
    )
    run_parser.add_argument(
        "--domain",
        type=str,
        default=None,
        help="Override target LC Waikiki domain (e.g. www.lcwaikiki.iq)",
    )
    run_parser.set_defaults(func=_cmd_run)

    # sc check
    check_parser = subparsers.add_parser(
        "check",
        help="Perform connectivity and health checks for Simroute and Ollama",
    )
    check_parser.set_defaults(func=_cmd_check)

    # sc balance
    balance_parser = subparsers.add_parser(
        "balance",
        help="Display current Simroute account balance",
    )
    balance_parser.set_defaults(func=_cmd_balance)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        # If run without arguments, display help
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
