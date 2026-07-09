# EBI (openEQUELLA Bulk Importer)
> 🛠 **Status:** This repository reflects the latest development. For the most recent stable executable, please see [Latest Releases](https://github.com/openequella/openEQUELLA-ebi/releases/latest).

The EBI is a popular tool for importing content into openEQUELLA. It can also be used for updating, deleting and exporting content.

The EBI is written in Python and distributed as standalone packages for Windows, macOS, and Linux, so most users can run it without installing Python or other dependencies.

User guide can be found at: https://openequella.github.io/equella-tools/bulkImporterUserManual.html

## Getting Started

For most users, the quickest way to get started is to download the latest standalone package from [Latest Releases](https://github.com/openequella/openEQUELLA-ebi/releases/latest).

1. Download the package for your operating system.
2. Extract or open the downloaded archive.
3. Launch the EBI application included in the package.

No `.env` setup is required for normal end-user use of the packaged application.

> **Note for macOS users:** When downloading the `ebi.dmg` release asset, macOS Gatekeeper may flag the application as "damaged" because it was downloaded from the internet and lacks an Apple Developer certificate. To run the application, remove the quarantine attribute:
> ```bash
> xattr -cr /path/to/ebi.app
> ```
> Alternatively, right-click the application bundle and choose **Open** to bypass the initial security prompt.

## Contributing

Developer and contributor guidance lives in [CONTRIBUTING.md](CONTRIBUTING.md), including:

- local development environment setup
- running EBI from source
- build and packaging instructions
- contribution workflow and pull request guidance
- testing expectations and code structure notes
