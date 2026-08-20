import unittest

from pywin_update_alternatives import detect_java_installations
from pywin_update_alternatives.java_detection import _msys_to_windows


class DetectJavaInstallationsTests(unittest.TestCase):
    def test_detects_jdk_and_jre_entries_from_windows_path(self) -> None:
        path_value = (
            r"C:\Program Files\Java\jdk-21\bin;"
            r"C:\Program Files\Java\jre1.8.0_351\bin;"
            r"C:\tools\python"
        )

        detected = detect_java_installations(path_value)

        self.assertEqual(detected.jdk, (r"C:\Program Files\Java\jdk-21\bin",))
        self.assertEqual(
            detected.jre,
            (
                r"C:\Program Files\Java\jre1.8.0_351\bin",
            ),
        )

    def test_keeps_non_jdk_java_entries_in_jre_bucket(self) -> None:
        path_value = r"C:\Program Files\Java\bin;C:\Program Files\Java\jdk-17\bin"

        detected = detect_java_installations(path_value)

        self.assertEqual(detected.jdk, (r"C:\Program Files\Java\jdk-17\bin",))
        self.assertEqual(
            detected.jre,
            (r"C:\Program Files\Java\bin",),
        )

    def test_deduplicates_entries_case_insensitively(self) -> None:
        path_value = r"C:\JAVA\JDK-21\bin;c:\java\jdk-21\bin"

        detected = detect_java_installations(path_value)

        self.assertEqual(detected.jdk, (r"C:\JAVA\JDK-21\bin",))

    # ------------------------------------------------------------------
    # Git Bash / MSYS2 compatibility
    # ------------------------------------------------------------------

    def test_detects_jdk_from_msys_colon_separated_path(self) -> None:
        """Git Bash exposes PATH with ':' separator and POSIX-style drive letters."""
        path_value = (
            "/c/Program Files/Java/jdk-21/bin"
            ":/c/Program Files/Java/jre1.8.0_351/bin"
            ":/c/tools/python"
        )

        detected = detect_java_installations(path_value)

        self.assertEqual(detected.jdk, (r"C:\Program Files\Java\jdk-21\bin",))
        self.assertEqual(detected.jre, (r"C:\Program Files\Java\jre1.8.0_351\bin",))

    def test_deduplicates_msys_and_windows_paths(self) -> None:
        """An MSYS path and its Windows equivalent should deduplicate."""
        path_value = r"C:\Java\jdk-21\bin;/c/Java/jdk-21/bin"

        detected = detect_java_installations(path_value)

        self.assertEqual(len(detected.jdk), 1)

    def test_msys_path_without_subdirectory(self) -> None:
        """MSYS paths with only a drive letter (e.g. /c) convert cleanly."""
        self.assertEqual(_msys_to_windows("/c"), "C:")

    def test_msys_to_windows_converts_drive_and_path(self) -> None:
        self.assertEqual(
            _msys_to_windows("/c/Program Files/Java/jdk-21/bin"),
            r"C:\Program Files\Java\jdk-21\bin",
        )

    def test_msys_to_windows_leaves_windows_paths_unchanged(self) -> None:
        self.assertEqual(
            _msys_to_windows(r"C:\Program Files\Java\jdk-21\bin"),
            r"C:\Program Files\Java\jdk-21\bin",
        )

    def test_msys_to_windows_leaves_relative_posix_paths_unchanged(self) -> None:
        """Paths like /usr/bin should not be mangled (no single-letter component)."""
        self.assertEqual(_msys_to_windows("/usr/bin"), "/usr/bin")


if __name__ == "__main__":
    unittest.main()
