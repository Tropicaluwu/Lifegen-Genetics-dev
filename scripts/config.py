import copy
import tomllib
import os

from scripts.game_structure.game.switches import switch_get_value, Switch
from scripts.housekeeping.datadir import get_save_dir
from scripts.game_structure import constants, game

with open("resources/game_config.toml", "r", encoding="utf-8") as read_file:
    CONFIG = tomllib.loads(read_file.read())

    calendar = CONFIG["seasons"]["calendar"]
    season_length = CONFIG["seasons"]["length"]
    constants.SEASON_CALENDAR = []
    for season in calendar:
        constants.SEASON_CALENDAR += [season] * season_length

def recursive_merge(dict1, dict2):
    for key, value in dict2.items():
        if key in dict1 and isinstance(dict1[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            dict1[key] = recursive_merge(dict1[key], value)
        else:
            # Merge non-dictionary values
            dict1[key] = value
    return dict1

# LG: get_config runs hundreds of thousands of times a moon (every age check goes through it), and each call
# deep copied the value and compared the whole CONFIG to itself. values are cached now (per cruel card list)
# and only lists and dicts get copied. the cache is cleared whenever CONFIG changes
_CONFIG_CACHE = {}
# moons -> CatAge, filled by CatAge.get_from_moons and emptied along with the config cache
AGE_CACHE = {}


def clear_config_cache():
    _CONFIG_CACHE.clear()
    AGE_CACHE.clear()


def other_config_refreshes():
    clear_config_cache()
    from scripts.cat.cats import Cat
    from scripts.cat.enums import CatAge
    Cat.age_moons = {
        CatAge.NEWBORN: CONFIG["cat_ages"]["newborn"],
        CatAge.KITTEN: CONFIG["cat_ages"]["kitten"],
        CatAge.ADOLESCENT: CONFIG["cat_ages"]["adolescent"],
        CatAge.YOUNG_ADULT: CONFIG["cat_ages"]["young adult"],
        CatAge.ADULT: CONFIG["cat_ages"]["adult"],
        CatAge.SENIOR_ADULT: CONFIG["cat_ages"]["senior adult"],
        CatAge.SENIOR: CONFIG["cat_ages"]["senior"],
    }

    calendar = CONFIG["seasons"]["calendar"]
    season_length = CONFIG["seasons"]["length"]
    constants.SEASON_CALENDAR = []
    for season in calendar:
        constants.SEASON_CALENDAR += [season] * season_length

def load_clan_config():
    global CONFIG
    reset_config()
    if switch_get_value(Switch.clan_list) and os.path.exists(
        get_save_dir() +
        f"/{switch_get_value(Switch.clan_list)[0]}/game_config.toml"
    ):
        with open(
            get_save_dir()
            + f"/{switch_get_value(Switch.clan_list)[0]}/game_config.toml",
            "r",
            encoding="utf-8",
        ) as read_file:
            config_override = tomllib.loads(read_file.read())
            CONFIG = recursive_merge(CONFIG, config_override)
            other_config_refreshes()

def reset_config():
    global CONFIG
    with open("resources/game_config.toml", "r", encoding="utf-8") as read_file:
        CONFIG = tomllib.loads(read_file.read())
        other_config_refreshes()


def get_config(
    config_path, creating_clan: bool = False, card_list_override: list[str] = None, copy_value: bool = True
):
    """
    Returns a given game config value. If the clan has cruel cards that can replace those values, then it will return the card modifier instead.
    :param config_path: Path to config value in dot notation - ex "graduation.min_graduating_age"
    :param creating_clan: Set to True if currently loaded game.clan.cruel_cards should be ignored.
    :param card_list_override: If you want to specify a list of cruel card IDs to search INSTEAD of using the saved clan cards, then list them here. Best used during clan creation.
    :param copy_value: LG: False hands back the cached list/dict itself, only for callers that never change it
    """
    # checking cards first
    card_list = card_list_override if card_list_override else []
    if game.clan and hasattr(game.clan, "cruel_cards") and not card_list and not creating_clan:
        card_list = game.clan.cruel_cards

    cache_key = (config_path, tuple(card_list))
    if cache_key not in _CONFIG_CACHE:
        _CONFIG_CACHE[cache_key] = _find_config(config_path, card_list)
    config_value = _CONFIG_CACHE[cache_key]
    if copy_value and isinstance(config_value, (dict, list, set)):
        return copy.deepcopy(config_value)
    return config_value


def _find_config(config_path, card_list):
    config_value = CONFIG
    config_keys = tuple(config_path.split("."))

    for card in card_list:
        card_info = constants.CRUEL_CARDS_ALL[card]
        if config_path in card_info["modifiers"]:
            config_value = card_info["modifiers"][config_path]

    # then checking game_config
    if config_value is CONFIG:
        for key in config_keys:
            config_value = config_value[key]
        if isinstance(config_value, dict) and card_list:
            # copy first, so a card's values never end up in the plain game config
            config_value = copy.deepcopy(config_value)
            for value in config_value:
                for card in card_list:
                    card_info = constants.CRUEL_CARDS_ALL[card]
                    if config_path + "." + value in card_info["modifiers"]:
                        config_value[value] = card_info["modifiers"][config_path + "." + value]

    return config_value
