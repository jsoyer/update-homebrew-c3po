# Update Homebrew C3PO

A Python script to automate updating Homebrew formulas with the latest version and SHA256 checksums from GitHub releases.

## Description

This script streamlines the process of maintaining Homebrew formulas by automatically:
- Fetching release information from GitHub
- Extracting version numbers
- Downloading and parsing SHA256 checksums
- Updating your Homebrew formula files with the latest data

Perfect for maintainers who need to keep their Homebrew taps up-to-date with upstream releases.

## Features

- Automatic version extraction from GitHub release URLs
- Support for multiple checksum file formats
- Multiple platform support (macOS Intel/ARM, Linux x86/ARM variants)
- Flexible app name detection or manual specification
- Comprehensive error handling and validation

## Requirements

- Python 3.6 or higher
- Required Python packages:
  - `requests`
  - `beautifulsoup4`

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/update-homebrew-c3po.git
cd update-homebrew-c3po
```

2. Install dependencies:
```bash
pip install requests beautifulsoup4
```

## Usage

### Basic Syntax

```bash
python update-homebrew-c3po.py RELEASE_URL --output FORMULA_FILE [--app-name APP_NAME]
```

### Arguments

- `release_url` (required): URL of the GitHub release page
  - Example: `https://github.com/owner/repo/releases/tag/1.0.0`

- `--output, -o` (required): Path to the Ruby formula file to update

- `--app-name, -n` (optional): Application name for filename matching
  - If not provided, automatically extracted from repository name

### Examples

Update a formula to version 0.16.0:
```bash
python update-homebrew-c3po.py \
  https://github.com/jetify-com/devbox/releases/tag/0.16.0 \
  -o devbox.rb
```

Update to the latest release:
```bash
python update-homebrew-c3po.py \
  https://github.com/company/myapp/releases/latest \
  -o myapp.rb
```

Specify app name explicitly (when binary name differs from repo name):
```bash
python update-homebrew-c3po.py \
  https://github.com/company/my-project/releases/tag/v2.0.0 \
  -o myapp.rb \
  --app-name myapp
```

Update with absolute path:
```bash
python update-homebrew-c3po.py \
  https://github.com/owner/repo/releases/tag/1.0.0 \
  -o /path/to/formula.rb
```

## Supported Platforms

The script automatically handles SHA256 checksums for the following platforms:

- macOS Intel (`darwin_amd64`)
- macOS ARM (`darwin_arm64`)
- Linux 32-bit (`linux_386`)
- Linux 64-bit (`linux_amd64`)
- Linux ARM 64-bit (`linux_arm64`)
- Linux ARMv7 (`linux_armv7l`)

## How It Works

1. Fetches the GitHub release page
2. Extracts the version number from the URL
3. Identifies the app name from the repository URL (or uses provided name)
4. Downloads and parses the checksums file
5. Maps checksums to platform-specific binaries
6. Updates the specified Ruby formula file with:
   - New version number
   - Updated SHA256 hashes for all platforms

## Exit Codes

- `0` - Success
- `1` - Error (missing checksums, file not found, network error, etc.)

## Troubleshooting

If the script reports "No SHA256 hashes found", this could mean:
1. The release doesn't include SHA256 hashes
2. The checksum file format is different than expected
3. The GitHub release page structure has changed

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Author

Jerome Soyer
