import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


class LauncherSmokeTests(unittest.TestCase):
    def launcher_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["PYWIN_UPDATE_ALTERNATIVES_PYTHON"] = sys.executable
        return env

    def run_launcher(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            cwd=REPO_ROOT,
            env=self.launcher_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def test_git_bash_launcher_supports_help_and_detect_java(self) -> None:
        result = self.run_launcher(["bash", str(REPO_ROOT / "pywin-update-alternatives.sh"), "--help"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Usage: pywin-update-alternatives", result.stdout)

        result = self.run_launcher(
            ["bash", str(REPO_ROOT / "pywin-update-alternatives.sh"), "detect-java", "--format", "json"]
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("jdk", payload)
        self.assertIn("jre", payload)

    @unittest.skipUnless(sys.platform == "win32", "PowerShell launcher test requires Windows")
    def test_powershell_launcher_supports_help_and_detect_java(self) -> None:
        powershell = shutil.which("powershell") or shutil.which("pwsh")
        if powershell is None:
            self.skipTest("PowerShell is not available")

        result = self.run_launcher(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(REPO_ROOT / "scripts" / "pywin-update-alternatives.ps1"),
                "--help",
            ]
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Usage: pywin-update-alternatives", result.stdout)

        result = self.run_launcher(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(REPO_ROOT / "scripts" / "pywin-update-alternatives.ps1"),
                "detect-java",
                "--format",
                "json",
            ]
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("jdk", payload)
        self.assertIn("jre", payload)

    @unittest.skipUnless(sys.platform == "win32", "CMD launcher test requires Windows")
    def test_cmd_launcher_supports_help_and_detect_java(self) -> None:
        cmd = shutil.which("cmd.exe")
        if cmd is None:
            self.skipTest("cmd.exe is not available")

        result = self.run_launcher([cmd, "/c", str(REPO_ROOT / "pywin-update-alternatives.cmd"), "--help"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Usage: pywin-update-alternatives", result.stdout)

        result = self.run_launcher(
            [
                cmd,
                "/c",
                str(REPO_ROOT / "pywin-update-alternatives.cmd"),
                "detect-java",
                "--format",
                "json",
            ]
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("jdk", payload)
        self.assertIn("jre", payload)


if __name__ == "__main__":
    unittest.main()
