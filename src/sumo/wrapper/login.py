import logging
import platform
from pathlib import Path
from argparse import ArgumentParser
from sumo.wrapper import SumoClient


logger = logging.getLogger("sumo.wrapper")
logger.setLevel(level="CRITICAL")


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
        "-i",
        "--interactive",
        dest="interactive",
        action="store_true",
        default=True,
        help="Login interactively",
    )

    parser.add_argument(
        "-d",
        "--devicecode",
        dest="devicecode",
        action="store_true",
        default=False,
        help="Login with device-code",
    )

    parser.add_argument(
        "-p",
        "--print",
        dest="print_token",
        action="store_true",
        default=False,
        help="Print access token",
    )

    parser.add_argument(
        "-s",
        "--silent",
        dest="silent",
        action="store_true",
        default=False,
        help="Attempt acquire token silently",
    )

    return parser


def main():
    args = get_parser().parse_args()
    logger.setLevel(level=args.verbosity)
    env = args.env
    logger.debug("env is %s", env)

    if args.silent:
        args.interactive = False
        args.devicecode = False
        args.print_token = False
    else:
        print("Login to Sumo environment: " + env)

    if args.interactive:
        lockfile_path = Path.home() / ".config/chromium/SingletonLock"
        if Path(lockfile_path).is_symlink() and not str(
            Path(lockfile_path).resolve()
        ).__contains__(platform.node()):
            # https://github.com/equinor/sumo-wrapper-python/issues/193
            args.interactive = False
            args.devicecode = True

    sumo = SumoClient(
        args.env, interactive=args.interactive, devicecode=args.devicecode
    )
    token = sumo.authenticate()

    if args.silent:
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
