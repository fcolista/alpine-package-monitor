#!/usr/bin/env python3

import os
import yaml
import subprocess
import asyncio
import aiohttp
import re
from packaging import version
from datetime import datetime, timedelta

# Load configuration from YAML file
with open("config.yaml", "r") as config_file:
    config = yaml.safe_load(config_file)

# Constants from YAML
APORTS_REPO_URL = config["aports_repo_url"]
APORTS_DIR = config["aports_dir"]
MAINTAINER = config["maintainer"]
RELEASE_MONITORING_API_URL = config["release_monitoring_api_url"]
API_KEY = config["api_key"]
DISTRIBUTION = config["distribution"]
VERSION_HISTORY_FILE = "version_history.yaml"
CHECK_INTERVAL_DAYS = config.get("check_interval_days", 0)  # Default to 0 (always check)


def update_aports_repo():
    """Clone or update the aports repository."""
    if not os.path.exists(APORTS_DIR):
        print(f"Cloning {APORTS_REPO_URL}...")
        subprocess.run(["git", "clone", "--depth=1", APORTS_REPO_URL, APORTS_DIR])
    else:
        print(f"Updating {APORTS_DIR}...")
        subprocess.run(["git", "-C", APORTS_DIR, "pull", "--rebase"])


def extract_package_info(apkbuild_path):
    """Extract package name, version, and alternative names from APKBUILD."""
    with open(apkbuild_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

        # Extract pkgname
        pkgname_match = re.search(r'^pkgname=(.+)$', content, re.MULTILINE)
        pkgname = pkgname_match.group(1).strip('"\'').strip() if pkgname_match else None

        # Extract pkgver
        pkgver_match = re.search(r'^pkgver=(.+)$', content, re.MULTILINE)
        pkgver = pkgver_match.group(1).strip('"\'').strip() if pkgver_match else None

        # Extract _pkgreal (for Perl packages)
        pkgreal_match = re.search(r'^_pkgreal=(.+)$', content, re.MULTILINE)
        pkgreal = pkgreal_match.group(1).strip('"\'').strip() if pkgreal_match else None

        # Extract _pkgname (for Python packages)
        pkgname_python_match = re.search(r'^_pkgname=(.+)$', content, re.MULTILINE)
        pkgname_python = pkgname_python_match.group(1).strip('"\'').strip() if pkgname_python_match else None

        return {
            "pkgname": pkgname,
            "pkgver": pkgver,
            "pkgreal": pkgreal,
            "pkgname_python": pkgname_python,
        }


def find_maintainer_packages_file_traversal():
    """Get all packages maintained by the specified maintainer by traversing files directly."""
    print(f"Looking for packages maintained by: {MAINTAINER}")

    packages = {}

    # Use multiple search patterns for better compatibility with busybox
    search_patterns = [
        MAINTAINER,  # Full maintainer string
        MAINTAINER.split("<")[0].strip() if "<" in MAINTAINER else "",  # Just the name
        MAINTAINER.split("<")[1].split(">")[0] if "<" in MAINTAINER and ">" in MAINTAINER else ""  # Just the email
    ]

    search_patterns = [p for p in search_patterns if p]  # Remove empty patterns

    print(f"Searching for patterns: {search_patterns}")

    # Walk through the aports directory structure
    for root, dirs, files in os.walk(APORTS_DIR):
        if "APKBUILD" in files:
            apkbuild_path = os.path.join(root, "APKBUILD")

            try:
                with open(apkbuild_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()

                    # Look for maintainer line
                    for pattern in search_patterns:
                        maintainer_line = None

                        # Simple case-insensitive search
                        for line in content.splitlines():
                            if line.startswith("# Maintainer:") and pattern.lower() in line.lower():
                                maintainer_line = line
                                break

                        if maintainer_line:
                            # Extract package info
                            package_info = extract_package_info(apkbuild_path)
                            if package_info["pkgname"] and package_info["pkgver"]:
                                packages[package_info["pkgname"]] = {
                                    "version": package_info["pkgver"],
                                    "pkgreal": package_info["pkgreal"],
                                    "pkgname_python": package_info["pkgname_python"],
                                }
                                print(f"Found package: {package_info['pkgname']} (version {package_info['pkgver']})")
                            break  # No need to check other patterns
            except Exception as e:
                print(f"Error processing file {apkbuild_path}: {e}")

    return packages


def load_version_history():
    """Load version history from YAML file."""
    if os.path.exists(VERSION_HISTORY_FILE):
        with open(VERSION_HISTORY_FILE, "r") as f:
            try:
                return yaml.safe_load(f) or {}
            except yaml.YAMLError:
                print(f"Error reading {VERSION_HISTORY_FILE}, creating new history")
                return {}
    return {}


def save_version_history(history):
    """Save version history to YAML file."""
    with open(VERSION_HISTORY_FILE, "w") as f:
        yaml.dump(history, f, default_flow_style=False)


def should_check_package(package, history):
    """Determine if a package needs to be checked based on history."""
    if CHECK_INTERVAL_DAYS == 0:  # Always check if interval is 0
        return True

    if package not in history:
        return True

    last_check = datetime.fromisoformat(history[package]["last_checked"])
    return (datetime.now() - last_check) > timedelta(days=CHECK_INTERVAL_DAYS)


async def get_latest_version_async(package_name, session):
    """Get the latest version of a package from release-monitoring.org asynchronously."""
    params = {
        "name": package_name,
        "distribution": DISTRIBUTION,
    }

    try:
        async with session.get(RELEASE_MONITORING_API_URL, params=params) as response:
            if response.status == 200:
                data = await response.json()
                if data["items"]:
                    project = data["items"][0]
                    stable_versions = project.get("stable_versions", [])
                    if stable_versions:
                        return stable_versions[0]
    except Exception as e:
        print(f"Error fetching data for {package_name}: {e}")

    return None


def send_telegram_message(message, bot_token, chat_id):
    """Send a message to a Telegram chat using a bot."""
    telegram_api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        import requests  # Import here to avoid dependency issues with async code
        response = requests.post(telegram_api_url, data=payload)
        if response.status_code == 200:
            print(f"Telegram notification sent successfully")
        else:
            print(f"Failed to send Telegram notification: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"Error sending Telegram notification: {e}")


def notify(message):
    """Send a notification message to both console and Telegram."""
    print(message)

    # Send notification via Telegram bot
    if config.get("telegram_bot_token") and config.get("telegram_chat_id"):
        send_telegram_message(
            message,
            config["telegram_bot_token"],
            config["telegram_chat_id"]
        )


async def check_package_version_async(package, package_info, session, history):
    """Check a single package version asynchronously."""
    current_version = package_info["version"]
    alternative_names = [package, package_info["pkgreal"], package_info["pkgname_python"]]
    alternative_names = [name for name in alternative_names if name]  # Remove None values

    latest_version = None
    for name in alternative_names:
        latest_version = await get_latest_version_async(name, session)
        if latest_version:
            break  # Stop if we find a match

    # Update history regardless of result
    if package not in history:
        history[package] = {}

    history[package]["last_checked"] = datetime.now().isoformat()
    history[package]["current_version"] = current_version

    if latest_version:
        history[package]["latest_version"] = latest_version

        # Normalize versions for comparison
        current_version_normalized = current_version.replace("-", ".")
        latest_version_normalized = latest_version.replace("-", ".")

        try:
            current_parsed = version.parse(current_version_normalized)
            latest_parsed = version.parse(latest_version_normalized)

            if latest_parsed > current_parsed:
                return "upgrade", f"🚀 Upgrade available for {package}: {current_version} -> {latest_version}"
            elif latest_parsed == current_parsed:
                return "up-to-date", f"✅ {package} is up to date ({current_version})"
            else:
                return "downgrade", f"⚠️ {package}: Current version ({current_version}) is newer than latest ({latest_version})"
        except version.InvalidVersion:
            return "invalid", f"❌ {package}: Invalid version format (current: {current_version}, latest: {latest_version})"
    else:
        return "no-version", f"❌ {package}: No version information found in release-monitoring.org"


async def compare_versions_async(packages):
    """Compare versions using async processing."""
    history = load_version_history()
    packages_to_check = {pkg: info for pkg, info in packages.items()
                         if should_check_package(pkg, history)}

    if not packages_to_check:
        print("No packages need checking at this time.")
        return

    print(f"Checking {len(packages_to_check)} packages...")

    async with aiohttp.ClientSession(headers={"Authorization": f"Bearer {API_KEY}"}) as session:
        tasks = []
        for package, package_info in packages_to_check.items():
            tasks.append(check_package_version_async(package, package_info, session, history))

        results = await asyncio.gather(*tasks)

    # Categorize results
    categorized_results = {
        "upgrade": [],
        "up-to-date": [],
        "no-version": [],
        "downgrade": [],
        "invalid": [],
    }

    for result in results:
        category, message = result
        categorized_results[category].append(message)

    # Print categorized results
    print("\n=== Upgrade Available ===")
    for message in categorized_results["upgrade"]:
        print(message)

    print("\n=== Up-to-Date ===")
    for message in categorized_results["up-to-date"]:
        print(message)

    print("\n=== No Version Found ===")
    for message in categorized_results["no-version"]:
        print(message)

    print("\n=== Downgrade Detected ===")
    for message in categorized_results["downgrade"]:
        print(message)

    print("\n=== Invalid Version Format ===")
    for message in categorized_results["invalid"]:
        print(message)

    # Save updated history
    save_version_history(history)


async def main():
    """Main function for the package monitor."""
    update_aports_repo()
    packages = find_maintainer_packages_file_traversal()

    if packages:
        print(f"Found {len(packages)} packages maintained by {MAINTAINER}")
        await compare_versions_async(packages)
    else:
        print(f"No packages found maintained by {MAINTAINER}.")


if __name__ == "__main__":
    asyncio.run(main())
