#!/usr/bin/env python3
"""
Fetch SHA256 hashes for all assets of a GitHub release, then update a
Homebrew formula (devbox.rb) with the release version and checksums.

Example:
    python parse_github_release_sha256_gemini.py \\
        https://github.com/jetify-com/devbox/releases/tag/0.16.0 \\
        devbox.rb
"""

import pathlib
import re
import sys
from typing import Dict, Iterable, Optional

import requests


def parse_release_url(url: str) -> Optional[tuple[str, str, str]]:
    """
    Extract the owner/repo/tag triple from a GitHub release URL.
    """
    match = re.search(r"github\.com/([^/]+)/([^/]+)/releases/tag/([^/]+)", url)
    if not match:
        return None
    return match.group(1), match.group(2), match.group(3)


def candidate_checksum_urls(owner: str, repo: str, tag: str) -> Iterable[str]:
    """
    Yield likely checksum file URLs for a given release. Most projects publish
    one of these names next to their assets.
    """
    names = [
        "checksums.txt",
        "checksums.sha256",
        "SHA256SUMS",
        "SHA256SUMS.txt",
    ]
    base = f"https://github.com/{owner}/{repo}/releases/download/{tag}"
    for name in names:
        yield f"{base}/{name}"


def parse_checksum_file(url: str) -> Dict[str, str]:
    """
    Download and parse a checksum file of the form:
        <sha256>  <filename>
    """
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()

    results: Dict[str, str] = {}
    for line in resp.text.splitlines():
        line = line.strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) != 2:
            continue

        sha256, filename = parts
        if re.fullmatch(r"[0-9a-fA-F]{64}", sha256):
            results[filename.lstrip("*")] = sha256.lower()
    return results


def fetch_release_checksums(release_url: str) -> tuple[str, Dict[str, str]]:
    """
    Try each candidate checksum URL until one succeeds and returns hashes.
    Returns the release tag and its checksum mapping.
    """
    parsed = parse_release_url(release_url)
    if not parsed:
        raise ValueError(
            "Release URL should look like "
            "https://github.com/<owner>/<repo>/releases/tag/<tag>"
        )

    owner, repo, tag = parsed

    last_error: Optional[Exception] = None
    for url in candidate_checksum_urls(owner, repo, tag):
        try:
            checksums = parse_checksum_file(url)
            if checksums:
                return tag, checksums
        except Exception as exc:  # noqa: BLE001 - best-effort fallback
            last_error = exc
            continue

    if last_error:
        raise last_error
    raise RuntimeError("No checksum file found for the release.")


def update_formula(path: pathlib.Path, version: str, checksums: Dict[str, str]) -> int:
    """
    Update the Homebrew formula:
      - set the version string
      - replace each sha256 to match the checksum file for its URL's filename
    Returns number of sha lines updated.
    """
    content = path.read_text()
    lines = content.splitlines()

    # Update version line (first occurrence)
    for idx, line in enumerate(lines):
        if re.match(r"\s*version\s+\"[^\"]+\"", line):
            lines[idx] = re.sub(r"\"[^\"]+\"", f"\"{version}\"", line, count=1)
            break

    updated = 0
    i = 0
    while i < len(lines):
        url_match = re.search(r'url\s+"([^"]+)"', lines[i])
        if not url_match:
            i += 1
            continue

        asset_url = url_match.group(1)
        expanded_url = asset_url.replace("#{version}", version)
        filename = expanded_url.rsplit("/", 1)[-1]
        if filename not in checksums:
            raise KeyError(f"Checksum for {filename} not found in checksum file.")

        # find the sha256 line that follows this url (before the next url)
        sha_idx: Optional[int] = None
        for j in range(i + 1, len(lines)):
            if re.search(r'url\s+"', lines[j]):
                break
            if re.match(r"\s*sha256\s+\"[^\"]+\"", lines[j]):
                sha_idx = j
                break

        if sha_idx is None:
            raise RuntimeError(f"No sha256 line found after url for {filename}.")

        indent = re.match(r"^(\s*)", lines[sha_idx]).group(1)
        lines[sha_idx] = f'{indent}sha256 "{checksums[filename]}"'
        updated += 1
        i = sha_idx
        i += 1

    path.write_text("\n".join(lines) + "\n")
    return updated


def main() -> None:
    release_url = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "https://github.com/jetify-com/devbox/releases/tag/0.16.0"
    )
    formula_path = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else pathlib.Path("devbox.rb")

    version, checksums = fetch_release_checksums(release_url)
    updated = update_formula(formula_path, version, checksums)

    print(f"Updated {formula_path} to version {version}")
    print(f"Replaced {updated} sha256 entr{'y' if updated == 1 else 'ies'}.")


if __name__ == "__main__":
    main()
