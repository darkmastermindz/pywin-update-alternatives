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

