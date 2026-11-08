"""LifeGen Genetics: checks GitHub for a newer version in the background."""
import re
import threading
from configparser import ConfigParser

# which branch has the newest version of each channel. Stable players download the stable
# branch (the green Code button), dev builds the dev branch. Each only hears about its own channel.
BRANCHES = {"stable": "stable", "dev": "dev"}
REPO = "Tropicaluwu/Lifegen-Genetics-dev"

# filled in by the check: the newest version ("v1.1.2"), if it's newer than this one
newer_version = None
_started = False


def update_channel():
    """"stable" or "dev", from update_channel in version.ini. Builds without it are stable."""
    version_ini = ConfigParser()
    version_ini.read("version.ini", encoding="utf-8")
    channel = version_ini.get("DEFAULT", "update_channel", fallback="stable")
    return channel if channel in BRANCHES else "stable"


def download_page():
    """Where players download the game (the green Code button, then Download ZIP)"""
    if update_channel() == "dev":
        return f"https://github.com/{REPO}/tree/{BRANCHES['dev']}"
    return f"https://github.com/{REPO}"


def version_tuple(version):
    """'v1.1.2' -> (1, 1, 2), so versions compare as numbers (1.10 is newer than 1.9)"""
    return tuple(int(part) for part in re.findall(r"\d+", str(version)))


def _check():
    global newer_version
    try:
        import requests
        from scripts.housekeeping.game_version import get_version_info

        branch = BRANCHES[update_channel()]
        response = requests.get(
            f"https://raw.githubusercontent.com/{REPO}/{branch}/version.ini", timeout=10
        )
        response.raise_for_status()
        found = re.search(r"^\s*version_number\s*=\s*(\S+)", response.text, re.MULTILINE)
        if not found:
            return
        latest = found.group(1)
        current = get_version_info().version_number
        if version_tuple(latest) > version_tuple(current):
            newer_version = latest
    except Exception:  # no internet, GitHub busy...: no reminder this time
        pass


def start_check():
    """Starts the check (once per game start)"""
    global _started
    from scripts.game_structure.game.settings import game_setting_get

    if _started or game_setting_get("check_for_updates") is False:
        return
    _started = True
    threading.Thread(target=_check, daemon=True).start()
