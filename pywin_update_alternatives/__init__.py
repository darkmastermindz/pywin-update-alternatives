"""Utilities for switching Windows development tool alternatives."""

from .cert_management import CertImportResult, add_cert_to_java
from .java_detection import JavaInstallations, detect_java_installations

__all__ = [
    "CertImportResult",
    "JavaInstallations",
    "add_cert_to_java",
    "detect_java_installations",
]
