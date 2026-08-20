from __future__ import annotations

import argparse
import json

from .java_detection import detect_java_installations


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pywin-update-alternatives",
        description="Windows alternative helpers that can run on an embedded Python runtime.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    detect_java_parser = subparsers.add_parser(
        "detect-java",
        help="Detect JDK/JRE paths from a PATH value.",
    )
    detect_java_parser.add_argument(
        "--path",
        dest="path_value",
        help="Optional PATH value to inspect. Defaults to the current process PATH.",
    )
    detect_java_parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        help="Output format.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "detect-java":
        detected = detect_java_installations(args.path_value)
        if args.format == "json":
            print(json.dumps(detected.to_dict(), indent=2))
        else:
            print("JDK:")
            for entry in detected.jdk:
                print(f"- {entry}")
            print("JRE:")
            for entry in detected.jre:
                print(f"- {entry}")
        return 0

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
