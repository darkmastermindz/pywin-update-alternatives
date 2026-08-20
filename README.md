# pywin-update-alternatives

Switch alternative versions for Windows development tools with a Python CLI that can bootstrap an official embeddable Python runtime on demand.

## Embedded Python support

This repository now includes a Windows launcher that downloads the latest official embeddable Python package from python.org the first time it is needed, extracts it into a local `.embedded-python` folder, and then runs the project with that private runtime.

Use either launcher from Windows:

- `pywin-update-alternatives.cmd`
- `scripts\pywin-update-alternatives.ps1`

Example:

```powershell
.\pywin-update-alternatives.cmd detect-java
```

## Current CLI commands

### `detect-java`

Detects Java-related PATH entries and separates them into JDK and JRE candidates.

```powershell
.\pywin-update-alternatives.cmd detect-java --format text
```
