import os
import sys
import logging

from argparse import ArgumentParser
from sumo.wrapper import CallSumoApi

logger = logging.getLogger("sumo.wrapper")
logger.setLevel(level="CRITICAL")


def get_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Login to Sumo on azure")
    parser.add_argument(
        "--env",
        dest="env",
        action="store",
        default="prod",
        help="Environment to log into",
    )
    parser.add_argument(
        "--verbosity",
        dest="verbosity",
        default="CRITICAL",
        help="Set the verbosity level",
    )
    return parser


def main():
    args = get_parser().parse_args()
    logger.setLevel(level=args.verbosity)
    env = args.env
    logger.debug("env is %s", env)

    print("Login to Sumo environment: " + env)

    CallSumoApi(env=env, writeback=True, verbosity=args.verbosity)


if __name__ == "__main__":
    main()
