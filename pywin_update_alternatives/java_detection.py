from __future__ import annotations

from dataclasses import dataclass
import os
import re
from typing import Iterable


JAVA_PATTERN = re.compile(r"(java|jdk|jre)", re.IGNORECASE)
JDK_PATTERN = re.compile(r"jdk", re.IGNORECASE)
JRE_PATTERN = re.compile(r"jre", re.IGNORECASE)

# Matches MSYS/Git Bash POSIX-style Windows paths such as /c/Program Files/...
# Group 1 is the drive letter; Group 2 is the rest of the path.
_MSYS_PATH_RE = re.compile(r"^/([a-zA-Z])(/.*)?$")


@dataclass(frozen=True)
class JavaInstallations:
    jdk: tuple[str, ...]
    jre: tuple[str, ...]

    def to_dict(self) -> dict[str, list[str]]:
        return {
            "jdk": list(self.jdk),
            "jre": list(self.jre),
        }


def _msys_to_windows(path: str) -> str:
    """Convert an MSYS/Git Bash POSIX path to a Windows path.

    ``/c/Program Files/Java/jdk-21/bin`` → ``C:\\Program Files\\Java\\jdk-21\\bin``

    Paths that are already Windows-style are returned unchanged.
    """
    m = _MSYS_PATH_RE.match(path)
    if not m:
        return path
    drive = m.group(1).upper()
    rest = (m.group(2) or "").replace("/", "\\")
    return f"{drive}:{rest}"


def _split_path_entries(path_value: str | None) -> tuple[str, ...]:
    if not path_value:
        return ()

    # Prefer semicolon splitting (Windows-native), but fall back to colon
    # when running inside Git Bash / MSYS2 where PATH uses ":" as separator.
    separator = ";" if ";" in path_value else os.pathsep
    entries = (entry.strip() for entry in path_value.split(separator) if entry.strip())
    return tuple(_msys_to_windows(entry) for entry in entries)


def _unique(entries: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []

    for entry in entries:
        normalized = os.path.normpath(entry).replace("\\", "/").lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(entry)

    return tuple(ordered)


def detect_java_installations(path_value: str | None = None) -> JavaInstallations:
    entries = _split_path_entries(path_value if path_value is not None else os.environ.get("PATH"))
    java_entries = tuple(entry for entry in entries if JAVA_PATTERN.search(entry))

    jdk_entries = _unique(entry for entry in java_entries if JDK_PATTERN.search(entry))
    jre_entries = _unique(
        entry
        for entry in java_entries
        if JRE_PATTERN.search(entry) or not JDK_PATTERN.search(entry)
    )

    return JavaInstallations(jdk=jdk_entries, jre=jre_entries)
