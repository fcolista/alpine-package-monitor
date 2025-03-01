# alpine-package-monitor
This script monitors packages maintained by a specific maintainer in the Alpine Linux `aports` repository. It checks for new versions of these packages using the [release-monitoring.org](https://release-monitoring.org/) API and notifies you if an upgrade is available. 

The script is designed to handle package name mismatches and supports advanced features like filtering by check intervals and sending notifications via Telegram .

---

## Features

- **Automatic Repository Updates**: Clones or updates the Alpine Linux `aports` repository.
- **Maintainer Filtering**: Finds packages maintained by a specific maintainer.
- **Version Comparison**: Compares the current version in `APKBUILD` with the latest version from `release-monitoring.org`.
- **Advanced Name Matching**: Handles package name mismatches by checking `_pkgreal` (for Perl packages) and `_pkgname` (for Python packages).
- **Categorized Output**: Organizes results into:
  - **Upgrade Available**
  - **Up-to-Date**
  - **No Version Found**
  - **Downgrade Detected**
  - **Invalid Version Format**
- **Telegram Notifications**: Sends notifications via a Telegram bot (optional).
- **Check Intervals**: Skips packages that were recently checked (configurable).

---

## Prerequisites

- **Python 3.7+**
  Required Python libraries:
  ```bash
  pip install aiohttp packaging pyyaml
  ```

**Git:** To clone and update the aports repository.

**API Key:** A valid API key from [release-monitoring.org](https://release-monitoring.org/).

---

## Setup
- **Clone the repository**
```
git clone https://github.com/yourusername/alpine-package-monitor.git
cd alpine-package-monitor
```
- **Install dependencies**
```bash
pip install -r requirements.txt
```
- **Create configuration file**
```yaml
aports_repo_url: "https://gitlab.alpinelinux.org/alpine/aports.git"
aports_dir: "aports"
maintainer: "Your Name <your.email@example.com>"
release_monitoring_api_url: "https://release-monitoring.org/api/v2/projects/"
api_key: "your_api_key_here"
distribution: "alpine"
check_interval_days: 1  # Optional: Set to 0 to always check
telegram_bot_token: "your_telegram_bot_token"  # Optional
telegram_chat_id: "your_telegram_chat_id"  # Optional
```
- **Run the script**
```bash
python3 check_aports.py
```

---

## Configuration

```config.yaml```

| **Key** | **Description** |
| --- | --- |
|```aports_repo_url```|	URL of the Alpine Linux aports repository.|
|```aports_dir```|	Directory to clone/update the aports repository.|
|```maintainer```|	Maintainer string to filter packages (e.g., Your Name <your.email@example.com>).|
|```release_monitoring_api_url```|	URL of the release-monitoring.org API.|
|```api_key```|	API key for release-monitoring.org.|
|```distribution```|	Distribution to filter packages (e.g., alpine).|
|```check_interval_days```|	Number of days to wait before rechecking a package (set to 0 to always check).|
|```telegram_bot_token```|	Telegram bot token for notifications (optional).|
|```telegram_chat_id```|	Telegram chat ID for notifications (optional).|

---

## Usage

**Running the Script**
- **Basic Usage:**

```bash
python3 check_aports.py
```
- **Output Example:**
```
Cloning https://gitlab.alpinelinux.org/alpine/aports.git...
Looking for packages maintained by: Your Name <your.email@example.com>
Found package: raft (version 0.18.1)
Found package: xmlstarlet (version 1.6.1)
Found 2 packages maintained by Your Name <your.email@example.com>
Checking 2 packages...

=== Upgrade Available ===
🚀 Upgrade available for raft: 0.18.1 -> 1.7.2

=== Up-to-Date ===
✅ xmlstarlet is up to date (1.6.1)
```

- **Telegram Notifications:**
If Telegram credentials are provided in ```config.yaml```, notifications will be sent to the specified chat.
