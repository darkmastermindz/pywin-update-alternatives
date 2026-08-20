from __future__ import annotations

import argparse
import json
import sys

from .cert_management import add_cert_to_java
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

    add_cert_parser = subparsers.add_parser(
        "add-java-cert",
        help="Import a certificate into the cacerts truststore of all detected JDK/JRE installations.",
    )
    add_cert_parser.add_argument(
        "cert",
        metavar="CERT_FILE",
        help="Path to the certificate file (.cer / .pem / .crt) to import.",
    )
    add_cert_parser.add_argument(
        "--alias",
        required=True,
        help="Alias under which the certificate is stored in the truststore.",
    )
    add_cert_parser.add_argument(
        "--path",
        dest="path_value",
        help="Optional PATH value to inspect for Java installations. Defaults to the current process PATH.",
    )
    add_cert_parser.add_argument(
        "--storepass",
        default="changeit",
        help="Truststore password (default: changeit).",
    )
    add_cert_parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="text",
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

    if args.command == "add-java-cert":
        results = add_cert_to_java(
            cert_path=args.cert,
            alias=args.alias,
            path_value=args.path_value,
            storepass=args.storepass,
        )
        if not results:
            print("No Java installations found.", file=sys.stderr)
            return 1

        all_ok = all(r.success for r in results)

        if args.format == "json":
            output = [
                {
                    "java_home": r.java_home,
                    "cacerts_path": r.cacerts_path,
                    "success": r.success,
                    "message": r.message,
                }
                for r in results
            ]
            print(json.dumps(output, indent=2))
        else:
            for r in results:
                status = "OK" if r.success else "FAILED"
                print(f"[{status}] {r.java_home}")
                if r.cacerts_path:
                    print(f"       cacerts : {r.cacerts_path}")
                print(f"       message : {r.message}")

        return 0 if all_ok else 1

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
