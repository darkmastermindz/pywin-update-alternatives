# pywin-update-alternatives

Switch alternative versions for Windows development tools with a Python CLI that can bootstrap an official embeddable Python runtime on demand.

## Shell compatibility

The tool works in all three common Windows shells.  Choose the launcher that matches your environment:

| Shell | Launcher |
|-------|----------|
| **CMD Prompt** | `pywin-update-alternatives.cmd` |
| **PowerShell** | `scripts\pywin-update-alternatives.ps1` |
| **Git Bash / MSYS2** | `./pywin-update-alternatives.sh` |

> **Note:** Git Bash and MSYS2 automatically convert Windows-style paths (e.g. `C:\Program Files\Java\jdk-21\bin`) to POSIX-style (`/c/Program Files/Java/jdk-21/bin`).  The tool handles this conversion transparently, so detected Java paths are always reported in Windows format.

## Embedded Python support

The CMD and PowerShell launchers download the latest official embeddable Python package from python.org the first time they are needed, extract it into a local `.embedded-python` folder, and then run the project with that private runtime.

If PowerShell is unavailable or the execution policy blocks the bootstrap script, the CMD launcher automatically falls back to a `python` / `py` interpreter already on `PATH`.

The Git Bash launcher uses `python` / `python3` / `py` from `PATH`, or the `.embedded-python` runtime if it was previously bootstrapped.

## Usage

### Debian-compatible alternatives mode

The Python entry point now also supports a Debian-style `update-alternatives` CLI for managing generic links, alternative targets, and slave links:

```bash
python -m pywin_update_alternatives --install /usr/bin/editor editor /opt/tools/nvim 100
python -m pywin_update_alternatives --display editor
python -m pywin_update_alternatives --config editor
```

Supported Debian-style commands include `--install`, `--remove`, `--remove-all`, `--auto`, `--display`, `--query`, `--list`, `--get-selections`, `--set-selections`, `--config`, `--set`, `--all`, `--help`, and `--version`.

### CMD Prompt

```cmd
pywin-update-alternatives.cmd detect-java
pywin-update-alternatives.cmd detect-java --format text
```

### PowerShell

```powershell
.\scripts\pywin-update-alternatives.ps1 detect-java
.\scripts\pywin-update-alternatives.ps1 detect-java --format text
```

### Git Bash / MSYS2

```bash
./pywin-update-alternatives.sh detect-java
./pywin-update-alternatives.sh detect-java --format text
```

## Current CLI commands

### `detect-java`

Detects Java-related PATH entries and separates them into JDK and JRE candidates.

```powershell
.\pywin-update-alternatives.cmd detect-java --format text
```

Options:

| Flag | Values | Default | Description |
|------|--------|---------|-------------|
| `--format` | `json`, `text` | `json` | Output format |
| `--path` | Any PATH string | Current process `PATH` | Override the PATH to inspect |

### `add-java-cert`

Imports a certificate (`.cer`, `.pem`, or `.crt`) into the `cacerts` truststore of every JDK and JRE installation found on `PATH`.  This is a thin, cross-shell wrapper around `keytool -importcert`.

```powershell
.\scripts\pywin-update-alternatives.ps1 add-java-cert C:\certs\my-ca.cer --alias my-ca
```

```bash
./pywin-update-alternatives.sh add-java-cert /c/certs/my-ca.cer --alias my-ca
```

Options:

| Flag | Values | Default | Description |
|------|--------|---------|-------------|
| `CERT_FILE` | File path | *(required)* | Path to the certificate file to import |
| `--alias` | String | *(required)* | Alias under which the certificate is stored in the truststore |
| `--storepass` | String | `changeit` | Truststore password |
| `--path` | Any PATH string | Current process `PATH` | Override the PATH used to find Java installations |
| `--format` | `json`, `text` | `text` | Output format |
