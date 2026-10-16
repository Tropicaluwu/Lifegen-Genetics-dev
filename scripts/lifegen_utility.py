import ujson
import re
from random import choice
from scripts.game_structure import game
from scripts.cat.enums import (
    CatAge,
    CatRank,
    CatGroup
)
from scripts.clan_package.get_clan_cats import find_alive_cats_with_rank, get_living_clan_cat_count
from scripts.game_structure.game.switches import switch_get_value, Switch
from scripts.screens.enums import GameScreen

_CLUSTER_MAP = None


def get_cluster(trait):
    """
    Returns the cluster(s) for a given trait.
    """
    # the map never changes while playing, so it's only read from the disk once
    global _CLUSTER_MAP
    if _CLUSTER_MAP is None:
        with open("resources/dicts/cluster_map.json", "r", encoding="utf-8") as file:
            _CLUSTER_MAP = ujson.load(file)
    cluster_map = _CLUSTER_MAP

    clusters = [key for key, values in cluster_map.items() if trait in values]

    # Assign cluster and second_cluster based on the length of clusters list
    cluster = clusters[0] if clusters else "stable"
    second_cluster = clusters[1] if len(clusters) > 1 else ""

    return cluster, second_cluster

def check_achievements(Cat, eventspage=False):
    you = game.clan.your_cat
    achievements = set()
    murder_history = you.history.murder
    num_victims = len(murder_history["is_murderer"]) if murder_history and "is_murderer" in murder_history else 0
    if num_victims >= 1:
        achievements.add("1")
    if num_victims >= 5:
        achievements.add("2")
    if num_victims >= 20:
        achievements.add("3")
    if num_victims >= 50:
        achievements.add("4")
    if num_victims == 0 and you.moons >= 120:
        achievements.add("25")

    your_mate_ids = you.mate
    for cat in Cat.all_cats_list:
        if cat.moons < 0:
            continue

        # genemod: a tom only shows tortie if he carries both O and o
        if cat.gender in ('male', 'tom') and 'O' in cat.phenotype.sexgene and 'o' in cat.phenotype.sexgene:
            achievements.add("5")
        if cat.insulted:
            achievements.add("29")
        if (cat.name.prefix == "Coffee" and cat.name.suffix == "dot") or (cat.name.prefix == "Chibi" and cat.name.suffix == "Galaxies"):
            achievements.add("30")
        if cat.status.rank == CatRank.APPRENTICE and cat.name.prefix == "Pea" and cat.phenotype.white[0] == "W":
            achievements.add("33")
        if cat.status.rank == CatRank.KITTEN and cat.moons > 6:
            achievements.add("34")
        if cat.backstory in ('dfkit', 'dfkit2'):
            achievements.add("35")
        # the old wildcard tortie check was based on lifegen pelt fields, with genetics
        # the closest thing is a chimera cat so that counts now
        if cat.chimerapheno is not None:
            achievements.add("6")

        if len(cat.mate) >= 2 and cat.status.rank in frozenset({CatRank.WARRIOR, CatRank.MEDIATOR, CatRank.LEADER}):
            group_ranks = {cat.status.rank}
            for mate in Cat.all_cats_list:
                if mate.ID in cat.mate and mate.status.rank in frozenset({CatRank.WARRIOR, CatRank.MEDIATOR, CatRank.LEADER}):
                    group_ranks.add(mate.status.rank)
            if group_ranks >= frozenset({CatRank.WARRIOR, CatRank.MEDIATOR, CatRank.LEADER}):
                achievements.add("31")

        is_dark_forest_cat = cat.status.group == CatGroup.DARK_FOREST or (not cat.dead and cat.joined_df)
        if cat.ID in your_mate_ids and not you.dead and is_dark_forest_cat and cat.history \
                and cat.history.beginning and cat.history.beginning.get("encountered") is True:
            achievements.add("36")

    if game.clan.age >= 1:
        living_count = get_living_clan_cat_count(Cat)
        if living_count == 0:
            achievements.add('40')
        elif living_count == 1 and you.status.alive_in_player_clan:
            achievements.add('23')
        else:
            if living_count >= 100:
                achievements.add('24')
            if living_count >= 400:
                achievements.add('39')

    if you.joined_df:
        achievements.add("7")
    
    if len(you.former_apprentices) >= 1:
        achievements.add("8")
    if len(you.former_apprentices) >= 5:
        achievements.add("9")
    
    if not you.inheritance:
        from scripts.cat_relations.inheritance import Inheritance
        you.inheritance = Inheritance(you)
    if you.inheritance.get_children():
        achievements.add("10")
    for i in you.relationships.keys():
        if you.relationships.get(i).like <= -60:
            achievements.add("11")
        if you.relationships.get(i).romance >= 60:
            achievements.add('12')
        
    if len(you.mate) >= 5:
        achievements.add('13')
    if you.status.rank == CatRank.WARRIOR:
        achievements.add('14')
    elif you.status.rank == CatRank.MEDICINE_CAT:
        achievements.add('15')
    elif you.status.rank == CatRank.MEDIATOR:
        achievements.add('16')
    elif you.status.rank == CatRank.DEPUTY:
        achievements.add('17')
    elif you.status.rank == CatRank.LEADER:
        achievements.add('18')
    elif you.status.rank == CatRank.ELDER:
        achievements.add('19')
    elif you.status.rank == CatRank.QUEEN:
        achievements.add('32')
    
    if you.moons >= 200:
        achievements.add('20')
    if you.status.is_exiled(CatGroup.PLAYER_CLAN_ID):
        achievements.add('21')
    elif you.status.is_outsider:
        achievements.add('22')
        
    if you.experience >= 100:
        achievements.add('26')
    if you.experience >= 200:
        achievements.add('27')
    if you.experience >= 300:
        achievements.add('28')

    new_achievements_list = []
    for item in achievements:
        already_earned = False
        for entry in game.clan.achievements:
            if entry[0] == item:
                already_earned = True
                break

        if not already_earned:
            game.clan.achievements.append([item, game.clan.your_cat.ID])
            if eventspage:
                new_achievements_list.append(item)
    if eventspage:
        return new_achievements_list
    
def get_current_camp():
    """ LG """
    if game.clan.your_cat:
        if game.clan.your_cat.status.group in [CatGroup.PLAYER_CLAN, CatGroup.OTHER_CLAN]:
            camp_nr = game.clan.camp_bg
            camp_bg_base_dir = "resources/images/camp_bg/clancat"
        elif game.clan.your_cat.status.group == CatGroup.ROGUE_GROUP:
            camp_nr = game.clan.rogue_group_bg
            camp_bg_base_dir = "resources/images/camp_bg/rogue"
        elif game.clan.your_cat.status.group == CatGroup.LONER_GROUP:
            camp_nr = game.clan.loner_group_bg
            camp_bg_base_dir = "resources/images/camp_bg/loner"
        elif game.clan.your_cat.status.group == CatGroup.HOUSEHOLD:
            camp_nr = game.clan.household_bg
            camp_bg_base_dir = "resources/images/camp_bg/kittypet"
        else:
            camp_nr = game.clan.no_group_bg
            camp_bg_base_dir = "resources/images/camp_bg/none"
    else:
        camp_nr = game.clan.camp_bg
        camp_bg_base_dir = "resources/images/camp_bg/clancat"

    return camp_bg_base_dir, camp_nr

def assign_new_bg(camp):
    """ LG """
    if game.clan.your_cat:
        if game.clan.your_cat.status.group in [CatGroup.PLAYER_CLAN, CatGroup.OTHER_CLAN]:
            game.clan.camp_bg = camp
        elif game.clan.your_cat.status.group == CatGroup.ROGUE_GROUP:
            game.clan.rogue_group_bg = camp
        elif game.clan.your_cat.status.group == CatGroup.LONER_GROUP:
            game.clan.loner_group_bg = camp
        elif game.clan.your_cat.status.group == CatGroup.HOUSEHOLD:
            game.clan.household_bg = camp
        else:
            game.clan.no_group_bg = camp
    else:
        game.clan.camp_bg = camp

# LG
def get_your_cat_group_count(Cat):
    count = 0
    for the_cat in Cat.all_cats.values():
        if not the_cat.status.alive_in_your_cat_group:
            continue
        count += 1
    return count
