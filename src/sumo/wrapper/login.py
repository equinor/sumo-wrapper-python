import os
import sys
from argparse import ArgumentParser
from sumo.wrapper import CallSumoApi


def get_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Login to Sumo on azure")
    parser.add_argument(
        "--env",
        dest="env",
        action="store",
        default="prod",
        help="Environment to log into",
    )
    return parser


def main():
    args = get_parser().parse_args()

    env = args.env

    print("Login to Sumo environment: " + env)

    CallSumoApi(env=env, writeback=True)


if __name__ == "__main__":
    main()
