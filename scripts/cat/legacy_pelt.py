"""
Old style (lifegen/clangen) pelt options for the cat customizer.

Genemod builds cats from genes instead of picking a pelt name + colour, so the
customizer on the make clan screen keeps its picks in a LegacyPelt and then
turns them into genes with the same porting code that converts old saves.
"""

from scripts.cat.pelts import Pelt
from scripts.cat.sprites.load_sprites import sprites
from scripts.game_structure.load_cat import accurate_porting


class LegacyPelt:
    # these are copied from lifegen's pelt/eye/skin sprite data, genemod doesnt ship those files anymore
    pelt_length = [
        "short", "medium", "long"
    ]
    all_pelt_colours = [
        "WHITE", "PALEGREY", "SILVER", "GREY", "DARKGREY", "GHOST", "BLACK", "CREAM", "PALEGINGER",
        "GOLDEN", "GINGER", "DARKGINGER", "SIENNA", "LIGHTBROWN", "LILAC", "BROWN", "GOLDEN-BROWN",
        "DARKBROWN", "CHOCOLATE"
    ]
    ginger_colours = [
        "CREAM", "PALEGINGER", "GOLDEN", "GINGER", "DARKGINGER", "SIENNA"
    ]
    black_colours = [
        "GREY", "DARKGREY", "GHOST", "BLACK"
    ]
    white_colours = [
        "WHITE", "PALEGREY", "SILVER"
    ]
    brown_colours = [
        "LIGHTBROWN", "LILAC", "BROWN", "GOLDEN-BROWN", "DARKBROWN", "CHOCOLATE"
    ]
    colour_categories = [ginger_colours, black_colours, white_colours, brown_colours]

    pelt_patterns = ["single", "tabby", "bengal", "marbled", "ticked", "smoke", "rosette", "speckled",
                     "mackerel", "classic", "sokoke", "agouti", "singlestripe", "masked"]
    pelt_categories = {
        "tabbies": ["Tabby", "Ticked", "Mackerel", "Classic", "Sokoke", "Agouti"],
        "spotted": ["Speckled", "Rosette"],
        "plain": ["SingleColour", "TwoColour", "Smoke", "Singlestripe"],
        "exotic": ["Bengal", "Marbled", "Masked"],
        "torties": ["Tortie", "Calico"],
    }
    torties = pelt_categories["torties"]

    tortie_patches = [
        "ONE", "TWO", "THREE", "FOUR", "REDTAIL", "DELILAH", "HALF", "STREAK", "MASK", "SMOKE",
        "MINIMALONE", "MINIMALTWO", "MINIMALTHREE", "MINIMALFOUR", "OREO", "SWOOP", "CHIMERA",
        "CHEST", "ARMTAIL", "GRUMPYFACE", "MOTTLED", "SIDEMASK", "EYEDOT", "BANDANA", "PACMAN",
        "STREAMSTRIKE", "SMUDGED", "DAUB", "EMBER", "BRIE", "ORIOLE", "ROBIN", "BRINDLE", "PAIGE",
        "ROSETAIL", "SAFI", "DAPPLENIGHT", "BLANKET", "BELOVED", "BODY", "SHILOH", "FRECKLED",
        "HEARTBEAT"
    ]
    little_white = [
        "LITTLE", "LIGHTTUXEDO", "BUZZARDFANG", "TIP", "PAWS", "BROKENBLAZE", "SCOURGE", "BLAZE",
        "BIB", "VEE", "HONEY", "BELLY", "TAILTIP", "TOES", "EXTRA", "TOESTAIL", "RAVENPAW",
        "LILTWO", "MUSTACHE", "REVERSEHEART", "SPARKLE", "RIGHTEAR", "LEFTEAR", "ESTRELLA",
        "REVERSEEYE", "BACKSPOT", "EYEBAGS", "LOCKET", "BLAZEMASK", "TEARS", "LUNA"
    ]
    mid_white = [
        "TUXEDO", "SAVANNAH", "FADESPOTS", "FANCY", "MITAINE", "DIVA", "BEARD", "UNDERS", "DAMIEN",
        "TOPCOVER", "SQUEAKS", "STAR", "SKUNK", "DAPPLEPAW", "WINGS", "WOODPECKER", "MISS",
        "BOWTIE", "VEST", "DIGIT", "FCTWO", "FCONE", "MIA", "FADEBELLY", "ROSINA", "PRINCESS",
        "DOUGIE"
    ]
    high_white = [
        "ANY", "ANYTWO", "BROKEN", "PIEBALD", "CURVED", "SHIBAINU", "OWL", "FRECKLES", "RINGTAIL",
        "HALFFACE", "PANTSTWO", "GOATEE", "PRINCE", "FAROFA", "MISTER", "MASKMANTLE", "PANTS",
        "REVERSEPANTS", "HALFWHITE", "APPALOOSA", "GLASS", "MAO", "PAINTED", "BUB", "SPARROW",
        "TRIXIE", "SAMMY", "FRONT", "BLOSSOMSTEP", "BULLSEYE", "FINN", "SCAR", "BUSTER",
        "HAWKBLAZE", "CAKE"
    ]
    mostly_white = [
        "VAN", "PEBBLESHINE", "ONEEAR", "LIGHTSONG", "BLACKSTAR", "PETAL", "TAIL", "APRON",
        "CAPSADDLE", "HEART", "MOORISH", "CHESTSPECK", "HEARTTWO", "BOOTS", "COW", "COWTWO",
        "LOVEBUG", "SHOOTINGSTAR", "EYESPOT", "PEBBLE", "TAILTWO", "BUDDY", "KROPKA"
    ]
    vitiligo_markings = [
        "MOON", "PHANTOM", "POWDER", "BLEACHED", "VITILIGO", "VITILIGOTWO", "KARPATI", "SMOKEY"
    ]
    point_markings = [
        "COLOURPOINT", "RAGDOLL", "SEPIAPOINT", "MINKPOINT", "SEALPOINT"
    ]
    all_eye_colours = [
        "YELLOW", "AMBER", "HAZEL", "PALEGREEN", "GREEN", "BLUE", "DARKBLUE", "GREY", "CYAN",
        "EMERALD", "HEATHERBLUE", "SUNLITICE", "COPPER", "SAGE", "COBALT", "PALEBLUE", "BRONZE",
        "SILVER", "PALEYELLOW", "GOLD", "GREENYELLOW", "ORANGE"
    ]
    yellow_eyes = [
        "YELLOW", "AMBER", "COPPER", "BRONZE", "SILVER", "PALEYELLOW", "GOLD", "GREENYELLOW",
        "ORANGE"
    ]
    green_eyes = [
        "HAZEL", "PALEGREEN", "GREEN", "EMERALD", "SAGE"
    ]
    blue_eyes = [
        "BLUE", "DARKBLUE", "GREY", "CYAN", "HEATHERBLUE", "SUNLITICE", "COBALT", "PALEBLUE"
    ]
    skin_sprites = [
        "BLACK", "RED", "PINK", "DARKBROWN", "BROWN", "LIGHTBROWN", "DARK", "DARKGREY", "GREY",
        "DARKSALMON", "SALMON", "PEACH", "DARKMARBLED", "MARBLED", "LIGHTMARBLED", "DARKBLUE",
        "BLUE", "LIGHTBLUE"
    ]
    general_scars = [
        "ONE", "TWO", "THREE", "MANLEG", "BRIGHTHEART", "MANTAIL", "BRIDGE", "RIGHTBLIND",
        "LEFTBLIND", "BOTHBLIND", "BURNPAWS", "BURNTAIL", "BURNBELLY", "BEAKCHEEK", "BEAKLOWER",
        "BURNRUMP", "CATBITE", "RATBITE", "FROSTFACE", "FROSTTAIL", "FROSTMITT", "FROSTSOCK",
        "QUILLCHUNK", "QUILLSCRATCH", "TAILSCAR", "SNOUT", "CHEEK", "SIDE", "THROAT", "TAILBASE",
        "BELLY", "TOETRAP", "SNAKE", "LEGBITE", "NECKBITE", "FACE", "HINDLEG", "BACK", "QUILLSIDE",
        "SCRATCHSIDE", "TOE", "BEAKSIDE", "CATBITETWO", "SNAKETWO", "FOUR"
    ]
    missing_part_scars = [
        "LEFTEAR", "RIGHTEAR", "NOTAIL", "NOLEFTEAR", "NORIGHTEAR", "NOEAR", "HALFTAIL", "NOPAW"
    ]
    all_scars = general_scars + missing_part_scars

    pattern_sprite_names: dict = {}

    def __init__(
        self,
        name: str = "SingleColour",
        length: str = "short",
        colour: str = "WHITE",
        white_patches: str = None,
        eye_color: str = "BLUE",
        eye_colour2: str = None,
        tortie_base: str = None,
        tortie_colour: str = None,
        tortie_marking: str = None,
        tortie_pattern: str = None,
        vitiligo: str = None,
        points: str = None,
        accessory: list = None,
        inventory: list = None,
        paralyzed: bool = False,
        opacity: int = 100,
        scars: list = None,
        tint: str = "none",
        skin: str = "BLACK",
        white_patches_tint: str = "none",
        newborn_sprite: str = None,
        kitten_sprite: str = None,
        adol_sprite: str = None,
        adult_sprite: str = None,
        senior_sprite: str = None,
        para_adult_sprite: str = None,
        reverse: bool = False,
    ):
        self.name = name
        self.length = length
        self.colour = colour
        self.white_patches = white_patches
        self.eye_colour = eye_color
        self.eye_colour2 = eye_colour2
        self.tortie_base = tortie_base
        self.tortie_colour = tortie_colour
        self.tortie_marking = tortie_marking
        self.tortie_pattern = tortie_pattern
        self.vitiligo = vitiligo
        self.points = points
        self.accessory = list(accessory) if accessory else []
        self.inventory = list(inventory) if inventory else list(self.accessory)
        self.paralyzed = paralyzed
        self.opacity = opacity
        self.scars = list(scars) if scars else []
        self.tint = tint or "none"
        self.skin = skin
        self.white_patches_tint = white_patches_tint or "none"
        self.reverse = reverse
        self.sprites = {
            "newborn": newborn_sprite,
            "kitten": kitten_sprite,
            "adolescent": adol_sprite,
            "adult": adult_sprite,
            "senior": senior_sprite,
            "para_adult": para_adult_sprite,
        }

    # names of the __init__ arguments, in the order they're saved
    SAVE_FIELDS = [
        "name", "length", "colour", "white_patches", "eye_color", "eye_colour2", "tortie_base",
        "tortie_colour", "tortie_marking", "tortie_pattern", "vitiligo", "points", "accessory",
        "inventory", "paralyzed", "opacity", "scars", "tint", "skin", "white_patches_tint", "reverse",
    ]

    def to_dict(self) -> dict:
        """the customizer picks, saved with the cat so editing again starts from them"""
        out = {}
        for field in self.SAVE_FIELDS:
            value = self.eye_colour if field == "eye_color" else getattr(self, field)
            out[field] = list(value) if isinstance(value, tuple) else value
        out["sprites"] = dict(self.sprites)
        return out

    @classmethod
    def from_dict(cls, data: dict):
        data = dict(data)
        sprite_names = data.pop("sprites", {}) or {}
        pelt = cls(**{k: v for k, v in data.items() if k in cls.SAVE_FIELDS})
        pelt.sprites.update(sprite_names)
        return pelt

    def copy(self):
        return LegacyPelt.from_dict(self.to_dict())

    def port_info(self) -> dict:
        """the old save keys that accurate_porting reads"""
        return {
            "pelt_name": self.name,
            "pelt_color": self.colour,
            "pelt_length": self.length,
            "white_patches": self.white_patches,
            "eye_colour": self.eye_colour,
            "eye_colour2": self.eye_colour2,
            "tortie_base": self.tortie_base,
            "tortie_color": self.tortie_colour,
            "tortie_marking": self.tortie_marking,
            "tortie_pattern": self.tortie_pattern,
            "vitiligo": self.vitiligo,
            "points": self.points,
        }

    def apply_to_cat(self, cat):
        """
        Gives the cat genes that match this pelt and a fresh genemod pelt.
        Same thing that happens to cats from a normal lifegen save on first load.
        """
        accurate_porting(cat, self.port_info())
        cat.pelt = Pelt(
            cat.phenotype,
            accessory=list(self.accessory),
            inventory=list(self.inventory),
            paralyzed=self.paralyzed,
            opacity=self.opacity,
            scars=list(self.scars),
            tint=self.tint,
            white_patches_tint=self.white_patches_tint,
            newborn_sprite=self.sprites["newborn"],
            kitten_sprite=self.sprites["kitten"],
            adol_sprite=self.sprites["adolescent"],
            adult_sprite=self.sprites["adult"],
            senior_sprite=self.sprites["senior"],
            para_adult_sprite=self.sprites["para_adult"],
            reverse=self.reverse,
        )
        cat.legacy_pelt = self
        cat.pelt.rebuild_sprite = True
        return cat.pelt
