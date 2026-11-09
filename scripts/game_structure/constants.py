from pygame import Cursor, image, SYSTEM_CURSOR_ARROW
import ujson
import tomllib

# these scripts don't import any clangen scripts into themselves, so it's okay for them to be imported here
from scripts.clan_resources.supply import Supply

from scripts.screens.enums import GameScreen

# this is just to make referencing main menu screens as a whole easier,
# note that the clan creation screen is included and the clan settings screen is excluded. this is intended.
MENU_SCREENS = [
    GameScreen.SETTINGS,
    GameScreen.START,
    GameScreen.SWITCH_CLAN,
    GameScreen.MAKE_CLAN_CHOOSE_CLANCOUNT,
    GameScreen.MAKE_CLAN_CHOOSE_MODE,
    GameScreen.MAKE_CLAN_CHOOSE_CARDS,
    GameScreen.MAKE_CLAN_CHOOSE_NAME,
    GameScreen.MAKE_CLAN_CHOOSE_CATS,
    GameScreen.MAKE_CLAN_CHOOSE_CAMP,
    GameScreen.MAKE_CLAN_CHOOSE_SYMBOL,
    GameScreen.MAKE_CLAN_CLAN_CREATED,
    # LG: without these the music changes when you open them
    GameScreen.MAKE_CLAN_CUSTOM_CAT,
    GameScreen.MAKE_CLAN_YOUR_NAME,
]
# whatever is playing keeps playing on these, they open from the menus and from inside a Clan
KEEP_MUSIC_SCREENS = [GameScreen.MAKE_CLAN_CUSTOM_CAT, GameScreen.MAKE_CLAN_YOUR_NAME]

EVENTS_PER_PAGE = 10

BIOME_TYPES = ["Forest", "Plains", "Mountainous", "Beach", "Wetlands", "Desert"]

CAMPS: dict = {
    "Forest": ["Classic", "Gully", "Grotto", "Lakeside", "Pine", "Birch"],
    "Mountainous": [
        "Cliff",
        "Cavern",
        "Crystal River",
        "Rocky Slope",
        "Quarry",
        "Ruins",
    ],
    "Plains": [
        "Grasslands",
        "Tunnels",
        "Wastelands",
        "Taiga",
        "Desert",
        "City",
        "Farm",
        "Bushland",
        "Castle",
        "Bridge",
    ],
    "Beach": [
        "Tidepools",
        "Tidal Cave",
        "Shipwreck",
        "Fjord",
        "Tropical_Island",
        "Quay",
    ],
}

SEASONS = ["Newleaf", "Greenleaf", "Leaf-fall", "Leaf-bare"]
SEASON_CALENDAR = [
    "Newleaf",
    "Newleaf",
    "Newleaf",
    "Greenleaf",
    "Greenleaf",
    "Greenleaf",
    "Leaf-fall",
    "Leaf-fall",
    "Leaf-fall",
    "Leaf-bare",
    "Leaf-bare",
    "Leaf-bare",
]

TEMPERAMENT_DICTS = [
    {
        "low_social": ["cunning", "proud", "bloodthirsty"],
        "mid_social": ["amiable", "stoic", "wary"],
        "high_social": ["gracious", "mellow", "logical"],
    },
    {
        "low_lawful": ["chaotic", "mercurial", "calculating"],
        "mid_lawful": ["eager", "observant", "adaptable"],
        "high_lawful": ["decisive", "methodical", "steadfast"],
    },
]

facet_types = ["lawfulness", "sociability", "aggression", "stability"]
facet_range = [0, 16]

OUTSIDER_REPS = ("welcoming", "neutral", "hostile")
OTHER_CLAN_REPS = ("ally", "neutral", "hostile")

HERBS: dict = {}
with open("resources/dicts/herb_info.json", "r", encoding="utf-8") as read_file:
    HERBS.update(ujson.loads(read_file.read()))

SUPPLY_TYPES = ["fresh_kill", "all_herb", "any_herb"]

SUPPLY_TYPES.extend(HERBS)

SUPPLY_TRIGGERS = ["always", *Supply]

SUPPLY_ADJUSTMENTS = [
    "reduce_eighth",
    "reduce_quarter",
    "reduce_half",
    "reduce_full",
    "increase_#",
]

CRUEL_CARDS_ALL: dict = {}
with open(
    "resources/dicts/cruel_season/origin_cards.json", "r", encoding="utf-8"
) as read_file:
    CRUEL_CARDS_ORIGIN: dict = ujson.loads(read_file.read())
CRUEL_CARDS_ALL.update(CRUEL_CARDS_ORIGIN)

with open(
    "resources/dicts/cruel_season/behavior_cards.json", "r", encoding="utf-8"
) as read_file:
    CRUEL_CARDS_BEHAVIOR: dict = ujson.loads(read_file.read())
CRUEL_CARDS_ALL.update(CRUEL_CARDS_BEHAVIOR)

with open(
    "resources/dicts/cruel_season/society_cards.json", "r", encoding="utf-8"
) as read_file:
    CRUEL_CARDS_SOCIETY: dict = ujson.loads(read_file.read())
CRUEL_CARDS_ALL.update(CRUEL_CARDS_SOCIETY)

with open(
    "resources/dicts/cruel_season/danger_cards.json", "r", encoding="utf-8"
) as read_file:
    CRUEL_CARDS_DANGER: dict = ujson.loads(read_file.read())
CRUEL_CARDS_ALL.update(CRUEL_CARDS_DANGER)

with open(
    "resources/dicts/cruel_season/environment_cards.json", "r", encoding="utf-8"
) as read_file:
    CRUEL_CARDS_ENVIRONMENT: dict = ujson.loads(read_file.read())
CRUEL_CARDS_ALL.update(CRUEL_CARDS_ENVIRONMENT)


with open(
    "resources/dicts/cruel_season/card_conflicts.json", "r", encoding="utf-8"
) as read_file:
    CRUEL_CARDS_CONFLICTS: dict = ujson.loads(read_file.read())

with open("resources/display_settings.toml", "r", encoding="utf-8") as read_file:
    DISPLAY_SETTINGS = tomllib.loads(read_file.read())

with open("resources/placements.json", "r", encoding="utf-8") as read_file:
    LAYOUTS = ujson.loads(read_file.read())

CUSTOM_CURSOR = Cursor((9, 0), image.load("resources/images/cursor.png"))
DEFAULT_CURSOR = Cursor(SYSTEM_CURSOR_ARROW)


def __getattr__(name):
    # LG: lifegen code still reads constants.CONFIG, the config now lives in scripts.config
    # (looked up every time since a clan's own game_config.toml can replace it)
    if name == "CONFIG":
        from scripts import config

        return config.CONFIG
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
