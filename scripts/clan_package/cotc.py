from scripts.cat.enums import CatGroup
from scripts.game_structure import game


def get_warring_clan():
    """
    returns enemy clan if a war is currently ongoing
    """
    # wars are stored per clan pair now (genemod), so just ask for the player clans enemies
    enemies = game.clan.get_wars(CatGroup.PLAYER_CLAN_ID)
    for other_clan in game.clan.all_other_clans:
        if other_clan.group_ID in enemies:
            return other_clan
    return None


def get_other_clan(clan_name):
    """
    returns the clan object of given clan name
    """
    for clan in game.clan.all_other_clans:
        if clan.displayname == clan_name:
            return clan


def change_clan_relations(clan, other_clan, difference):
    """
    will change the Clan's relation with other clans according to the difference parameter.
    """
    # grab the relation value for that clan
    clan_relations = game.clan.get_relations(clan, other_clan)
    # change the value
    clan_relations += difference
    # making sure it doesn't exceed the bounds
    if clan_relations > 30:
        clan_relations = 30
    elif clan_relations < 0:
        clan_relations = 0
    # setting it in the Clan save
    game.clan.set_relations(clan, other_clan, clan_relations)


def change_clan_reputation(difference, clan):
    """
    will change the Clan's reputation with outsider cats according to the difference parameter.
    """
    clan.reputation += difference
    if clan.reputation < 0:
        clan.reputation = 0  # clamp to 0
    elif clan.reputation > 100:
        clan.reputation = 100  # clamp to 100
