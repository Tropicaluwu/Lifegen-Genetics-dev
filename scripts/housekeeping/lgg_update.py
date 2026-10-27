"""LifeGen Genetics: is there a newer version on GitHub?

ClanGen's own updater asks ClanGen's update server, which knows nothing about LifeGen Genetics,
so this asks GitHub instead. It runs in the background once per game start, so the start screen
never waits for it, and it quietly gives up without internet.
"""
import re
import threading

# players download the development branch (the green Code button), so its version.ini is the
# newest version
VERSION_FILE = "https://raw.githubusercontent.com/Tropicaluwu/Lifegen-Genetics-dev/development/version.ini"
# where players download the game (the green Code button, then Download ZIP)
DOWNLOAD_PAGE = "https://github.com/Tropicaluwu/Lifegen-Genetics-dev"

# filled in by the check: the newest version ("v1.1.2"), if it's newer than this one
newer_version = None
_started = False


def version_tuple(version):
    """'v1.1.2' -> (1, 1, 2), so versions compare as numbers (1.10 is newer than 1.9)"""
    return tuple(int(part) for part in re.findall(r"\d+", str(version)))


def _check():
    global newer_version
    try:
        import requests
        from scripts.housekeeping.version import get_version_info

        response = requests.get(VERSION_FILE, timeout=10)
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
