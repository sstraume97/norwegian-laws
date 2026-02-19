"""Download public archives from Lovdata API."""
import os
import urllib.request
from pathlib import Path

BASE_URL = "https://api.lovdata.no/v1/publicData/get"

ARCHIVES = {
    "gjeldende": "gjeldende-lover.tar.bz2",
    "forskrifter": "gjeldende-sentrale-forskrifter.tar.bz2",
    "lovtidend_historical": "lovtidend-avd1-2001-2025.tar.bz2",
    "lovtidend_current": "lovtidend-avd1-2026.tar.bz2",
}


def download_file(url: str, dest: str) -> str:
    """Download a file if it doesn't already exist."""
    if os.path.exists(dest):
        print(f"  Skipping {dest} (already exists)")
        return dest
    print(f"  Downloading {url}...")
    urllib.request.urlretrieve(url, dest)
    size_mb = os.path.getsize(dest) / (1024 * 1024)
    print(f"  Saved {dest} ({size_mb:.1f} MB)")
    return dest


def download_archives(output_dir: str = ".") -> dict[str, str]:
    """Download all law archives from the Lovdata API.

    Returns a dict with keys 'gjeldende' and 'lovtidend' pointing
    to the downloaded archive paths.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    result = {}
    gjeldende_path = os.path.join(output_dir, ARCHIVES["gjeldende"])
    download_file(f"{BASE_URL}/{ARCHIVES['gjeldende']}", gjeldende_path)
    result["gjeldende"] = gjeldende_path

    lovtidend = []
    for key in ["lovtidend_historical", "lovtidend_current"]:
        path = os.path.join(output_dir, ARCHIVES[key])
        download_file(f"{BASE_URL}/{ARCHIVES[key]}", path)
        lovtidend.append(path)
    result["lovtidend"] = lovtidend

    return result
