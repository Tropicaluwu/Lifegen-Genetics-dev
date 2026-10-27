"""Your own changes to the game's name lists (made in the Names window).

They're kept apart from the game's lists, in custom_names.json: one in the saves folder for all
saves, and one in a save's own folder for just that save. They stack: a save uses the game's
names, then the all-saves changes, then its own. For each list you can add names, take any name
out (the game's or your own), or use only your own names. The rank endings (kit, paw, star...)
can each be changed.
"""
import copy
import os

import ujson

from scripts.housekeeping.datadir import get_save_dir

# list shown in the window: the name list it changes
LISTS = {
    "Prefixes": "normal_prefixes",
    "Suffixes": "normal_suffixes",
    "Rank endings": "special_suffixes",
    "Loner names": "loner_names",
    "Kittypet names": "human_names",
    "Clan names": "clan_prefixes",
    "Blocked names": "inappropriate_names",
}
FILE_NAME = "custom_names.json"


def file_path(save=None):
    folder = get_save_dir() if save is None else os.path.join(get_save_dir(), save)
    return os.path.join(folder, FILE_NAME)


def empty():
    return {"lists": {}, "rank_endings": {}}


def load(save=None):
    """The changes for all saves (save=None) or for one save"""
    path = file_path(save)
    if not os.path.exists(path):
        return empty()
    try:
        with open(path, "r", encoding="utf-8") as read_file:
            data = ujson.loads(read_file.read())
    except (OSError, ValueError):
        return empty()
    data.setdefault("lists", {})
    data.setdefault("rank_endings", {})
    return data


def save(data, save=None):
    path = file_path(save)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as write_file:
        write_file.write(ujson.dumps(data, indent=4, ensure_ascii=False))


def list_changes(data, key):
    """The changes to one list: {"added": [...], "removed": [...], "only_mine": bool}"""
    changes = data["lists"].setdefault(key, {})
    changes.setdefault("added", [])
    changes.setdefault("removed", [])
    changes.setdefault("only_mine", False)
    return changes


def apply(names_dict, data):
    """Puts one set of changes on a copy of the name lists and returns it"""
    names_dict = copy.deepcopy(names_dict)
    for key, changes in data.get("lists", {}).items():
        if key not in names_dict or not isinstance(names_dict[key], list):
            continue
        added = [name for name in changes.get("added", []) if name]
        removed = {name.lower() for name in changes.get("removed", [])}
        if changes.get("only_mine"):
            current = list(added)
        else:
            current = [name for name in names_dict[key] if name.lower() not in removed]
            current += [name for name in added if name not in current]
        names_dict[key] = current
    for rank, ending in data.get("rank_endings", {}).items():
        names_dict.setdefault("special_suffixes", {})[rank] = ending
    return names_dict


def combined(base, save=None):
    """The name lists a save uses (save=None: the all-saves lists)"""
    names_dict = apply(base, load())
    if save:
        names_dict = apply(names_dict, load(save))
    # a list that ends up empty would crash name making: keep the game's then
    # (the blocked names can be empty)
    for key, value in names_dict.items():
        if key != "inappropriate_names" and isinstance(value, list) and not value and base.get(key):
            names_dict[key] = list(base[key])
    return names_dict


# how often a cat gets one of your own prefixes or suffixes instead of the game's (Genemod's
# namer mostly names cats after their looks, so your names need a share of their own)
SHARES = {"rarely": 0.1, "sometimes": 0.3, "often": 0.6, "always": 1.0}
DEFAULT_SHARE = "sometimes"


def merged_info(save=None):
    """Per list: your added names, the names taken out, how often yours are used and whether
    only yours are used (all saves, then the save's own on top)"""
    info = {}
    for data in [load()] + ([load(save)] if save else []):
        for key, changes in data.get("lists", {}).items():
            entry = info.setdefault(key, {"added": [], "removed": set(), "share": DEFAULT_SHARE, "only_mine": False})
            added = [name for name in changes.get("added", []) if name]
            entry["added"] += [name for name in added if name not in entry["added"]]
            entry["removed"] |= {name.lower() for name in changes.get("removed", [])}
            # a save can bring back a name taken out for all saves
            entry["removed"] -= {name.lower() for name in added}
            entry["added"] = [name for name in entry["added"] if name.lower() not in entry["removed"]]
            if "share" in changes:
                entry["share"] = changes["share"]
            if "only_mine" in changes:
                entry["only_mine"] = changes["only_mine"]
    return info


def pick(info, key):
    """One of your own names for this list, if it's their turn, or None"""
    from random import choice, random

    entry = info.get(key)
    if not entry or not entry["added"]:
        return None
    chance = 1.0 if entry["only_mine"] else SHARES.get(entry["share"], 0)
    return choice(entry["added"]) if random() < chance else None


def is_removed(info, key, name):
    return bool(name) and name.lower() in info.get(key, {}).get("removed", ())
