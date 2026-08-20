import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pywin_update_alternatives.__main__ import main
from pywin_update_alternatives.debian_alternatives import _root_join

class DebianAlternativesCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.base = Path(self.tempdir.name)
        self.altdir = self.base / "altdir"
        self.admindir = self.base / "admindir"
        self.instdir = self.base / "instdir"
        self.log_file = self.base / "alternatives.log"

    def invoke(self, *args: str, stdin_text: str = "") -> tuple[int, str, str]:
        stdin = io.StringIO(stdin_text)
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch("sys.stdin", stdin), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
            rc = main(list(args))
        return rc, stdout.getvalue(), stderr.getvalue()

    def command_prefix(self) -> list[str]:
        return [
            "--altdir",
            str(self.altdir),
            "--admindir",
            str(self.admindir),
            "--instdir",
            str(self.instdir),
            "--log",
            str(self.log_file),
        ]

    def make_file(self, relative_path: str) -> str:
        path = self.base / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(relative_path, encoding="utf-8")
        return str(path)

    def test_install_query_list_and_force(self) -> None:
        alt1 = self.make_file("targets/editor-one")
        alt2 = self.make_file("targets/editor-two")
        slave1 = self.make_file("targets/editor-one.1")
        slave2 = self.make_file("targets/editor-two.1")
        master_link = self.instdir / "usr" / "bin" / "editor"
        master_link.parent.mkdir(parents=True, exist_ok=True)
        master_link.write_text("occupied", encoding="utf-8")

        rc, _stdout, stderr = self.invoke(
            *self.command_prefix(),
            "--install",
            "/usr/bin/editor",
            "editor",
            alt1,
            "10",
            "--slave",
            "/usr/share/man/man1/editor.1.gz",
            "editor.1.gz",
            slave1,
        )
        self.assertEqual(rc, 2)
        self.assertIn("--force", stderr)

        rc, _stdout, stderr = self.invoke(
            *self.command_prefix(),
            "--force",
            "--install",
            "/usr/bin/editor",
            "editor",
            alt1,
            "10",
            "--slave",
            "/usr/share/man/man1/editor.1.gz",
            "editor.1.gz",
            slave1,
        )
        self.assertEqual(rc, 0, stderr)

        rc, _stdout, stderr = self.invoke(
            *self.command_prefix(),
            "--verbose",
            "--install",
            "/usr/bin/editor",
            "editor",
            alt2,
            "20",
            "--slave",
            "/usr/share/man/man1/editor.1.gz",
            "editor.1.gz",
            slave2,
        )
        self.assertEqual(rc, 0, stderr)
        self.assertTrue(master_link.is_symlink())
        self.assertEqual(os.readlink(self.altdir / "editor"), alt2)
        self.assertEqual(os.readlink(master_link), str(self.altdir / "editor"))

        rc, stdout, stderr = self.invoke(*self.command_prefix(), "--query", "editor")
        self.assertEqual(rc, 0, stderr)
        self.assertIn("Name: editor", stdout)
        self.assertIn("Status: auto", stdout)
        self.assertIn(f"Best: {alt2}", stdout)
        self.assertIn(f"Alternative: {alt1}", stdout)

        rc, stdout, stderr = self.invoke(*self.command_prefix(), "--list", "editor")
        self.assertEqual(rc, 0, stderr)
        self.assertEqual(stdout.strip().splitlines(), sorted([alt1, alt2]))
        self.assertTrue(self.log_file.exists())

    def test_set_auto_get_set_selections_remove_and_remove_all(self) -> None:
        alt1 = self.make_file("targets/vi-one")
        alt2 = self.make_file("targets/vi-two")

        for path, priority in ((alt1, "5"), (alt2, "10")):
            rc, _stdout, stderr = self.invoke(
                *self.command_prefix(),
                "--install",
                "/usr/bin/vi",
                "vi",
                path,
                priority,
            )
            self.assertEqual(rc, 0, stderr)

        rc, _stdout, stderr = self.invoke(*self.command_prefix(), "--set", "vi", alt1)
        self.assertEqual(rc, 0, stderr)

        rc, stdout, stderr = self.invoke(*self.command_prefix(), "--get-selections")
        self.assertEqual(rc, 0, stderr)
        self.assertIn(f"vi manual {alt1}", stdout)

        rc, _stdout, stderr = self.invoke(
            *self.command_prefix(),
            "--set-selections",
            stdin_text=f"vi auto {alt1}\n",
        )
        self.assertEqual(rc, 0, stderr)

        rc, _stdout, stderr = self.invoke(
            *self.command_prefix(),
            "--set-selections",
            stdin_text="vi auto\n",
        )
        self.assertEqual(rc, 2)
        self.assertIn("Invalid selections line", stderr)

        rc, stdout, stderr = self.invoke(*self.command_prefix(), "--query", "vi")
        self.assertEqual(rc, 0, stderr)
        self.assertIn("Status: auto", stdout)
        self.assertIn(f"Value: {alt2}", stdout)

        rc, _stdout, stderr = self.invoke(*self.command_prefix(), "--remove", "vi", alt2)
        self.assertEqual(rc, 0, stderr)
        rc, stdout, stderr = self.invoke(*self.command_prefix(), "--query", "vi")
        self.assertEqual(rc, 0, stderr)
        self.assertIn(f"Value: {alt1}", stdout)

        master_link = self.instdir / "usr" / "bin" / "vi"
        rc, _stdout, stderr = self.invoke(*self.command_prefix(), "--remove-all", "vi")
        self.assertEqual(rc, 0, stderr)
        self.assertFalse((self.admindir / "vi.json").exists())
        self.assertFalse(master_link.exists())

    def test_config_all_skip_auto_help_and_version(self) -> None:
        alt1 = self.make_file("targets/pager-one")
        alt2 = self.make_file("targets/pager-two")
        cat = self.make_file("targets/cat")

        rc, _stdout, stderr = self.invoke(
            *self.command_prefix(),
            "--install",
            "/usr/bin/pager",
            "pager",
            alt1,
            "10",
        )
        self.assertEqual(rc, 0, stderr)
        rc, _stdout, stderr = self.invoke(
            *self.command_prefix(),
            "--install",
            "/usr/bin/pager",
            "pager",
            alt2,
            "20",
        )
        self.assertEqual(rc, 0, stderr)
        rc, _stdout, stderr = self.invoke(
            *self.command_prefix(),
            "--install",
            "/usr/bin/cat",
            "cat",
            cat,
            "10",
        )
        self.assertEqual(rc, 0, stderr)

        rc, stdout, stderr = self.invoke(*self.command_prefix(), "--config", "pager", stdin_text="2\n")
        self.assertEqual(rc, 0, stderr)
        self.assertIn("choices for the alternative pager", stdout)

        rc, stdout, stderr = self.invoke(*self.command_prefix(), "--get-selections")
        self.assertEqual(rc, 0, stderr)
        self.assertIn(f"pager manual {alt1}", stdout)
        self.assertIn(f"cat auto {cat}", stdout)

        rc, _stdout, stderr = self.invoke(
            *self.command_prefix(),
            "--skip-auto",
            "--all",
            stdin_text="0\n",
        )
        self.assertEqual(rc, 0, stderr)

        rc, stdout, stderr = self.invoke(*self.command_prefix(), "--help")
        self.assertEqual(rc, 0, stderr)
        self.assertIn("Usage: pywin-update-alternatives", stdout)

        rc, stdout, stderr = self.invoke(*self.command_prefix(), "--version")
        self.assertEqual(rc, 0, stderr)
        self.assertIn("pywin-update-alternatives", stdout)

    def test_root_join_preserves_windows_drive_letter(self) -> None:
        rooted = _root_join(Path("/tmp/root"), r"C:\tools\python.exe")
        self.assertEqual(rooted, Path("/tmp/root") / "C" / "tools" / "python.exe")


if __name__ == "__main__":
    unittest.main()
