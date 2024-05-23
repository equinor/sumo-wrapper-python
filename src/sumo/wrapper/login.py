import logging
import platform
from pathlib import Path
from argparse import ArgumentParser
from sumo.wrapper import SumoClient


logger = logging.getLogger("sumo.wrapper")
logger.setLevel(level="CRITICAL")

modes = ["interactive", "devicecode", "silent"]


def get_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Login to Sumo on azure")

    parser.add_argument(
        "-e",
        "--env",
        dest="env",
        action="store",
        default="prod",
        help="Environment to log into",
    )

    parser.add_argument(
        "-v",
        "--verbosity",
        dest="verbosity",
        default="CRITICAL",
        help="Set the verbosity level",
    )

    parser.add_argument(
        "-m",
        "--mode",
        dest="mode",
        action="store",
        default="interactive",
        help=f"Valid modes: {', '.join(modes)}",
    )

    parser.add_argument(
        "-p",
        "--print",
        dest="print_token",
        action="store_true",
        default=False,
        help="Print access token",
    )

    return parser


def main():
    args = get_parser().parse_args()
    logger.setLevel(level=args.verbosity)
    env = args.env
    mode = args.mode

    logger.debug("env is %s", env)

    if mode not in modes:
        print(f"Invalid mode: {mode}")
        return 1

    if mode != "silent":
        print("Login to Sumo environment: " + env)

    if mode == "interactive":
        lockfile_path = Path.home() / ".config/chromium/SingletonLock"
        if Path(lockfile_path).is_symlink() and not str(
            Path(lockfile_path).resolve()
        ).__contains__(platform.node()):
            # https://github.com/equinor/sumo-wrapper-python/issues/193
            args.interactive = False
            args.devicecode = True

    sumo = SumoClient(
        args.env,
        interactive=mode == "interactive",
        devicecode=mode == "devicecode",
    )
    token = sumo.authenticate()

    if mode == "silent":
        if token is None:
            return 1
        return 0
    else:
        if args.print_token:
            print(f"TOKEN: {token}")

        if token is not None:
            print("Successfully logged in to Sumo environment: " + env)
        else:
            print("Failed login to Sumo environment: " + env)


if __name__ == "__main__":
    main()
