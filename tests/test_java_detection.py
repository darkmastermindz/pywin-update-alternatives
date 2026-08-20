import unittest

from pywin_update_alternatives import detect_java_installations


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


if __name__ == "__main__":
    unittest.main()
