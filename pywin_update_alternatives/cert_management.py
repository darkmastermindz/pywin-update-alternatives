from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .java_detection import detect_java_installations

# Default password for the Java cacerts truststore.
_DEFAULT_STOREPASS = "changeit"


@dataclass(frozen=True)
class CertImportResult:
    java_home: str
    cacerts_path: str
    success: bool
    message: str


def _find_cacerts(java_bin_path: str) -> str | None:
    """Return the path to the cacerts truststore for a given Java bin directory.

    Looks in ``<java_home>/lib/security/cacerts`` (Java 9+) and
    ``<java_home>/jre/lib/security/cacerts`` (Java 8 JDK layout).
    """
    java_home = Path(java_bin_path).parent
    candidates = [
        java_home / "lib" / "security" / "cacerts",
        java_home / "jre" / "lib" / "security" / "cacerts",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def _find_keytool(java_bin_path: str) -> str | None:
    """Return the path to the ``keytool`` executable inside *java_bin_path*."""
    for name in ("keytool.exe", "keytool"):
        keytool = Path(java_bin_path) / name
        if keytool.exists():
            return str(keytool)
    return None


def _import_cert(
    keytool: str,
    cacerts: str,
    cert_path: str,
    alias: str,
    storepass: str,
) -> tuple[bool, str]:
    """Run ``keytool -importcert`` and return ``(success, message)``."""
    cmd: list[str] = [
        keytool,
        "-importcert",
        "-noprompt",
        "-trustcacerts",
        "-alias", alias,
        "-file", cert_path,
        "-keystore", cacerts,
        "-storepass", storepass,
    ]
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if result.returncode == 0:
            return True, result.stdout.strip() or "Certificate imported successfully."
        return False, result.stdout.strip() or f"keytool exited with code {result.returncode}."
    except FileNotFoundError:
        return False, f"keytool not found at: {keytool}"
    except OSError as exc:
        return False, str(exc)


def add_cert_to_java(
    cert_path: str,
    alias: str,
    path_value: str | None = None,
    storepass: str = _DEFAULT_STOREPASS,
    java_bin_paths: Sequence[str] | None = None,
) -> list[CertImportResult]:
    """Import a certificate into the cacerts truststore of all detected Java installs.

    Parameters
    ----------
    cert_path:
        Absolute path to the ``.cer`` / ``.pem`` / ``.crt`` certificate file.
    alias:
        Alias under which the certificate is stored in the truststore.
    path_value:
        Optional PATH string to pass to :func:`detect_java_installations`.
        Defaults to the current process ``PATH``.
    storepass:
        Truststore password.  Defaults to the standard Java default ``changeit``.
    java_bin_paths:
        If supplied, use these bin-directory paths instead of auto-detecting via
        ``path_value``.  Useful for testing or when the caller already knows the
        Java installations.
    """
    if java_bin_paths is None:
        detected = detect_java_installations(path_value if path_value is not None else os.environ.get("PATH"))
        all_bin_paths = list(detected.jdk) + list(detected.jre)
    else:
        all_bin_paths = list(java_bin_paths)

    results: list[CertImportResult] = []

    seen_cacerts: set[str] = set()

    for bin_path in all_bin_paths:
        java_home = str(Path(bin_path).parent)
        cacerts = _find_cacerts(bin_path)
        if cacerts is None:
            results.append(
                CertImportResult(
                    java_home=java_home,
                    cacerts_path="",
                    success=False,
                    message="cacerts truststore not found.",
                )
            )
            continue

        # Avoid importing the same truststore twice when JDK & JRE share one.
        norm_cacerts = os.path.normcase(os.path.normpath(cacerts))
        if norm_cacerts in seen_cacerts:
            results.append(
                CertImportResult(
                    java_home=java_home,
                    cacerts_path=cacerts,
                    success=True,
                    message="Skipped: this truststore was already imported via another Java installation.",
                )
            )
            continue
        seen_cacerts.add(norm_cacerts)

        keytool = _find_keytool(bin_path)
        if keytool is None:
            results.append(
                CertImportResult(
                    java_home=java_home,
                    cacerts_path=cacerts,
                    success=False,
                    message="keytool executable not found.",
                )
            )
            continue

        success, message = _import_cert(keytool, cacerts, cert_path, alias, storepass)
        results.append(
            CertImportResult(
                java_home=java_home,
                cacerts_path=cacerts,
                success=success,
                message=message,
            )
        )

    return results
