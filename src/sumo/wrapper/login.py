import logging

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
        default=False,
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

    return parser


def main():
    args = get_parser().parse_args()
    logger.setLevel(level=args.verbosity)
    env = args.env
    logger.debug("env is %s", env)

    print("Login to Sumo environment: " + env)

    sumo = SumoClient(
        args.env, interactive=args.interactive, devicecode=args.devicecode
    )
    token = sumo.authenticate()

    if args.print_token:
        print(f"TOKEN: {token}")


if __name__ == "__main__":
    main()
