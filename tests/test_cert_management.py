import os
import subprocess
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from pywin_update_alternatives.cert_management import (
    _find_cacerts,
    _find_keytool,
    _import_cert,
    add_cert_to_java,
)


class FindCacertsTests(unittest.TestCase):
    def test_finds_java9_layout(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            bin_dir = Path(td) / "jdk-21" / "bin"
            cacerts = Path(td) / "jdk-21" / "lib" / "security" / "cacerts"
            cacerts.parent.mkdir(parents=True)
            cacerts.touch()
            bin_dir.mkdir()

            result = _find_cacerts(str(bin_dir))
            self.assertEqual(os.path.normcase(result), os.path.normcase(str(cacerts)))

    def test_finds_java8_jdk_layout(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            bin_dir = Path(td) / "jdk1.8.0" / "bin"
            cacerts = Path(td) / "jdk1.8.0" / "jre" / "lib" / "security" / "cacerts"
            cacerts.parent.mkdir(parents=True)
            cacerts.touch()
            bin_dir.mkdir()

            result = _find_cacerts(str(bin_dir))
            self.assertEqual(os.path.normcase(result), os.path.normcase(str(cacerts)))

    def test_returns_none_when_not_found(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            bin_dir = Path(td) / "jdk-21" / "bin"
            bin_dir.mkdir(parents=True)
            self.assertIsNone(_find_cacerts(str(bin_dir)))


class FindKeytoolTests(unittest.TestCase):
    def test_finds_keytool_exe(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            bin_dir = Path(td) / "bin"
            bin_dir.mkdir()
            keytool = bin_dir / "keytool.exe"
            keytool.touch()

            result = _find_keytool(str(bin_dir))
            self.assertEqual(os.path.normcase(result), os.path.normcase(str(keytool)))

    def test_finds_keytool_without_extension(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            bin_dir = Path(td) / "bin"
            bin_dir.mkdir()
            keytool = bin_dir / "keytool"
            keytool.touch()

            result = _find_keytool(str(bin_dir))
            self.assertEqual(os.path.normcase(result), os.path.normcase(str(keytool)))

    def test_returns_none_when_not_found(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            bin_dir = Path(td) / "bin"
            bin_dir.mkdir()
            self.assertIsNone(_find_keytool(str(bin_dir)))


class ImportCertTests(unittest.TestCase):
    @patch("subprocess.run")
    def test_success(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="Certificate was added to keystore")
        ok, msg = _import_cert("/bin/keytool", "/path/cacerts", "/path/cert.cer", "my-alias", "changeit")
        self.assertTrue(ok)
        self.assertIn("Certificate", msg)

    @patch("subprocess.run")
    def test_failure(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="keytool error: ...")
        ok, msg = _import_cert("/bin/keytool", "/path/cacerts", "/path/cert.cer", "my-alias", "changeit")
        self.assertFalse(ok)

    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_file_not_found(self, _mock_run: MagicMock) -> None:
        ok, msg = _import_cert("/nonexistent/keytool", "/path/cacerts", "/path/cert.cer", "my-alias", "changeit")
        self.assertFalse(ok)
        self.assertIn("keytool not found", msg)


class AddCertToJavaTests(unittest.TestCase):
    def _make_java_home(self, td: str, name: str, layout: str = "java9") -> str:
        """Create a minimal fake Java home inside *td* and return its bin path."""
        java_home = Path(td) / name
        bin_dir = java_home / "bin"
        bin_dir.mkdir(parents=True)

        # Create a fake keytool
        keytool = bin_dir / "keytool"
        keytool.touch()

        # Create cacerts
        if layout == "java9":
            cacerts_dir = java_home / "lib" / "security"
        else:
            cacerts_dir = java_home / "jre" / "lib" / "security"
        cacerts_dir.mkdir(parents=True)
        (cacerts_dir / "cacerts").touch()

        return str(bin_dir)

    @patch("pywin_update_alternatives.cert_management._import_cert", return_value=(True, "OK"))
    def test_imports_into_all_detected_installs(self, mock_import: MagicMock) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            bin1 = self._make_java_home(td, "jdk-21")
            bin2 = self._make_java_home(td, "jre-11")

            results = add_cert_to_java(
                cert_path="/fake/cert.cer",
                alias="my-alias",
                java_bin_paths=[bin1, bin2],
            )

            self.assertEqual(len(results), 2)
            self.assertTrue(all(r.success for r in results))
            self.assertEqual(mock_import.call_count, 2)

    @patch("pywin_update_alternatives.cert_management._import_cert", return_value=(True, "OK"))
    def test_deduplicates_shared_cacerts(self, mock_import: MagicMock) -> None:
        """When two bin paths share the same cacerts file, it should only be imported once."""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            bin1 = self._make_java_home(td, "jdk-21")
            # Second entry points to same dir (duplicate)
            results = add_cert_to_java(
                cert_path="/fake/cert.cer",
                alias="my-alias",
                java_bin_paths=[bin1, bin1],
            )

            self.assertEqual(mock_import.call_count, 1)

    @patch("pywin_update_alternatives.cert_management._import_cert", return_value=(True, "OK"))
    def test_reports_missing_cacerts(self, mock_import: MagicMock) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            bin_dir = Path(td) / "java" / "bin"
            bin_dir.mkdir(parents=True)

            results = add_cert_to_java(
                cert_path="/fake/cert.cer",
                alias="my-alias",
                java_bin_paths=[str(bin_dir)],
            )

            self.assertEqual(len(results), 1)
            self.assertFalse(results[0].success)
            self.assertIn("cacerts", results[0].message)
            mock_import.assert_not_called()

    @patch("pywin_update_alternatives.cert_management._import_cert", return_value=(True, "OK"))
    def test_reports_missing_keytool(self, mock_import: MagicMock) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            java_home = Path(td) / "jdk-21"
            bin_dir = java_home / "bin"
            bin_dir.mkdir(parents=True)
            # cacerts exists but no keytool
            cacerts_dir = java_home / "lib" / "security"
            cacerts_dir.mkdir(parents=True)
            (cacerts_dir / "cacerts").touch()

            results = add_cert_to_java(
                cert_path="/fake/cert.cer",
                alias="my-alias",
                java_bin_paths=[str(bin_dir)],
            )

            self.assertEqual(len(results), 1)
            self.assertFalse(results[0].success)
            self.assertIn("keytool", results[0].message)
            mock_import.assert_not_called()


if __name__ == "__main__":
    unittest.main()
