"""the gene menus of the custom cat maker (from the LifeGen Genetics Cat Maker). Each
menu sets the genes that make that look, and reads the current choice back from the genes, so the
menus and the genes never disagree.

Menus are grouped into tabs (see TABS at the bottom). SHORT has shorter names for the lists."""

import json
import os
from collections import namedtuple


OTHER = "(other)"

# label: shown above the menu. read/write: get the current choice and set a new one.
# on: "genes" menus get the genes, "state" menus get the whole cat (for things that aren't genes).
# multi: pick any number of options (read and write a list). reset: a multi menu's "let the genes
# decide" choice (written as None).
Menu = namedtuple("Menu", "label options read write on multi reset", defaults=("genes", False, None))

# Genemod's eye color names: row = refraction grade 1-11, column = pigmentation grade 1-11,
# then the blue column (12) and the albino column (13). Same table as Genotype.EyeColourFinder.
EYE_COLORS = [
    ["Citrine", "Golden Beryl", "Yellow", "Pale Golden", "Golden", "Amber", "Light Orange", "Orange", "Cinnabar", "Auburn", "Copper", "Ice Blue", "Pink"],
    ["Pale Citrine", "Pale Yellow", "Lemon", "Deep Yellow", "Dull Golden", "Honey", "Pale Orange", "Burnt Orange", "Dark Orange", "Russet", "Dark Topaz", "Aquamarine", "Rose"],
    ["Lemonade Yellow", "Straw Yellow", "Dandelion Yellow", "Banana Yellow", "Sunglow Yellow", "Copal", "Dull Orange", "Rust Orange", "Topaz", "Chocolate", "Burgundy", "Sky Blue", "Magenta"],
    ["Light Celadon", "Pale Chartreuse", "Pear Green", "Brass Yellow", "Golden Green", "Butterscotch", "Dusty Orange", "Tawny", "Jasper", "Light Brown", "Earth", "Cyan", "Periwinkle"],
    ["Light Jade", "Pale Lime", "Spring Bud", "Chartreuse", "Pale Hazel", "Yellow Hazel", "Golden Fluorite", "Beaver Brown", "Sienna", "Chestnut", "Umber", "Baby Blue", "Violet"],
    ["Light Fluorite", "Mantis Green", "Spring Green", "Lime", "Green Tea", "Hazel", "Green Hazel", "Dark Copal", "Cinnamon", "Raw Umber", "Sepia", "Aqua", "Glass"],
    ["Pale Emerald", "Apple Green", "Shamrock", "Lemon-Lime", "Peridot", "Antique Brass", "Dark Hazel", "Brown-Green", "Hazel Brown", "Bronze", "Bistre Brown", "Cerulean", "Moonstone"],
    ["Malachite", "Olivine", "Pastel Green", "Bright Green", "Pistachio", "Dull Olive", "Murky Green", "Jungle Green", "Hemlock Green", "Thatch Green", "Muddy", "Ocean Blue", "Albino Ice Blue"],
    ["Pale Turquoise", "Mint", "Snake Green", "Dark Lime", "Fern Green", "Dull Green", "Dark Fern Green", "Olive", "Tumbleweed Green", "Bronze Olive", "Deep Bronze", "Teal", "Albino Aquamarine"],
    ["Turquoise", "Viridian", "Green Onion", "Leaf Green", "Green", "Sap Green", "Dark Leaf Green", "Forest Green", "Dark Peridot", "Seaweed Green", "Dark Olive", "Sapphire", "Albino Sky Blue"],
    ["Deep Turquoise", "Amazonite", "Pine Green", "Deep Leaf Green", "Jade", "Emerald", "Deep Green", "Deep Forest Green", "Dark Green", "Dark Moss Green", "Black Olive", "Azure", "Albino Azure"],
]

# dominance order for genes where one copy hides another (first = most dominant)
ORDER = {
    "eumelanin": ["B", "b", "bl"],
    "dilute": ["D", "d"],
    "pinkdilute": ["Dp", "dp"],
    "dilutemd": ["Dm", "dm"],
    "agouti": ["A", "Apb", "a"],
    "mack": ["Mc", "mc"],
    "ticked": ["Ta", "ta"],
    "silver": ["I", "i"],
    "ext": ["Eg", "E", "ea", "er", "ec"],
    "corin": ["N", "sg", "sh", "fg"],
    "furLength": ["L", "l"],
}


def express(genes, gene, allele):
    """Makes `allele` the one that shows, keeping the hidden copy when it can stay hidden"""
    order = ORDER[gene]
    pair = genes[gene]
    other = pair[1] if pair[0] == allele else pair[0]
    if other in order and order.index(other) >= order.index(allele):
        setattr(genes, gene, [allele, other])
    else:
        setattr(genes, gene, [allele, allele])


def shown(genes, gene):
    """The copy that shows (the most dominant one)"""
    order = ORDER[gene]
    return min(genes[gene], key=lambda a: order.index(a) if a in order else len(order))


def set_poly_sum(genes, gene, total):
    """Polygenes are strings of 0-2 per spot; spread `total` over the spots"""
    spots = len(genes[gene])
    total = max(0, min(total, spots * 2))
    base, extra = divmod(total, spots)
    setattr(genes, gene, "".join(str(base + (1 if i < extra else 0)) for i in range(spots)))


def poly_sum(genes, gene):
    return sum(int(d) for d in genes[gene])


def x_genes(genes):
    return [a for a in genes.sexgene if a != "Y"]


def set_x_genes(genes, xs):
    if "Y" in genes.sexgene:
        genes.sexgene = xs + ["Y"]
    else:
        genes.sexgene = xs


def gene_menu(gene, yes, no, dominant):
    """A No/Yes menu for one gene. A dominant gene shows with one copy, a recessive one needs two."""

    def read(genes):
        copies = genes[gene].count(yes)
        return "Yes" if copies >= (1 if dominant else 2) else "No"

    def write(genes, value):
        if value == "No":
            setattr(genes, gene, [no, no])
        else:
            setattr(genes, gene, [yes, no] if dominant else [yes, yes])

    return ["No", "Yes"], read, write


def flag_menu(attr, yes=True, no=False):
    """A No/Yes menu for a single setting"""

    def read(genes):
        return "Yes" if getattr(genes, attr) == yes else "No"

    def write(genes, value):
        setattr(genes, attr, yes if value == "Yes" else no)

    return ["No", "Yes"], read, write


def level_menu(gene, levels):
    """A menu for a polygene by how much of it there is. levels: name -> (lowest total, total to set)"""

    def read(genes):
        total = poly_sum(genes, gene)
        found = OTHER
        for name, (lowest, _) in levels.items():
            if total >= lowest:
                found = name
        return found

    def write(genes, value):
        set_poly_sum(genes, gene, levels[value][1])

    return list(levels), read, write


# --- color ------------------------------------------------------------------------------------

def get_sex(genes):
    if genes.sex == "intersex":
        return "Intersex"
    return "Tom" if "Y" in genes.sexgene else "Molly"


def set_sex(genes, value):
    xs = x_genes(genes) or ["o"]
    if value == "Intersex":
        genes.sex = "intersex"
    elif value == "Tom":
        if "Y" not in genes.sexgene:
            # a tortie tom keeps both X genes (XXY), like real tortie toms
            genes.sexgene = (xs if len(set(xs)) > 1 else xs[:1]) + ["Y"]
        genes.sex = "tom"
    else:
        if "Y" in genes.sexgene:
            genes.sexgene = xs if len(xs) >= 2 else xs[:1] * 2
        genes.sex = "molly"


# name: (number of X, Y or not)
CHROMOSOMES = {"XX": (2, False), "XY": (1, True), "XXY": (2, True), "X (one X)": (1, False), "XXX": (3, False)}


def get_chromosomes(genes):
    xs = x_genes(genes)
    for name, (count, y) in CHROMOSOMES.items():
        if len(xs) == count and ("Y" in genes.sexgene) == y:
            return name
    return OTHER


def set_chromosomes(genes, value):
    count, y = CHROMOSOMES[value]
    xs = x_genes(genes) or ["o"]
    # keep the X genes there are (so a tortie stays tortie when it can)
    xs = (xs * 3)[:count] if len(xs) < count else xs[:count]
    if count >= 2 and "O" in x_genes(genes) and "o" in x_genes(genes):
        xs = ["O", "o"] + xs[2:]
    genes.sexgene = xs + (["Y"] if y else [])
    if genes.sex != "intersex":
        genes.sex = "tom" if y else "molly"


# (black-based color, dilute, pink-eyed dilute): name
EUMELANIN_COLORS = {
    ("B", "D", "Dp"): "Black", ("b", "D", "Dp"): "Chocolate", ("bl", "D", "Dp"): "Cinnamon",
    ("B", "d", "Dp"): "Blue", ("b", "d", "Dp"): "Lilac", ("bl", "d", "Dp"): "Fawn",
    ("B", "D", "dp"): "Dove", ("b", "D", "dp"): "Champagne", ("bl", "D", "dp"): "Buff",
    ("B", "d", "dp"): "Platinum", ("b", "d", "dp"): "Lavender", ("bl", "d", "dp"): "Beige",
}
# (dilute, pink-eyed dilute): name
RED_COLORS = {("D", "Dp"): "Red", ("d", "Dp"): "Cream", ("D", "dp"): "Honey", ("d", "dp"): "Ivory"}
COLORS = ["Black", "Chocolate", "Cinnamon", "Blue", "Lilac", "Fawn", "Red", "Cream",
          "Dove", "Champagne", "Buff", "Platinum", "Lavender", "Beige", "Honey", "Ivory"]


def get_color(genes):
    dilute, pink = shown(genes, "dilute"), shown(genes, "pinkdilute")
    if "o" not in genes.sexgene:
        return RED_COLORS.get((dilute, pink), OTHER)
    return EUMELANIN_COLORS.get((shown(genes, "eumelanin"), dilute, pink), OTHER)


def set_color(genes, value):
    xs = x_genes(genes)
    for (dilute, pink), name in RED_COLORS.items():
        if name == value:
            set_x_genes(genes, ["O"] * len(xs))
            express(genes, "dilute", dilute)
            express(genes, "pinkdilute", pink)
            return
    if "o" not in xs:
        # was red-based, now black-based (not tortie)
        set_x_genes(genes, ["o"] * len(xs))
    for (eum, dilute, pink), name in EUMELANIN_COLORS.items():
        if name == value:
            express(genes, "eumelanin", eum)
            express(genes, "dilute", dilute)
            express(genes, "pinkdilute", pink)


TORTIE = ["No", "Tortie", "Brindled bicolor"]


def get_tortie(genes):
    xs = x_genes(genes)
    if "O" in xs and "o" in xs:
        return "Brindled bicolor" if genes.brindledbi else "Tortie"
    return "No"


def set_tortie(genes, value):
    if value == "No":
        # red stays red, everything else loses the red patches
        keep = "O" if get_color(genes) in RED_COLORS.values() else "o"
        set_x_genes(genes, [keep] * (2 if "Y" not in genes.sexgene else 1))
        genes.brindledbi = False
        return
    set_x_genes(genes, ["O", "o"])
    if "Y" not in genes.sexgene:
        genes.sex = "molly"
    genes.brindledbi = value == "Brindled bicolor"


def get_caramel(genes):
    return "Yes" if shown(genes, "dilutemd") == "Dm" else "No"


def set_caramel(genes, value):
    express(genes, "dilutemd", "Dm" if value == "Yes" else "dm")


POINTS = ["Full color", "Sepia", "Mink", "Burmocha", "Colorpoint", "Siamocha", "Mocha", "Albino"]
POINT_PAIRS = {
    "Full color": ["C", "C"], "Sepia": ["cb", "cb"], "Mink": ["cb", "cs"], "Burmocha": ["cb", "cm"],
    "Colorpoint": ["cs", "cs"], "Siamocha": ["cs", "cm"], "Mocha": ["cm", "cm"], "Albino": ["c", "c"],
}


def get_points(genes):
    # read like Genemod's PointFinder: the top copy, and what it's paired with
    top, other = genes.pointgene[0], genes.pointgene[1]
    if top == "C":
        return "Full color"
    if top == "cb":
        return {"cs": "Mink", "cm": "Burmocha"}.get(other, "Sepia")
    if top == "cs":
        return "Siamocha" if other == "cm" else "Colorpoint"
    return "Mocha" if top == "cm" else "Albino"


def set_points(genes, value):
    genes.pointgene = list(POINT_PAIRS[value])


EXTENSION = {"Normal": "E", "Grizzled": "Eg", "Amber": "ea", "Russet": "er", "Carnelian": "ec"}


def get_extension(genes):
    found = shown(genes, "ext")
    for name, allele in EXTENSION.items():
        if allele == found:
            return name
    return OTHER


def set_extension(genes, value):
    allele = EXTENSION[value]
    if value == "Grizzled":
        genes.ext = ["Eg", "E"]
    elif value == "Normal":
        express(genes, "ext", "E")
    else:
        genes.ext = [allele, allele]


SUNSHINE = {"None": "N", "Sunshine": "sh", "Extreme sunshine": "sg", "Flaxen gold": "fg"}


def get_sunshine(genes):
    found = shown(genes, "corin")
    for name, allele in SUNSHINE.items():
        if allele == found:
            return name
    return OTHER


def set_sunshine(genes, value):
    allele = SUNSHINE[value]
    genes.corin = ["N", "N"] if value == "None" else [allele, allele]


SPECIAL_RED = {"None": None, "Cameo": "cameo", "Blue-red": "blue-red", "Blue-tipped": "blue-tipped",
               "Pseudo-cinnamon": "cinnamon"}


def get_special_red(genes):
    for name, value in SPECIAL_RED.items():
        if genes.specialred == value:
            return name
    return OTHER


def set_special_red(genes, value):
    genes.specialred = SPECIAL_RED[value]


NOSE = ["Normal", "Red nose", "Black nose"]


def get_nose(genes):
    if genes.blacknose:
        return "Black nose"
    return "Red nose" if genes.rednose else "Normal"


def set_nose(genes, value):
    genes.rednose = value == "Red nose"
    genes.blacknose = value == "Black nose"


SATURATION = [f"Saturation {n}" for n in range(7)]


def get_saturation(genes):
    return f"Saturation {genes.saturation}" if 0 <= genes.saturation <= 6 else OTHER


def set_saturation(genes, value):
    genes.saturation = int(value.split()[-1])


# --- pattern and shading ----------------------------------------------------------------------

# Every tabby pattern Genemod draws (see Phenotype.GetTabbySprite and TabbyFinder).
# name: what makes it
#   ticked: the ticked genes, breakthrough: stripes breaking through ticking (pinstripe family)
#   mack: "Mc" mackerel or "mc" classic, spots/bengal/sokoke/ticks: polygene totals
PATTERNS = {
    "Solid": None,
    "Mackerel": dict(ticked=["ta", "ta"], mack="Mc", spots=1),
    "Broken mackerel": dict(ticked=["ta", "ta"], mack="Mc", spots=4),
    "Spotted": dict(ticked=["ta", "ta"], mack="Mc", spots=7),
    "Braided": dict(ticked=["ta", "ta"], mack="Mc", spots=1, bengal=6),
    "Broken braided": dict(ticked=["ta", "ta"], mack="Mc", spots=4, bengal=6),
    "Partly rosetted": dict(ticked=["ta", "ta"], mack="Mc", spots=7, bengal=4),
    "Rosetted": dict(ticked=["ta", "ta"], mack="Mc", spots=7, bengal=6),
    "Classic": dict(ticked=["ta", "ta"], mack="mc"),
    "Marbled": dict(ticked=["ta", "ta"], mack="mc", bengal=6),
    "Sokoke": dict(ticked=["ta", "ta"], mack="mc", sokoke=7),
    "Sheeted": dict(ticked=["ta", "ta"], mack="mc", sheeted=True),
    "Ticked": dict(ticked=["Ta", "Ta"], ticks=2),
    "Reduced barring ticked": dict(ticked=["Ta", "Ta"], ticks=5),
    "Agouti ticked": dict(ticked=["Ta", "Ta"], ticks=8),
    "Pinstripe": dict(ticked=["Ta", "ta"], mack="Mc", breakthrough=True, spots=1),
    "Broken pinstripe": dict(ticked=["Ta", "ta"], mack="Mc", breakthrough=True, spots=4),
    "Servaline": dict(ticked=["Ta", "ta"], mack="Mc", breakthrough=True, spots=7),
    "Braided pinstripe": dict(ticked=["Ta", "ta"], mack="Mc", breakthrough=True, spots=1, bengal=6),
    "Broken braided pinstripe": dict(ticked=["Ta", "ta"], mack="Mc", breakthrough=True, spots=4, bengal=6),
    "Servaline-rosetted": dict(ticked=["Ta", "ta"], mack="Mc", breakthrough=True, spots=7, bengal=6),
    "Shaded": dict(ticked=["Ta", "Ta"], wideband=12),
    "Chinchilla": dict(ticked=["Ta", "Ta"], wideband=15),
}


def get_pattern(genes):
    if shown(genes, "agouti") == "a":
        return "Solid"
    wb = poly_sum(genes, "wideband")
    spots = poly_sum(genes, "spotted")
    bengal = poly_sum(genes, "bengal")
    if wb > 13:
        return "Chinchilla"
    if genes.ticked[1] == "Ta" or (not genes.breakthrough and genes.ticked[0] == "Ta"):
        if wb > 11:
            return "Shaded"
        ticks = poly_sum(genes, "tickgenes")
        return "Agouti ticked" if ticks >= 6 else "Reduced barring ticked" if ticks >= 4 else "Ticked"
    if genes.ticked[0] == "Ta":
        if bengal < 4:
            return "Broken pinstripe" if spots == 4 else "Pinstripe" if spots < 6 else "Servaline"
        return "Broken braided pinstripe" if spots == 4 else "Braided pinstripe" if spots < 6 else "Servaline-rosetted"
    if shown(genes, "mack") == "mc":
        if genes.sheeted:
            return "Sheeted"
        if bengal > 3:
            return "Marbled"
        if poly_sum(genes, "sokoke") > 5:
            return "Sokoke"
        return "Classic"
    if bengal < 4:
        return "Mackerel" if spots < 3 else "Broken mackerel" if spots < 6 else "Spotted"
    if spots < 3:
        return "Braided"
    if spots < 6:
        return "Broken braided"
    return "Partly rosetted" if bengal < 6 else "Rosetted"


def set_pattern(genes, value):
    recipe = PATTERNS[value]
    if recipe is None:
        genes.agouti = ["a", "a"]
        return
    if shown(genes, "agouti") == "a":
        express(genes, "agouti", "A")
    genes.ticked = list(recipe["ticked"])
    genes.breakthrough = recipe.get("breakthrough", False)
    genes.sheeted = recipe.get("sheeted", False)
    if "mack" in recipe:
        if recipe["mack"] == "mc":
            genes.mack = ["mc", "mc"]
        else:
            express(genes, "mack", "Mc")
    if "spots" in recipe:
        set_poly_sum(genes, "spotted", recipe["spots"])
    if "ticks" in recipe:
        set_poly_sum(genes, "tickgenes", recipe["ticks"])
    # the bengal and sokoke look only where the pattern asks for it
    set_poly_sum(genes, "bengal", recipe.get("bengal", min(poly_sum(genes, "bengal"), 3)))
    set_poly_sum(genes, "sokoke", recipe.get("sokoke", min(poly_sum(genes, "sokoke"), 5)))
    wb = poly_sum(genes, "wideband")
    if "wideband" in recipe:
        set_poly_sum(genes, "wideband", recipe["wideband"])
    elif wb > 13 or (wb > 11 and genes.ticked == ["Ta", "Ta"]):
        # that much wideband would make it chinchilla or shaded
        set_poly_sum(genes, "wideband", 11 if genes.ticked[0] == "ta" else 9)


TABBY_TYPES = ["Normal", "Charcoal", "Twilight"]


def get_tabby_type(genes):
    if genes.agouti == ["Apb", "Apb"]:
        return "Twilight"
    if shown(genes, "agouti") == "Apb":
        return "Charcoal"
    return "Normal"


def set_tabby_type(genes, value):
    # charcoal hides under normal tabby but shows over solid, so a charcoal cat carries solid
    if value == "Twilight":
        genes.agouti = ["Apb", "Apb"]
    elif value == "Charcoal":
        genes.agouti = ["Apb", "a"]
    elif shown(genes, "agouti") == "Apb":
        genes.agouti = ["A", "A"]


def get_silver(genes):
    return "Yes" if shown(genes, "silver") == "I" else "No"


def set_silver(genes, value):
    express(genes, "silver", "I" if value == "Yes" else "i")


# wideband: how far the light band on each hair goes. A lot of it makes golden, shaded and chinchilla
WIDEBAND = {"Low": (0, 3), "Medium": (6, 8), "High": (10, 11), "Very high (golden or shaded)": (12, 12),
            "Highest (chinchilla)": (14, 15)}
RUFOUSING = {"Low": (0, 1), "Medium": (3, 4), "High": (6, 7)}


def get_bleaching(genes):
    return "Yes" if genes.bleach[0] == "lb" else "No"


def set_bleaching(genes, value):
    genes.bleach = ["lb", "lb"] if value == "Yes" else ["Lb", "Lb"]


def get_ghosting(genes):
    return "Yes" if genes.ghosting[0] == "Gh" else "No"


def set_ghosting(genes, value):
    genes.ghosting = ["Gh", "gh"] if value == "Yes" else ["gh", "gh"]


PANGERE = {"None": None, "Small 1": "pangere small 1", "Small 2": "pangere small 2",
           "Medium 1": "pangere medium 1", "Medium 2": "pangere medium 2",
           "Medium 1 and tail": "pangere medium 1 + tail"}


def get_pangere(genes):
    for name, value in PANGERE.items():
        if genes.pangere == value:
            return name
    return OTHER


def set_pangere(genes, value):
    genes.pangere = PANGERE[value]


# --- white ------------------------------------------------------------------------------------

# White spotting: low white is one copy of ws, high white two. Each has 5 grades, and the
# grade picks which of Genemod's white patches can show (see Pelt.generate_white).
# name: (white genes, white grade)
WHITE = {
    "None": (["w", "w"], None),
    "Low white 1: a spot or toes": (["ws", "w"], 1),
    "Low white 2: chest and toes": (["ws", "w"], 2),
    "Low white 3: chest, belly and paws": (["ws", "w"], 3),
    "Low white 4: socks and more": (["ws", "w"], 4),
    "Low white 5: bicolor": (["ws", "w"], 5),
    "High white 1: high bicolor": (["ws", "ws"], 1),
    "High white 2: mask and mantle": (["ws", "ws"], 2),
    "High white 3: piebald": (["ws", "ws"], 3),
    "High white 4: van": (["ws", "ws"], 4),
    "High white 5: almost all white": (["ws", "ws"], 5),
    "White gloves": (["wg", "wg"], None),
    "Thai stripe": (["wt", "w"], 3),
    "Thai high white": (["wt", "wt"], 3),
    "Salmiak": (["wsal", "wsal"], None),
    "All white": (["W", "w"], None),
}


def get_white(genes):
    for name, (pair, grade) in WHITE.items():
        if sorted(genes.white) == sorted(pair) and (grade is None or grade == genes.whitegrade):
            return name
    return OTHER


def set_white(genes, value):
    pair, grade = WHITE[value]
    genes.maker_white = None  # the new white picks its own patches
    genes.white = list(pair)
    if grade is not None:
        genes.whitegrade = grade


# PAX3 dominant blue eyes: one copy gives blue eyes and ClanGen's own white patches
BLUE_EYED_WHITE = {
    "None": ["NoDBE", "NoDBE"],
    "Some white": ["DBEalt", "NoDBE"],
    "Lots of white": ["DBEalt", "DBEalt"],
    "All white": ["DBEcel", "DBEcel"],
}


def get_blue_eyed_white(genes):
    for name, pair in BLUE_EYED_WHITE.items():
        if sorted(genes.pax3) == sorted(pair):
            return name
    if "NoDBE" in genes.pax3:
        return "Some white"
    return OTHER


def set_blue_eyed_white(genes, value):
    genes.pax3 = list(BLUE_EYED_WHITE[value])


def get_roan(genes):
    return "Yes" if genes.karp[0] == "K" else "No"


def set_roan(genes, value):
    genes.karp = ["K", "k"] if value == "Yes" else ["k", "k"]


# --- eyes -------------------------------------------------------------------------------------
# Genemod picks odd eyes, blue eyes from white and sectoral eyes by chance. Picking an eye here
# fixes it: the choice is kept on the genes as maker_eyes and put back after every redraw.

EYES = [name for row in EYE_COLORS for name in row]


def eye_type(name):
    """Genemod's eye code for a color name, like "R5 ; P7" or "R2 ; blue" """
    for r, row in enumerate(EYE_COLORS):
        if name in row:
            p = row.index(name) + 1
            pig = "blue" if p == 12 else "albino" if p == 13 else f"P{p}"
            return f"R{r + 1} ; {pig}"
    raise ValueError(name)


def eye_name(code):
    try:
        ref, pig = code.split(" ; ")
        p = 12 if pig == "blue" else 13 if pig == "albino" else int(pig[1:])
        return EYE_COLORS[int(ref[1:]) - 1][p - 1]
    except (ValueError, IndexError, AttributeError):
        return OTHER


def maker_eyes(genes):
    """The fixed eye choices, starting from how the eyes look now"""
    eyes = getattr(genes, "maker_eyes", None)
    if eyes is None:
        eyes = {
            "left": genes.lefteyetype,
            "right": genes.righteyetype,
            "sectoral": genes.extraeye,
            "sectoral_color": genes.extraeyetype or genes.lefteyetype,
        }
        genes.maker_eyes = eyes
    return eyes


def apply_maker_eyes(genes):
    """Puts the fixed eye choices back after Genemod rolls the eyes again"""
    eyes = getattr(genes, "maker_eyes", None)
    if not eyes:
        return
    genes.lefteyetype, genes.righteyetype = eyes["left"], eyes["right"]
    genes.lefteye, genes.righteye = eye_name(eyes["left"]), eye_name(eyes["right"])
    genes.extraeye = eyes["sectoral"]
    genes.extraeyetype = eyes["sectoral_color"]
    genes.extraeyecolour = eye_name(eyes["sectoral_color"])


def set_eye_genes(genes, code):
    """The eye grade genes follow the chosen color (blue and albino eyes come from other genes)"""
    ref, pig = code.split(" ; ")
    genes.refraction = int(ref[1:])
    if pig.startswith("P"):
        genes.pigmentation = int(pig[1:])


def get_both_eyes(genes):
    # the first eye (the second one is "Odd eye" when they don't match)
    return eye_name(genes.lefteyetype)


def set_both_eyes(genes, value):
    eyes = maker_eyes(genes)
    eyes["left"] = eyes["right"] = eye_type(value)
    set_eye_genes(genes, eyes["left"])


def get_left_eye(genes):
    return eye_name(genes.lefteyetype)


def set_left_eye(genes, value):
    maker_eyes(genes)["left"] = eye_type(value)
    set_eye_genes(genes, eye_type(value))


def get_right_eye(genes):
    return eye_name(genes.righteyetype)


def set_right_eye(genes, value):
    maker_eyes(genes)["right"] = eye_type(value)


SECTORAL = ["None"] + [f"Sectoral {n}" for n in range(1, 7)]


def get_sectoral(genes):
    if not genes.extraeye:
        return "None"
    return genes.extraeye.replace("sectoral", "Sectoral ")


def set_sectoral(genes, value):
    eyes = maker_eyes(genes)
    eyes["sectoral"] = None if value == "None" else value.replace("Sectoral ", "sectoral")
    # a patch the same color as the eye can't be seen: start it in a different color
    if eyes["sectoral"] and eye_name(eyes["sectoral_color"]) in (eye_name(eyes["left"]), eye_name(eyes["right"])):
        eyes["sectoral_color"] = eye_type("Copper" if "blue" not in eyes["left"] else "Sky Blue")


def get_sectoral_color(genes):
    return eye_name(genes.extraeyetype) if genes.extraeyetype else OTHER


def set_sectoral_color(genes, value):
    eyes = maker_eyes(genes)
    eyes["sectoral_color"] = eye_type(value)
    if not eyes["sectoral"]:
        eyes["sectoral"] = "sectoral1"


# --- fur --------------------------------------------------------------------------------------

FUR_LENGTH = ["Short", "Medium", "Long"]


def get_fur_length(genes):
    if shown(genes, "furLength") == "L":
        return "Short"
    return "Medium" if genes.longtype == "medium" else "Long"


def set_fur_length(genes, value):
    if value == "Short":
        express(genes, "furLength", "L")
    else:
        genes.furLength = ["l", "l"]
        genes.longtype = "medium" if value == "Medium" else "long"


# one gene: Selkirk rex, Devon rex, and the sphynx hairless gene (with Devon it's fur-pointed)
SEDESP = {"Normal": ["Hr", "Hr"], "Selkirk rex": ["Se", "Hr"], "Devon rex": ["re", "re"],
          "Fur-pointed": ["hr", "re"], "Hairless (sphynx)": ["hr", "hr"]}


def get_sedesp(genes):
    if genes.sedesp[0] == "Se":
        return "Selkirk rex"
    for name, pair in SEDESP.items():
        if sorted(genes.sedesp) == sorted(pair):
            return name
    if genes.sedesp[0] == "Hr":
        return "Normal"
    return OTHER


def set_sedesp(genes, value):
    genes.sedesp = list(SEDESP[value])


RUSSIAN = {"Normal": (["hrbd", "hrbd"], None), "Brush coat": (["Hrbd", "hrbd"], ["hi", "hi"]),
           "Patchy brush coat": (["Hrbd", "hrbd"], ["hi", "ha"]), "Hairless": (["Hrbd", "Hrbd"], None)}


def get_russian(genes):
    if genes.ruhr[1] == "Hrbd" or (genes.ruhr == ["Hrbd", "hrbd"] and genes.ruhrmod[0] == "ha"):
        return "Hairless"
    if genes.ruhr[0] != "Hrbd":
        return "Normal"
    return "Brush coat" if genes.ruhrmod == ["hi", "hi"] else "Patchy brush coat"


def set_russian(genes, value):
    pair, mod = RUSSIAN[value]
    genes.ruhr = list(pair)
    if mod:
        genes.ruhrmod = list(mod)


# --- body -------------------------------------------------------------------------------------

EARS = ["Normal", "Folded", "Curled"]


def get_ears(genes):
    if genes.fold[0] == "Fd":
        return "Folded"
    if genes.curl[0] == "Cu":
        return "Curled"
    return "Normal"


def set_ears(genes, value):
    genes.fold = ["Fd", "fd"] if value == "Folded" else ["fd", "fd"]
    genes.curl = ["Cu", "cu"] if value == "Curled" else ["cu", "cu"]


# name: (gene changes from a normal tail, manx tail type)
TAILS = {
    "Normal": ({}, None),
    "American bobtail": ({"manx": ["Ab", "ab"]}, "stubby"),
    "Manx: slightly short": ({"manx": ["M", "ab"]}, "most"),
    "Manx: short": ({"manx": ["M", "ab"]}, "stubby"),
    "Manx: stubby": ({"manx": ["M", "ab"]}, "stumpy"),
    "Manx: barely visible": ({"manx": ["M", "ab"]}, "riser"),
    "Manx: no tail": ({"manx": ["M", "ab"]}, "rumpy"),
    "Japanese bobtail: kinked": ({"jbob": ["Jb", "jb"]}, None),
    "Japanese bobtail: pom-pom": ({"jbob": ["jb", "jb"]}, None),
    "Karelian bobtail: pom-pom": ({"kab": ["kab", "kab"]}, None),
    "Kurilian bobtail: pom-pom": ({"kub": ["Kub", "kub"]}, None),
    "Toybob: kinked": ({"toybob": ["Tb", "tb"]}, None),
    "Toybob: pom-pom": ({"toybob": ["Tb", "Tb"]}, None),
}
NORMAL_TAIL = {"manx": ["ab", "ab"], "jbob": ["Jb", "Jb"], "kab": ["Kab", "Kab"],
               "toybob": ["tb", "tb"], "kub": ["kub", "kub"]}


def get_tail(genes):
    for name, (changes, manxtype) in TAILS.items():
        wanted = dict(NORMAL_TAIL, **changes)
        if all(sorted(genes[g]) == sorted(pair) for g, pair in wanted.items()):
            if manxtype is None or genes.manxtype == manxtype or name == "American bobtail":
                return name
    return OTHER


def set_tail(genes, value):
    changes, manxtype = TAILS[value]
    for gene, pair in dict(NORMAL_TAIL, **changes).items():
        setattr(genes, gene, list(pair))
    if manxtype:
        genes.manxtype = manxtype


LEGS = ["Normal", "Short legs", "Extra toes", "Short legs, extra toes"]


def get_legs(genes):
    short = genes.munch[0] == "Mk"
    toes = genes.poly[0] == "Pd"
    return LEGS[short + 2 * toes]


def set_legs(genes, value):
    index = LEGS.index(value)
    genes.munch = ["Mk", "mk"] if index & 1 else ["mk", "mk"]
    genes.poly = ["Pd", "pd"] if index & 2 else ["pd", "pd"]


BODY_TYPES = ["snub-nosed cobby", "cobby", "semi-cobby", "intermediate", "semi-oriental", "oriental",
              "wedge-faced oriental"]
SIZES = ["teacup", "tiny", "small", "below average", "average", "above average", "large", "massive",
         "giant", "goliath"]


def get_body_type(genes):
    return genes.body_label.capitalize() if genes.body_label else OTHER


def set_body_type(genes, value):
    # Genemod moves the body number into the picked type's range
    genes.body_label = value.lower()


def get_size(genes):
    return genes.height_label.capitalize() if genes.height_label else OTHER


def set_size(genes, value):
    index = SIZES.index(value.lower())
    genes.height_value = genes.height_indexes[index]
    genes.shoulder_height = 0  # worked out again from the new size


def menu(label, options, read, write, **kwargs):
    return Menu(label, options, read, write, **kwargs)


TABS = [
    ("Color", [
        menu("Color", COLORS, get_color, set_color),
        menu("Tortie", TORTIE, get_tortie, set_tortie),
        menu("Caramel or apricot", ["No", "Yes"], get_caramel, set_caramel),
        menu("Points", POINTS, get_points, set_points),
        menu("Extension", list(EXTENSION), get_extension, set_extension),
        menu("Sunshine", list(SUNSHINE), get_sunshine, set_sunshine),
        menu("Special red", list(SPECIAL_RED), get_special_red, set_special_red),
        menu("Nose", NOSE, get_nose, set_nose),
        menu("Saturation", SATURATION, get_saturation, set_saturation),
    ]),
    ("Pattern", [
        menu("Tabby pattern", list(PATTERNS), get_pattern, set_pattern),
        menu("Tabby type", TABBY_TYPES, get_tabby_type, set_tabby_type),
        menu("Silver", ["No", "Yes"], get_silver, set_silver),
        menu("Wideband", *level_menu("wideband", WIDEBAND)),
        menu("Rufousing", *level_menu("rufousing", RUFOUSING)),
        menu("Belly rufousing", *level_menu("unders_ruf", RUFOUSING)),
        menu("Bleaching", ["No", "Yes"], get_bleaching, set_bleaching),
        menu("Ghosting", ["No", "Yes"], get_ghosting, set_ghosting),
        menu("Pangere", list(PANGERE), get_pangere, set_pangere),
        menu("Pseudo-merle (silver cats)", *flag_menu("pseudomerle")),
    ]),
    ("White", [
        menu("White", list(WHITE), get_white, set_white),
        menu("Blue-eyed white", list(BLUE_EYED_WHITE), get_blue_eyed_white, set_blue_eyed_white),
        menu("Vitiligo", *flag_menu("vitiligo")),
        menu("Roan (karpati)", ["No", "Yes"], get_roan, set_roan),
    ]),
    ("Eyes", [
        menu("Both eyes", EYES, get_both_eyes, set_both_eyes),
        menu("Left eye", EYES, get_left_eye, set_left_eye),
        menu("Right eye", EYES, get_right_eye, set_right_eye),
        menu("Sectoral patch", SECTORAL, get_sectoral, set_sectoral),
        menu("Sectoral color", EYES, get_sectoral_color, set_sectoral_color),
    ]),
    ("Fur", [
        menu("Fur length", FUR_LENGTH, get_fur_length, set_fur_length),
        menu("Selkirk, Devon or sphynx", list(SEDESP), get_sedesp, set_sedesp),
        menu("Cornish rex", *gene_menu("cornish", "r", "R", dominant=False)),
        menu("LaPerm", *gene_menu("laperm", "Lp", "lp", dominant=True)),
        menu("Ural rex", *gene_menu("urals", "ru", "Ru", dominant=False)),
        menu("Tennessee rex", *gene_menu("tenn", "tr", "Tr", dominant=False)),
        menu("Fleece", *gene_menu("fleece", "fc", "Fc", dominant=False)),
        menu("Wirehair", *gene_menu("wirehair", "Wh", "wh", dominant=True)),
        menu("Lykoi", *gene_menu("lykoi", "ly", "Ly", dominant=False)),
        menu("Russian brush coat", list(RUSSIAN), get_russian, set_russian),
        menu("Satin", *gene_menu("satin", "st", "St", dominant=False)),
        menu("Glitter", *gene_menu("glitter", "gl", "Gl", dominant=False)),
    ]),
    ("Body", [
        menu("Ears", EARS, get_ears, set_ears),
        menu("Four ears", *gene_menu("fourear", "dup", "Dup", dominant=False)),
        menu("Tail", list(TAILS), get_tail, set_tail),
        menu("Ringtail (curled tail)", *gene_menu("ring", "rt", "Rt", dominant=False)),
        menu("Legs and paws", LEGS, get_legs, set_legs),
        menu("Body type", [b.capitalize() for b in BODY_TYPES], get_body_type, set_body_type),
        menu("Size", [s.capitalize() for s in SIZES], get_size, set_size),
    ]),
]


# shorter names for the custom cat maker's lists (the full name shows under the cat)
SHORT = {
    "Caramel or apricot": "Caramel",
    "Pseudo-merle (silver cats)": "Pseudo-merle",
    "Roan (karpati)": "Roan",
    "Selkirk, Devon or sphynx": "Rex/hairless",
    "Russian brush coat": "Brush coat",
    "Ringtail (curled tail)": "Ringtail",
    "Very high (golden or shaded)": "Very high",
    "Highest (chinchilla)": "Highest",
    "Low white 1: a spot or toes": "Low white 1",
    "Low white 2: chest and toes": "Low white 2",
    "Low white 3: chest, belly and paws": "Low white 3",
    "Low white 4: socks and more": "Low white 4",
    "Low white 5: bicolor": "Low white 5",
    "High white 1: high bicolor": "High white 1",
    "High white 2: mask and mantle": "High white 2",
    "High white 3: piebald": "High white 3",
    "High white 4: van": "High white 4",
    "High white 5: almost all white": "High white 5",
    "Manx: slightly short": "Manx (most)",
    "Manx: short": "Manx (short)",
    "Manx: stubby": "Manx (stubby)",
    "Manx: barely visible": "Manx (riser)",
    "Manx: no tail": "Manx (rumpy)",
    "Japanese bobtail: kinked": "Japanese kinked",
    "Japanese bobtail: pom-pom": "Japanese pom",
    "Karelian bobtail: pom-pom": "Karelian bobtail",
    "Kurilian bobtail: pom-pom": "Kurilian bobtail",
    "Short legs, extra toes": "Short legs+toes",
    "Broken braided pinstripe": "Broken braid pin",
    "Braided pinstripe": "Braided pin",
    "Servaline-rosetted": "Serval-rosetted",
    "Reduced barring ticked": "Reduced barring",
    "Medium 1 and tail": "Medium 1 + tail",
    "Wedge-faced oriental": "Wedge oriental",
    "Patchy brush coat": "Patchy brush",
    "Hairless (sphynx)": "Sphynx",
    "Pangere": "Pale markings",
    "Sectoral 1": "Top of eye 1", "Sectoral 2": "Top of eye 2", "Sectoral 3": "Top of both",
    "Sectoral 4": "Bottom of eye 1", "Sectoral 5": "Bottom of eye 2", "Sectoral 6": "Bottom of both",
    "Deep Forest Green": "Deep Forest",
    "Albino Aquamarine": "Albino Aqua",
}


def short(text):
    return SHORT.get(text, text)


# --- the custom cat maker's combined menus ----------------------------------------------------

# one list for the coat type (each one sets its gene and puts every other fur gene back to normal)
NORMAL_FUR = {"sedesp": ["Hr", "Hr"], "cornish": ["R", "R"], "laperm": ["lp", "lp"], "urals": ["Ru", "Ru"],
              "tenn": ["Tr", "Tr"], "fleece": ["Fc", "Fc"], "wirehair": ["wh", "wh"], "lykoi": ["Ly", "Ly"],
              "ruhr": ["hrbd", "hrbd"]}
FUR_TYPES = {
    "Normal": {},
    "Selkirk rex": {"sedesp": ["Se", "Hr"]},
    "Devon rex": {"sedesp": ["re", "re"]},
    "Cornish rex": {"cornish": ["r", "r"]},
    "LaPerm": {"laperm": ["Lp", "lp"]},
    "Ural rex": {"urals": ["ru", "ru"]},
    "Tennessee rex": {"tenn": ["tr", "tr"]},
    "Fleece": {"fleece": ["fc", "fc"]},
    "Wirehair": {"wirehair": ["Wh", "wh"]},
    "Lykoi": {"lykoi": ["ly", "ly"]},
    "Brush coat": {"ruhr": ["Hrbd", "hrbd"], "ruhrmod": ["hi", "hi"]},
    "Patchy brush": {"ruhr": ["Hrbd", "hrbd"], "ruhrmod": ["hi", "ha"]},
    "Fur-pointed": {"sedesp": ["hr", "re"]},
    "Sphynx": {"sedesp": ["hr", "hr"]},
    "Russian hairless": {"ruhr": ["Hrbd", "Hrbd"]},
}


def get_fur_type(genes):
    for name, changes in FUR_TYPES.items():
        if name == "Normal":
            continue
        if all(sorted(genes[g]) == sorted(pair) for g, pair in changes.items()):
            return name
    if all(sorted(genes[g]) == sorted(pair) for g, pair in NORMAL_FUR.items()):
        return "Normal"
    return OTHER


def set_fur_type(genes, value):
    for gene, pair in NORMAL_FUR.items():
        setattr(genes, gene, list(pair))
    for gene, pair in FUR_TYPES[value].items():
        setattr(genes, gene, list(pair))


# the second eye: "None" for matching eyes (the first eye is "Both eyes")
def get_odd_eye(genes):
    left, right = eye_name(genes.lefteyetype), eye_name(genes.righteyetype)
    return "None" if left == right else right


def set_odd_eye(genes, value):
    eyes = maker_eyes(genes)
    eyes["right"] = eyes["left"] if value == "None" else eye_type(value)


EXTRA_MENUS = [
    menu("Fur type", list(FUR_TYPES), get_fur_type, set_fur_type),
    menu("Odd eye", ["None"] + EYES, get_odd_eye, set_odd_eye),
    # the tortie patches' color: "Natural" is a real tortie, any other color makes the cat a
    # chimera (two sets of genes, one for the patches). The custom cat maker does the work.
    menu("Tortie color", ["Natural"] + COLORS, lambda genes: OTHER, lambda genes, value: None),
    # the patches' pattern: "Same as cat" for a real tortie, any other makes a chimera too
    menu("Tortie pattern", ["Same as cat"] + list(PATTERNS), lambda genes: OTHER, lambda genes, value: None),
]



# --- white patches, as the game's sprites have them (for the white list) ----------------------

def _sprite_list(path):
    with open(path, encoding="utf-8") as file:
        return [name for row in json.load(file)["sprite_list"] for name in row]


def _files(folder):
    return sorted(name[:-4] for name in os.listdir(folder) if name.endswith(".png"))


def white_patch_groups():
    """[(heading, [patch names])]: Genemod's, ClanGen's, color spots (white that's taken away)"""
    clangen = [name for size in ("little", "mid", "high", "mostly")
               for name in _sprite_list(f"sprites/dicts/white_patches_{size}_sprite_data.json")]
    genemod = [name for name in _files("sprites/genemod/white") if not name.startswith("pangere")]
    groups = [("Genemod patches:", genemod),
              ("ClanGen patches:", [name for name in clangen if name.lower() not in genemod]),
              ("Color spots:", [f"break/{name}" for name in _files("sprites/genemod/break white")])]
    return groups


def patch_name(name):
    """A patch's name for the list: "left front bicolour2" -> "L front bicolor 2" """
    text = name.replace("break/", "").replace("MMW_", "").replace("MMT_", "").replace("bicolour", "bicolor")
    words = text.lower().split()
    words = ["L" if w == "left" else "R" if w == "right" else w for w in words]
    text = " ".join(words)
    if text[-1:].isdigit() and not text[-2:-1].isspace() and not text[-2:-1].isdigit():
        text = text[:-1] + " " + text[-1]
    # ClanGen has a tortie patch called just "BODY"
    text = " ".join(text.replace("reverse", "reverse ").replace("sprite", "").split())
    text = text[:1].upper() + text[1:]
    return text if len(text) <= 16 else text[:15].rstrip() + "."


# How much of the cat each white gene covers on average (measured from the game's own white
# placement, Pelt.generate_white): picked patches get the white genes that match their amount.
# (share of the cat that's white, white genes, white grade), from the most white down
WHITE_BY_AMOUNT = [
    (0.885, ["ws", "ws"], 5), (0.815, ["ws", "ws"], 4), (0.68, ["ws", "ws"], 3), (0.53, ["ws", "ws"], 2),
    (0.485, ["ws", "ws"], 1), (0.385, ["ws", "w"], 5), (0.25, ["ws", "w"], 4), (0.135, ["ws", "w"], 3),
    (0.06, ["ws", "w"], 2), (0.0001, ["ws", "w"], 1),
]
_PATCH_PIXELS = {}


def _patch_pixels(name, pose="12"):
    """The pixels a patch covers (on the adult pose)"""
    if (name, pose) not in _PATCH_PIXELS:
        from scripts.cat.sprites.load_sprites import sprites
        surf = sprites.sprites.get(name + pose)
        pixels = set()
        if surf is not None:
            width, height = surf.get_size()
            pixels = {(x, y) for x in range(width) for y in range(height) if surf.get_at((x, y))[3] > 40}
        _PATCH_PIXELS[(name, pose)] = pixels
    return _PATCH_PIXELS[(name, pose)]


def white_amount(patches):
    """The share of the cat the patches make white (color spots take white away)"""
    body = _patch_pixels("FULLWHITE")
    if not body:
        return 0
    white = set()
    for name in patches:
        if name.startswith("break/"):
            white -= _patch_pixels(name)
        else:
            white |= _patch_pixels(name)
    return len(white & body) / len(body)


def white_genes_for(patches):
    """(white genes, white grade) for that much white, like the game would give it"""
    amount = white_amount(patches)
    for lowest, pair, grade in WHITE_BY_AMOUNT:
        if amount >= lowest:
            return list(pair), grade
    return ["w", "w"], None


# genes the custom cat maker's lists don't set start out plain (no hidden extra toes or rex fur
# from the random cat underneath)
PLAIN_GENES = {
    "wirehair": ["wh", "wh"], "laperm": ["lp", "lp"], "cornish": ["R", "R"], "urals": ["Ru", "Ru"],
    "tenn": ["Tr", "Tr"], "fleece": ["Fc", "Fc"], "sedesp": ["Hr", "Hr"], "ruhr": ["hrbd", "hrbd"],
    "lykoi": ["Ly", "Ly"], "pinkdilute": ["Dp", "Dp"], "dilutemd": ["dm", "dm"], "ext": ["E", "E"],
    "corin": ["N", "N"], "karp": ["k", "k"], "bleach": ["Lb", "Lb"], "ghosting": ["gh", "gh"],
    "satin": ["St", "St"], "glitter": ["Gl", "Gl"], "curl": ["cu", "cu"], "fold": ["fd", "fd"],
    "fourear": ["Dup", "Dup"], "manx": ["ab", "ab"], "kab": ["Kab", "Kab"], "toybob": ["tb", "tb"],
    "jbob": ["Jb", "Jb"], "kub": ["kub", "kub"], "ring": ["Rt", "Rt"], "munch": ["mk", "mk"],
    "poly": ["pd", "pd"], "pax3": ["NoDBE", "NoDBE"],
}


def make_plain(genes):
    for gene, pair in PLAIN_GENES.items():
        setattr(genes, gene, list(pair))
    genes.ruhrmod = ""
    genes.specialred = None
    genes.vitiligo = False
    genes.pseudomerle = False
    genes.brindledbi = False
    genes.pangere = None
    genes.sex = "tom" if "Y" in genes.sexgene else "molly"
    genes.somatic = {}
    genes.breeds = {}
