#!/usr/bin/env python3
"""
Script to parse GitHub release page, extract SHA256 hashes, and update Homebrew formula.

DESCRIPTION:
    This script automates the process of updating any Homebrew formula with
    the latest version and SHA256 checksums from a GitHub release page. It fetches the
    release information, downloads the checksums file, and updates the formula accordingly.

USAGE:
    python parse_github_release_sha256.py RELEASE_URL --output OUTPUT_FILE [--app-name APP_NAME]

ARGUMENTS:
    release_url     Required. URL of the GitHub release page.
                    Example: https://github.com/owner/repo/releases/tag/1.0.0

    --output, -o    Required. Path to the Ruby formula file to update.

    --app-name, -n  Optional. Name of the application (used for filename matching).
                    If not provided, will be extracted from the GitHub repository name.

EXAMPLES:
    # Update devbox.rb to version 0.16.0
    python parse_github_release_sha256.py https://github.com/jetify-com/devbox/releases/tag/0.16.0 -o devbox.rb

    # Update myapp formula to latest release
    python parse_github_release_sha256.py https://github.com/company/myapp/releases/latest -o myapp.rb

    # Update with explicit app name (if binary name differs from repo name)
    python parse_github_release_sha256.py https://github.com/company/my-project/releases/tag/v2.0.0 -o myapp.rb --app-name myapp

    # Update with absolute path
    python parse_github_release_sha256.py https://github.com/owner/repo/releases/tag/1.0.0 -o /path/to/formula.rb

REQUIREMENTS:
    - Python 3.6+
    - requests library: pip install requests
    - beautifulsoup4 library: pip install beautifulsoup4

    Install all requirements:
    pip install requests beautifulsoup4

OUTPUT:
    The script will:
    1. Fetch the GitHub release page
    2. Extract the version number from the URL
    3. Extract the app name from the repository URL (or use provided --app-name)
    4. Download and parse the checksums file
    5. Display all found SHA256 hashes
    6. Update the specified Ruby formula file with:
       - New version number
       - Updated SHA256 hashes for all platforms

SUPPORTED PLATFORMS:
    - macOS Intel (darwin_amd64)
    - macOS ARM (darwin_arm64)
    - Linux 32-bit (linux_386)
    - Linux 64-bit (linux_amd64)
    - Linux ARM 64-bit (linux_arm64)
    - Linux ARMv7 (linux_armv7l)

EXIT CODES:
    0 - Success
    1 - Error (missing checksums, file not found, network error, etc.)

AUTHOR:
    Generic script for updating Homebrew formulas from GitHub releases

"""

import requests
from bs4 import BeautifulSoup
import re
import sys
import os

def extract_app_name_from_url(url):
    """
    Extract the application name from the GitHub repository URL.

    Args:
        url: GitHub release URL

    Returns:
        str: Application name
    """
    # Extract repo name from URL like https://github.com/owner/repo/releases/...
    match = re.search(r'github\.com/[^/]+/([^/]+)/', url)
    if match:
        return match.group(1)
    return None


def parse_release_page(url, app_name=None):
    """
    Parse GitHub release page and extract version and SHA256 hashes for each file.

    Args:
        url: URL of the GitHub release page
        app_name: Optional application name (extracted from URL if not provided)

    Returns:
        tuple: (version, app_name, dict of filename to SHA256 hash)
    """
    print(f"Fetching release page: {url}")

    # Extract version from URL
    version_match = re.search(r'/tag/v?(\d+\.\d+\.\d+)', url)
    if not version_match:
        raise ValueError(f"Could not extract version from URL: {url}")
    version = version_match.group(1)

    # Extract app name if not provided
    if not app_name:
        app_name = extract_app_name_from_url(url)
        if not app_name:
            raise ValueError(f"Could not extract app name from URL: {url}")
        print(f"Detected app name: {app_name}")

    # Fetch the page
    response = requests.get(url)
    response.raise_for_status()

    # Parse HTML
    soup = BeautifulSoup(response.text, 'html.parser')

    results = {}

    # Method 1: Look for SHA256 checksums file
    asset_links = soup.find_all('a', href=re.compile(r'/(releases/download|assets)/'))

    checksums_url = None
    for link in asset_links:
        href = link.get('href', '')
        filename = href.split('/')[-1]
        if 'checksum' in filename.lower() or 'sha256' in filename.lower() or filename.endswith('sums.txt'):
            checksums_url = f"https://github.com{href}" if href.startswith('/') else href
            break

    if checksums_url:
        try:
            print(f"Found checksums file: {checksums_url}")
            checksum_response = requests.get(checksums_url)
            checksum_response.raise_for_status()

            # Parse checksums file (format: <hash>  <filename>)
            for line in checksum_response.text.split('\n'):
                line = line.strip()
                if not line:
                    continue

                # Try different formats
                parts = re.split(r'\s+', line, 1)
                if len(parts) == 2:
                    if len(parts[0]) == 64 and all(c in '0123456789abcdefABCDEF' for c in parts[0]):
                        sha256_hash = parts[0].lower()
                        filename = parts[1].strip('*').strip()
                        results[filename] = sha256_hash
        except Exception as e:
            print(f"Warning: Could not fetch checksums file: {e}")

    # Method 2: Look for SHA256 in release notes if checksums file not found
    if not results:
        release_body = soup.find('div', {'class': 'markdown-body'})

        if release_body:
            text = release_body.get_text()

            patterns = [
                r'([a-zA-Z0-9._-]+\.(?:tar\.gz|zip|tar\.xz|exe|dmg|deb|rpm))\s*[:\s]+\s*([a-fA-F0-9]{64})',
                r'([a-fA-F0-9]{64})\s+([a-zA-Z0-9._-]+\.(?:tar\.gz|zip|tar\.xz|exe|dmg|deb|rpm))',
            ]

            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    groups = match.groups()
                    if len(groups[0]) == 64 and all(c in '0123456789abcdefABCDEF' for c in groups[0]):
                        sha256_hash = groups[0].lower()
                        filename = groups[1]
                    else:
                        filename = groups[0]
                        sha256_hash = groups[1].lower()

                    results[filename] = sha256_hash

    return version, app_name, results


def update_formula_file(version, app_name, sha256_hashes, rb_file_path):
    """
    Update the Homebrew formula file with new version and SHA256 hashes.

    Args:
        version: Version string (e.g., "0.16.0")
        app_name: Application name (e.g., "devbox")
        sha256_hashes: Dictionary mapping filename to SHA256 hash
        rb_file_path: Path to formula .rb file
    """
    # Read the current file
    with open(rb_file_path, 'r') as f:
        content = f.read()

    # Update version
    content = re.sub(
        r'version\s+"[\d.]+"',
        f'version "{version}"',
        content
    )

    # Map platform identifiers to filenames
    platform_map = {
        'darwin_amd64': f'{app_name}_{version}_darwin_amd64.tar.gz',
        'darwin_arm64': f'{app_name}_{version}_darwin_arm64.tar.gz',
        'linux_386': f'{app_name}_{version}_linux_386.tar.gz',
        'linux_amd64': f'{app_name}_{version}_linux_amd64.tar.gz',
        'linux_arm64': f'{app_name}_{version}_linux_arm64.tar.gz',
        'linux_armv7l': f'{app_name}_{version}_linux_armv7l.tar.gz',
    }

    # Update SHA256 hashes
    for platform, filename in platform_map.items():
        if filename in sha256_hashes:
            sha256 = sha256_hashes[filename]
            # Find and replace the sha256 line after the corresponding platform URL
            # Look for pattern: url "..._<platform>.tar.gz" followed by sha256 line
            pattern = rf'(url\s+"[^"]*_{platform}\.tar\.gz"[^)]*\))\s*\n\s*sha256\s+"[a-fA-F0-9]+"'
            replacement = rf'\1\n    sha256 "{sha256}"'
            content = re.sub(pattern, replacement, content)
            print(f"Updated SHA256 for {platform}: {sha256}")
        else:
            print(f"Warning: No SHA256 found for {filename}")

    # Write the updated content back
    with open(rb_file_path, 'w') as f:
        f.write(content)

    print(f"\nSuccessfully updated {rb_file_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Parse GitHub release page, extract SHA256 hashes, and update Homebrew formula.',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        'release_url',
        help='URL of the GitHub release page (e.g., https://github.com/owner/repo/releases/tag/1.0.0)'
    )
    parser.add_argument(
        '-o', '--output',
        dest='output_file',
        required=True,
        help='Path to the Ruby formula file to update'
    )
    parser.add_argument(
        '-n', '--app-name',
        dest='app_name',
        default=None,
        help='Application name (if different from repository name)'
    )

    args = parser.parse_args()
    url = args.release_url
    rb_file_path = os.path.abspath(args.output_file)
    app_name = args.app_name

    if not os.path.exists(rb_file_path):
        print(f"Error: Formula file not found at {rb_file_path}")
        sys.exit(1)

    try:
        # Parse release page
        version, detected_app_name, sha256_hashes = parse_release_page(url, app_name)

        # Use detected app name if not provided
        if not app_name:
            app_name = detected_app_name

        if not sha256_hashes:
            print("\nNo SHA256 hashes found on the page.")
            print("This could mean:")
            print("1. The release doesn't include SHA256 hashes")
            print("2. The format is different than expected")
            print("3. The page structure has changed")
            sys.exit(1)

        print(f"\n{'='*80}")
        print(f"Application: {app_name}")
        print(f"Version: {version}")
        print(f"Found {len(sha256_hashes)} file(s) with SHA256 hashes:")
        print(f"{'='*80}\n")

        for filename, sha256 in sorted(sha256_hashes.items()):
            print(f"  {filename}: {sha256}")

        # Update formula file
        print(f"\n{'='*80}")
        print(f"Updating {os.path.basename(rb_file_path)}...")
        print(f"{'='*80}\n")

        update_formula_file(version, app_name, sha256_hashes, rb_file_path)

        print(f"\n{'='*80}")
        print("Update complete!")
        print(f"{'='*80}")

    except requests.RequestException as e:
        print(f"Error fetching the page: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
