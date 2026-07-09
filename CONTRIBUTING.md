# Contributing

Thank you for your interest in contributing to the EBI (openEQUELLA Bulk Importer)!
Contributions of all kinds are welcome — bug fixes, new features, documentation improvements, and issue reports.

## Development Setup

For a user-focused overview and release links, see [README.md](README.md). This guide covers contributor and maintainer workflows.

### Prerequisites

- Python 3.8+
- wxPython 4.x
- On Linux, GTK+ 3 development libraries are required for wxPython
- PyInstaller if you need to produce standalone packages locally

Creating a virtual environment is recommended to avoid dependency conflicts:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Install the project dependencies:

```bash
pip3 install -r requirements.txt
```

> **Note on Linux**: You may need to install GTK+ 3 development libraries before installing `wxPython`.

Linux system packages commonly required for wxPython:

```bash
sudo apt-get install build-essential gettext python3-dev libgtk-3-dev
```

If you need to build standalone packages locally, install PyInstaller as well:

```bash
pip3 install PyInstaller
```

### Running the App Locally

From the repository root, launch the GUI application with:

```bash
python3 source/ebi.py
```

### Code Structure Overview

- `source/ebi.py`: Main entry point script that launches the GUI.
- `source/MainFrame.py`: Core wxPython GUI definitions and flow wiring.
- `source/Engine.py`: CSV processing state and data orchestration.
- `source/RowProcessor.py`: Row-to-item processing logic using a `RowContext`.
- `source/equellaclient_rest.py`: REST API client surface used by EBI.

## Contribution Workflow

1. **Fork** the repository on GitHub and clone your fork locally.
2. **Create a branch** for your change:
   ```bash
   git checkout -b my-feature-or-fix
   ```
3. **Make your changes** and verify they work by running EBI from source (see [Running the App Locally](#running-the-app-locally)).
4. **Commit** with a clear, descriptive message.
5. **Push** your branch to your fork and open a **Pull Request** against `master`.
6. Respond to any review feedback.

## Code Conventions

- Follow [PEP 8](https://peps.python.org/pep-0008/) style guidelines for Python code.
- Keep changes focused — one logical change per pull request makes review easier.
- Use descriptive variable and function names.

## Testing

EBI does not currently have an automated test suite.
Before submitting a pull request, manually verify your changes by running EBI from source:

```bash
python3 source/ebi.py
```

Exercise any workflows affected by your change (e.g. import, export, update, delete) against a running openEQUELLA instance to confirm correct behaviour.

## Packaging and CI

Standalone packages for Windows, macOS, and Linux are built automatically via GitHub Actions.
You do not need to build packages locally to contribute code changes.

### Automated Builds (GitHub Actions)

The CI workflow automatically compiles all three standalone versions (Windows, macOS, Linux) for supported pull requests and pushes to `master`. The resulting packages are uploaded as GitHub Actions build artifacts for those workflow runs. On tag pushes, the workflow also publishes these packages as release assets in GitHub Releases.

### Manual Compilation

For local testing or manual builds, compile each standalone version on its matching operating system: Windows on Windows, Linux on Linux, and macOS on macOS.

#### Compiling a Windows Standalone Package

Use a Windows computer with Python 3.8+, wxPython, and PyInstaller installed.

Navigate to the `package-win` directory and run `package.bat`. It creates `ebi.zip` containing the packaged application.
`package.bat` does the following automatically:
1. Validates Python and PyInstaller dependencies.
2. Removes any previous packages from the working folder.
3. Invokes `setup.py`, which uses PyInstaller to generate a standalone package in a folder called `dist`. The `dist` folder contains `ebi.exe`, which is the standalone Windows EBI executable.
4. Renames the `dist` folder to `ebi`.
5. Copies the source files into the `ebi\source` folder for reference.
6. Invokes `package.py`, which zips the `ebi` folder into `ebi.zip`.

#### Compiling a Linux Standalone Package

Use a Linux computer with Python 3.8+, wxPython, and PyInstaller installed.

Navigate to the `package-linux` directory and run `bash package.sh`. It creates `ebi.zip` containing the packaged application compatible with Linux environments.
`package.sh` performs the same operations automatically as its Windows counterpart (`package.bat`), yielding an ELF executable (`ebi`) inside `ebi/ebi` rather than an `.exe`, and finally zipping it into `ebi.zip`.

#### Compiling a macOS Standalone Package

Use a Macintosh computer with Python 3.8+, wxPython 4.2+, and PyInstaller installed.

Navigate to the `package-mac` directory and run `bash ebi-package.command` (or make it executable and run it). It creates `ebi.dmg` in the `dist` subfolder.
`ebi-package.command` does the following:
1. Validates dependencies and checks for PyInstaller.
2. Removes previous builds from the `build` and `dist` directories.
3. Invokes `setup.py`, which uses PyInstaller to generate a macOS application bundle (`ebi.app`) inside the `dist` folder.
4. Copies the launcher script wrapper into the `ebi.app` package.
5. Creates a disk image `ebi.dmg` in the `dist` folder from `ebi.app` using `hdiutil`.

## Reporting Issues

Please use [GitHub Issues](https://github.com/openequella/openEQUELLA-ebi/issues) to report bugs or request features.
When reporting a bug, include:
- EBI version or commit used
- Operating system and Python version (if running from source)
- Steps to reproduce the problem
- Any relevant error messages or screenshots
