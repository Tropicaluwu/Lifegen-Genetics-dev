# pylint: disable=line-too-long
"""

TODO: Docs


"""
import logging
import random
from copy import deepcopy

# pylint: enable=line-too-long
import traceback
from math import floor

import i18n
import ujson
from enum import Enum

import re

from scripts.cat.cats import Cat, cat_class, BACKSTORIES
from scripts.cat.pelts import Pelt
from scripts.cat.sprites.load_sprites import sprites
from scripts.clan_package.cotc import get_warring_clan

from scripts.clan_resources.freshkill import FreshkillPile
from scripts.cat_relations.relationship import Relationship
from scripts.cat.enums import (
    CatAge,
    CatRank,
    CatGroup,
    CatStanding,
    CatSocial,
    CatThought,
)
from scripts.cat.names import Name
from scripts.cat.save_load import save_cats, add_cat_to_fade_id
from scripts.cat.skills import SkillPath
from scripts.clan_package.settings import get_clan_setting, set_clan_setting
from scripts.game_structure.game.settings import game_setting_get
from scripts.clan_resources.freshkill import FRESHKILL_EVENT_ACTIVE
from scripts.conditions import (
    medicine_cats_can_cover_clan,
    get_amount_cat_for_one_medic,
)
from scripts.event_class import Single_Event
from scripts.events_module.event_filters import event_for_other_clan

from scripts.events_module.generate_events import GenerateEvents, generate_events
from scripts.events_module.outsider_events import OutsiderEvents
from scripts.events_module.patrol.patrol import Patrol
from scripts.events_module.relationship.pregnancy_events import Pregnancy_Events
from scripts.events_module.relationship.relation_events import Relation_Events
from scripts.events_module.relationship.crossclan_event_generation import handle_crossclan_relationships
from scripts.events_module.short.condition_events import Condition_Events
from scripts.events_module.short.short_event_generation import create_short_event
from scripts.game_structure import constants
from scripts.game_structure.game.switches import (
    Switch,
    switch_get_value,
    switch_set_value,
    switch_append_list_value
)
from scripts.events_module.consequences import (
    create_new_cat
)
from scripts.game_structure import game
from scripts.game_structure.localization import load_lang_resource
from scripts.ui.windows.save_error import SaveErrorWindow
from scripts.events_module.text_adjust import (
    ongoing_event_text_adjust,
    event_text_adjust,
    ceremony_text_adjust,
    adjust_list_text,
    history_text_adjust,
    pronoun_repl,
    process_text
)

from scripts.events_module.consequences import unpack_rel_block
from scripts.clan_package.cotc import (
    change_clan_reputation,
    change_clan_relations,
    get_other_clan,
)
from scripts.clan_package.get_clan_cats import (
    find_alive_cats_with_rank,
    get_living_clan_cat_count,
)

from scripts.events_module.filter_random_cats import choose_random_cats

from scripts.lifegen_utility import get_cluster, check_achievements, get_your_cat_group_count

logger = logging.getLogger(__name__)

class BirthType(Enum):
    NO_PARENTS = "birth_no_parents"
    ONE_PARENT = "birth_one_parent"
    TWO_PARENTS = "birth_two_parents"
    ONE_ADOPTIVE_PARENT = "birth_one_adoptive_parent"
    TWO_ADOPTIVE_PARENTS = "birth_two_adoptive_parents"
    ONE_OUTSIDER_PARENT = "birth_one_parent_outsider"
    TWO_OUTSIDER_PARENTS = "birth_two_parent_outsiders"
    ALONE = "birth_alone"
    # LG: outsider-pair birth types for MCs who start as kittypet / loner / rogue
    TWO_KITTYPET_PARENTS = "birth_two_kittypet_parents"
    TWO_LONER_PARENTS = "birth_two_loner_parents"
    TWO_ROGUE_PARENTS = "birth_two_rogue_parents"
    MIXED_OUTSIDER_PARENTS = "birth_mixed_outsider_parents"

    def birth_type_weights(self, mc_group=None):
        # Base weights, used as-is for clan MCs
        weights = {
            BirthType.NO_PARENTS: 2,
            BirthType.ONE_PARENT: 2,
            BirthType.TWO_PARENTS: 3,
            BirthType.ONE_ADOPTIVE_PARENT: 3,
            BirthType.TWO_ADOPTIVE_PARENTS: 3,
            BirthType.ONE_OUTSIDER_PARENT: 2,
            BirthType.TWO_OUTSIDER_PARENTS: 1
        }

        # For outsider MCs: replace the generic outsider-parent types with group-specific ones, biased towards parents matching the player cat's group.
        outsider_match = {
            CatGroup.HOUSEHOLD_ID: BirthType.TWO_KITTYPET_PARENTS,
            CatGroup.LONER_GROUP_ID: BirthType.TWO_LONER_PARENTS,
            CatGroup.ROGUE_GROUP_ID: BirthType.TWO_ROGUE_PARENTS,
        }
        if mc_group in outsider_match:
            del weights[BirthType.ONE_OUTSIDER_PARENT]
            del weights[BirthType.TWO_OUTSIDER_PARENTS]
            matching = outsider_match[mc_group]
            for bt in (
                BirthType.TWO_KITTYPET_PARENTS,
                BirthType.TWO_LONER_PARENTS,
                BirthType.TWO_ROGUE_PARENTS,
            ):
                weights[bt] = 6 if bt == matching else 1
            weights[BirthType.MIXED_OUTSIDER_PARENTS] = 2

        return weights

all_events = {}
new_cat_invited = False
ceremony_accessory = False
CEREMONY_TXT = None
WAR_TXT = None
ceremony_lang = None
war_lang = None
ceremony_id_by_tag = {}

# LG
checks = []
b_txt = load_lang_resource("events/birth_events.json")
lifegen_ceremonies = load_lang_resource("events/lifegen_events/ceremonies.json")
kit_events = load_lang_resource("events/lifegen_events/kit_events.json")
m_txt = {}
cat_dict = {}

def one_moon():
    """
    Handles the moon skipping of the whole Clan.
    """
    try:
        _one_moon_impl()
    finally:
        Cat.end_moon_cache()


def _one_moon_impl():
    global new_cat_invited
    global checks
    # i have no idea what checks does. coffee help
    
    game.cur_events_list = []
    game.herb_events_list = []
    game.freshkill_event_list = []
    game.mediated = []
    game.told_story = []
    switch_set_value(Switch.saved_clan, False)
    new_cat_invited = False
    Relation_Events.clear_trigger_dict()
    Patrol.used_patrols.clear()
    game.patrolled.clear()
    game.just_died.clear()
    game.dated_cats.clear()

    # age up the clan, set current season
    game.clan.age += 1

    update_afterlife_temper()
    Pregnancy_Events.handle_pregnancy_age(game.clan)

    if switch_get_value(Switch.change_group):
        new_group_ID = switch_get_value(Switch.change_group)

        game.clan.your_cat.status.add_to_group(new_group_ID, game.clan.your_cat.age)
        change_group_events(new_group_ID)
        # this runs this skip regardless of auto freshkill setting so
        # the new group will always have food
        # otherwise, switching from a rogue group to a clan would starve them all
        auto_freshkill()

        # auto freshkill is set when the player is an outsider
        if not game.clan.your_cat.status.group.is_any_clan_group():
            set_clan_setting("freshkill", True)
        else:
            # player rejoined the clan the outsider pile gets discarded so a future trip back outside starts fresh.
            if game.clan.freshkill_pile:
                game.clan.freshkill_pile.discard_outside_pile()

        switch_set_value(Switch.change_group, None)

    your_cat = game.clan.your_cat
    blood_kits = (
        len(your_cat.inheritance.get_blood_kits()) if your_cat.inheritance else 0
    )
    checks = [
        len(your_cat.apprentice),
        len(your_cat.mate),
        blood_kits,
        game.clan.leader.ID if game.clan.leader else None,
    ]

    # 1 = reg patrol 2 = lifegen patrol 3 = df patrol 4 = date
    switch_set_value(Switch.patrolled, [])
    switch_set_value(Switch.window_open, False)
    
    if game.clan.your_cat.status.rank == CatRank.MEDICINE_APPRENTICE or game.clan.your_cat.status.rank == CatRank.MEDICINE_CAT:
        switch_set_value(
            Switch.attended_half_moon, False
        )

    if (
        game.clan.game_mode in ("expanded", "cruel season")
        and game.clan.freshkill_pile
    ):
        # feed the cats and update the nutrient status
        relevant_cats = list(
            filter(
                lambda _cat: _cat.status.alive_in_your_cat_group,
                Cat.all_cats.values(),
            )
        )
        game.clan.freshkill_pile.time_skip(relevant_cats, game.freshkill_event_list)
        # get the moonskip freshkill
        get_moon_freshkill()

    # Adding in any potential lead den events that have been saved
    if get_clan_setting("lead_den_interaction"):
        handle_lead_den_event()

    clancount = game.clan.clancount == "multiclan"
    clannames = [game.clan.displayname] + [c.displayname for c in game.clan.all_other_clans]

    check_war()

    # checking if a lost cat returns on their own
    rejoin_upperbound = constants.CONFIG["lost_cat"]["rejoin_chance"]
    if random.randint(1, rejoin_upperbound) == 1:
        handle_lost_cats_return(clan=game.clan)
    
    handle_tnr_return(clan=game.clan)

    if clancount:
        for clan in game.clan.all_other_clans:
            if random.randint(1, rejoin_upperbound) == 1:
                handle_lost_cats_return(clan=clan)
            handle_tnr_return(clan=clan)

    #Kill kits as needed
    faded_kits = {}
    for clan in [game.clan] + game.clan.all_other_clans:
        if get_clan_setting('modded_kits'):
            faded_kits[clan.displayname] = kit_deaths(Cat.all_cats_list, clan=clan)
        else:
            faded_kits[clan.displayname] = []
        if not clancount:
            break

    trigger_future_events(clan=game.clan)

    if clancount:
        for clan in game.clan.all_other_clans:
            trigger_future_events(clan=clan)

    # Calling of "one_moon" functions.
    
    # LG: Disasters
    # CHECKMERGE
    # im gonna entirely redo how disasters are done. sorry coffee this code scares the shit out of me
    # and it keeps failing build tests. like Crazy
    # disaster_text = load_lang_resource(f"events/disasters/{game.clan.biome.lower()}.json")
    # if not game.clan.disaster and random.randint(1,10) == 1:
    #     for clan_cat in game.clan.clan_cats:
    #         clan_cat_cat = Cat.fetch_cat(clan_cat)
    #         if clan_cat_cat:
    #             clan_cat_cat.faith -= round(random.uniform(-1,0), 2)

    #     chosen_disaster_name = random.choice(list(disaster_text.keys()))
    #     # CHECKMERGE add real filtering here

    #     game.clan.disaster = chosen_disaster_name
        
    #     if Switch.next_possible_disaster:
    #         current_disaster =  disaster_text.get(Switch.next_possible_disaster)
    #     else:
    #         current_disaster = disaster_text[chosen_disaster_name]
    
    # if game.clan.disaster and game.clan.disaster != "":
    #     if game.clan.disaster == Switch.next_possible_disaster:
    #         switch_set_value(Switch.next_possible_disaster, None)
    #     for clan_cat in game.clan.clan_cats:
    #         clan_cat_cat = Cat.fetch_cat(clan_cat)
    #         if clan_cat_cat:
    #             clan_cat_cat.faith -= round(random.uniform(-0.1,0), 2)
    #     handle_disaster(disaster_text[game.clan.disaster], resource=disaster_text)
    # ---

    Cat.begin_moon_cache()

    other_clan_cats = [c for c in Cat.all_cats_list if c.status.is_other_clancat]
    for cat in Cat.all_cats_list.copy():
        if (
            cat.status.alive_in_your_cat_group
            and not cat.status.group.is_any_clan_group()
            and not cat.status.group.is_afterlife()
        ):
            # LG: cats that live with you outside of the clan
            one_moon_cat(cat, game.clan)
        elif (
            not cat.status.group_ID
            or (cat.status.is_other_clancat and game.clan.clancount == "singleclan")
            # cats in a rogue group, loner group or household your cat isn't part of anymore
            # still get their moon, before they were skipped and stopped aging
            or cat.status.group_ID in (CatGroup.ROGUE_GROUP_ID, CatGroup.LONER_GROUP_ID, CatGroup.HOUSEHOLD_ID)
        ):
            one_moon_outside_cat(cat, other_clan_cats)
        elif cat.status.group.is_any_clan_group() or cat.status.group.is_afterlife():
            one_moon_cat(cat, cat.status.fetch_clan_object(game.clan))
        cat.pelt.rebuild_sprite = True

    # keeping this commented out till disasters are more polished
    # disaster_events.handle_disasters()

    # Handle grief events.
    if game.clan.grief_strings:
        # Grab all the dead or outside cats, who should not have grief text
        for ID in game.clan.grief_strings.copy():
            check_cat = Cat.all_cats.get(ID)
            if isinstance(check_cat, Cat):
                if check_cat.dead or (check_cat.status.is_outsider and not check_cat.status.alive_in_your_cat_group):
                    game.clan.grief_strings.pop(ID)

        # Generate events

        for cat_id, details in game.clan.grief_strings.items():
            for _info in details:
                text = _info[0]
                cats = _info[1]
                grief_type = _info[2]

                if grief_type == "minor":
                    Cat.fetch_cat(cat_id).get_new_thought(
                        text, other_cat=Cat.fetch_cat(cats[0])
                    )

                else:
                    game.cur_events_list.append(
                        Single_Event(text, ["birth_death", "relation"], cats, clan=Cat.fetch_cat(cat_id).status.group_ID)
                    )
                    Cat.fetch_cat(cat_id).faith -= round(random.uniform(-1,0), 2)

        game.clan.grief_strings.clear()

    if game.dead_cats_to_grieve:
        ghost_names = {}
        sorted_dead_cats = {}
        shaken_cats = {}
        extra_event = None
        for ghost in game.dead_cats_to_grieve.copy():
            # LG if
            if not ghost:
                game.dead_cats_to_grieve.remove(ghost)
                print("WARNING: Nonetype in game.dead_cats_to_grieve.")
                continue
            if ghost.dead_for > 1 or not ghost.dead:
                continue
            # ---
            last_living = ghost.status.get_last_living_group()
            if ghost.status.is_exiled(last_living) or ghost.status.has_left(last_living):
                pass
            elif last_living == CatGroup.PLAYER_CLAN_ID:
                if game.clan.displayname not in ghost_names:
                    ghost_names[game.clan.displayname] = []
                    sorted_dead_cats[game.clan.displayname] = []
                ghost_names[game.clan.displayname].append(str(ghost.name))
                sorted_dead_cats[game.clan.displayname].append(ghost)
            elif group := next(filter(lambda c: last_living == c.group_ID, game.clan.all_other_clans), None):
                group = ghost.status.fetch_clan_object()
                if group.displayname not in ghost_names:
                    ghost_names[group.displayname] = []
                    sorted_dead_cats[group.displayname] = []
                ghost_names[group.displayname].append(str(ghost.name))
                sorted_dead_cats[group.displayname].append(ghost)
        for clan in [game.clan] + game.clan.all_other_clans:
            if clan.displayname not in ghost_names:
                continue
            extra_event = None
            insert = adjust_list_text(ghost_names[clan.displayname])

            if len(ghost_names[clan.displayname]) > 1:
                event = i18n.t(
                    "hardcoded.event_deaths", count=len(ghost_names[clan.displayname]), insert=insert
                )

                if len(ghost_names[clan.displayname])-len(faded_kits.get(clan.displayname, [])) > 2:
                    alive_cats = list(
                        filter(
                            lambda kitty: (
                                not kitty.status.is_leader and kitty.status.group_ID == clan.group_ID
                            ),
                            Cat.all_cats.values(),
                        )
                    )
                    # finds a percentage of the living Clan to become shaken

                    if len(alive_cats) == 0:
                        return
                    else:
                        shaken_cats[clan.displayname] = random.sample(
                            alive_cats,
                            k=max(
                                int((len(alive_cats) * random.randint(4, 6)) / 100),
                                1,
                            ),
                        )

                    shaken_cat_names = []
                    for cat in shaken_cats[clan.displayname]:
                        shaken_cat_names.append(str(cat.name))
                        cat.get_injured(
                            "shock",
                            event_triggered=False,
                            lethal=False,
                            severity="minor"
                        )

                    insert = adjust_list_text(shaken_cat_names)

                    extra_event = i18n.t(
                        "hardcoded.event_shaken_grief",
                        count=len(shaken_cat_names),
                        insert=insert,
                    )

            else:
                event = i18n.t("hardcoded.event_deaths", count=1)
                #event = event_text_adjust(Cat, event, main_cat=Cat.dead_cats[0])

            game.cur_events_list.append(
                Single_Event(
                    event_text_adjust(Cat, event, main_cat=sorted_dead_cats[clan.displayname][0], clan=clan),
                    ["birth_death"],
                    [i.ID for i in sorted_dead_cats[clan.displayname]],
                    cat_dict={"m_c": (sorted_dead_cats[clan.displayname])[0]} 
                    if len(sorted_dead_cats[clan.displayname]) == 1 else None,
                    clan=clan.group_ID
                )
            )
            if extra_event:
                game.cur_events_list.append(
                    Single_Event(
                        event_text_adjust(Cat, extra_event, clan=clan), 
                        ["birth_death"], 
                        [i.ID for i in shaken_cats.get(clan.displayname, [])], 
                        clan=clan.group_ID
                    )
                )
            
            if not clancount:
                break
        game.dead_cats_to_grieve.clear()

    if (
        game.clan.game_mode in ("expanded", "cruel season")
        and game.clan.freshkill_pile
    ):
        # make a notification if the Clan does not have enough prey
        if (
            FRESHKILL_EVENT_ACTIVE
            and not game.clan.freshkill_pile.clan_has_enough_food()
        ):
            event_string = i18n.t("defaults.warn_low_freshkill")
            game.cur_events_list.insert(0, Single_Event(event_string, clan=game.clan.group_ID))
            game.freshkill_event_list.append(event_string)

    handle_focus()

    # handle the herb supply for the moon
    mc = game.clan.your_cat
    mc_group = mc.status.group if mc else CatGroup.NONE
    if mc and not mc_group.is_any_clan_group():
        # the herb supply follows the player group when they're an
        # outsider, same as the freshkill pile. Kittypets are cared for by
        # Twolegs and don't need herbs, can change possibly
        if mc_group != CatGroup.HOUSEHOLD:
            group_cats = [
                c for c in Cat.all_cats_list if c.status.alive_in_your_cat_group
            ]
            game.clan.herb_supply.handle_moon(
                clan_size=len(group_cats),
                clan_cats=group_cats,
                med_cats=[mc] if mc.status.alive_in_your_cat_group else [],
            )
    else:
        game.clan.herb_supply.handle_moon(
            clan_size=get_living_clan_cat_count(Cat),
            clan_cats=[c for c in Cat.all_cats_list if c.status.alive_in_player_clan],
            med_cats=find_alive_cats_with_rank(
                Cat,
                ranks=[CatRank.MEDICINE_CAT, CatRank.MEDICINE_APPRENTICE],
                working=True,
            ),
        )

    if game.clan.game_mode in ("expanded", "cruel season"):
        amount_per_med = get_amount_cat_for_one_medic()
        med_fulfilled = medicine_cats_can_cover_clan(
            Cat.all_cats.values(), amount_per_med, clan=CatGroup.PLAYER_CLAN_ID
        )

        if not med_fulfilled:
            string = i18n.t("defaults.warn_low_medcats")
            game.cur_events_list.insert(0, Single_Event(string, "health", clan=game.clan.group_ID))
    else:
        has_med = any(
            cat.status.rank.is_any_medicine_rank()
            and cat.status.alive_in_player_clan
            for cat in Cat.all_cats.values()
        )
        if not has_med:
            string = event_text_adjust(Cat, i18n.t("defaults.warn_no_medcats"), clan=game.clan)
            game.cur_events_list.insert(0, Single_Event(string, "health", clan=game.clan.group_ID))
    if clancount:
        for oc in game.clan.all_other_clans:
            has_med = any(
                cat.status.rank.is_any_medicine_rank()
                and cat.status.group_ID == oc.group_ID
                for cat in Cat.all_cats.values()
            )
            if not has_med:
                string = event_text_adjust(Cat, i18n.t("defaults.warn_no_medcats"), clan=oc)
                game.cur_events_list.insert(0, Single_Event(string, "health", clan=oc.group_ID))


    # Clear the list of cats that died this moon.
    game.just_died.clear()

    # Promote leader and deputy, if needed.
    for clan in [game.clan] + game.clan.all_other_clans:
        check_and_promote_leader(clan)
        check_and_promote_deputy(clan)
        if not clancount:
            break

    if clancount:
        handle_crossclan_relationships()

    # Resort
    if switch_get_value(Switch.sort_type) != "id":
        Cat.sort_cats()

    # Clear all the loaded event dicts.
    GenerateEvents.clear_loaded_events()

    # autosave
    if get_clan_setting("autosave") and game.clan.age % 5 == 0:
        try:
            save_cats(switch_get_value(Switch.clan_name), Cat, game)
            game.clan.save_clan()
            game.clan.save_pregnancy(game.clan)
            game.save_events()
        except:
            SaveErrorWindow(traceback.format_exc())

    if game.clan.your_cat.status.alive_in_your_cat_group:
        if game.clan.your_cat.moons == 0:
            generate_birth_event()
        elif game.clan.your_cat.moons < 6:
            generate_kit_events()
        elif game.clan.your_cat.status.is_outsider:
            # Outsiders (kittypet/loner/rogue) don't get Clan ceremonies
            # show a short message when they reach a new age
            if game.clan.your_cat.moons in (6, 12, 120):
                generate_outsider_age_ceremony()
            else:
                generate_lifegen_events()
        elif game.clan.your_cat.moons == 6:
            generate_app_ceremony()
        elif game.clan.your_cat.status.rank.is_any_apprentice_rank():
            generate_lifegen_events()
        elif (
            game.clan.your_cat.status.rank in (
                CatRank.WARRIOR,
                CatRank.MEDICINE_CAT,
                CatRank.MEDIATOR,
                CatRank.QUEEN
                ) and
                not game.clan.your_cat.w_done and
                not game.clan.your_cat.status.is_shunned()
                ):
            generate_ceremony()
        elif game.clan.your_cat.status.rank != CatRank.ELDER and game.clan.your_cat.moons != 119:
            generate_lifegen_events()
        elif (
            game.clan.your_cat.moons == 119 and
            game.clan.your_cat.status.alive_in_player_clan and
            not game.clan.your_cat.status.is_shunned()
            ):
            if 'retire' not in switch_get_value(Switch.windows_dict):
                switch_append_list_value(Switch.windows_dict, 'retire')
        elif (
            game.clan.your_cat.moons == 120 and
            game.clan.your_cat.status.rank == CatRank.ELDER and
            game.clan.your_cat.status.alive_in_player_clan and
            not game.clan.your_cat.status.is_shunned()
            ):
            generate_elder_ceremony()
        elif game.clan.your_cat.status.rank == CatRank.ELDER:
            generate_lifegen_events()

        if game.clan.your_cat.moons >= 12:
            if not game.clan.your_cat.status.is_shunned():
                check_gain_app(checks)
            check_gain_mate(checks)
            check_gain_kits(checks)
            if not game.clan.your_cat.status.is_shunned():
                check_retire()

        if not int(random.random() * 10) and game.clan.your_cat.status.rank != CatRank.NEWBORN:
            gain_acc()

    elif game.clan.your_cat.dead and game.clan.your_cat.dead_for == 0:
        generate_death_event()
    elif game.clan.your_cat.dead:
        generate_lifegen_events()
        
    # LIFEGEN
    # murdered dict clears after six moons of no murder attempts
    if "moon" in game.clan.murdered:
        if game.clan.age - game.clan.murdered["moon"] >= 6:
            game.clan.murdered = {}

    game.clan.affair = False
    game.clan.exile_return = False

    generate_dialogue_focus()
    checks = [
        len(game.clan.your_cat.apprentice),
        len(game.clan.your_cat.mate),
        len(game.clan.your_cat.inheritance.get_blood_kits()) if game.clan.your_cat.inheritance else 0,
        None
        ]
    if game.clan.leader:
        checks[3] = game.clan.leader.ID
        
    # Resort
    if switch_get_value(Switch.sort_type) != "id":
        Cat.sort_cats()

    # Clear all the loaded event dicts.
    GenerateEvents.clear_loaded_events()

    # autosave
    if get_clan_setting("autosave") and game.clan.age % 5 == 0:
        try:
            save_cats(switch_get_value(Switch.clan_name), Cat, game)
            game.clan.save_clan()
            game.clan.save_pregnancy(game.clan)
            game.save_events()
        except:
            SaveErrorWindow(traceback.format_exc())

    # ACHIEVEMENTS
    new_achievements = check_achievements(Cat, eventspage=True)

    achievements_list = []
    all_achievements = load_lang_resource("achievements.json")
    for item in new_achievements:
        achievements_list.append(f"<b>{all_achievements[item][0]}</b>")

    
    if achievements_list:
        if len(achievements_list) == 1:
            pre_string = "You've earned an achievement this moon: "
        else:
            pre_string = f"You've earned {len(achievements_list)} achievements this moon: "

        string = adjust_list_text(achievements_list)
        game.cur_events_list.insert(0, Single_Event((pre_string + string + "!"), "alert"))
    # ---


def update_afterlife_temper():
    """
    Updates the temperaments of the afterlives based off cats who have newly joined an afterlife.
    """
    for c in game.updated_afterlife_cats:
        if not c.status.did_join_group_this_moon:
            continue

        # only high ranks and guides can influence
        if (
            c.status.rank
            not in (
                CatRank.LEADER,
                CatRank.MEDICINE_CAT,
                CatRank.DEPUTY,
            )
            and c not in [game.clan.instructor] + [clan.instructor for clan in game.clan.all_other_clans]
        ):
            continue

        # first change facets of the group they joined
        if (
            c.status.group == CatGroup.STARCLAN
            and c.ID not in game.starclan.influencing_cats
        ):
            game.starclan.adjust_facets_by_cat(c)
            # then remove them from other afterlife, if they were there
            if c.ID in game.dark_forest.influencing_cats:
                game.dark_forest.adjust_facets_by_cat(c, do_removal=True)

        # now do same for DF
        elif (
            c.status.group == CatGroup.DARK_FOREST
            and c.ID not in game.dark_forest.influencing_cats
        ):
            game.dark_forest.adjust_facets_by_cat(c)
            if c.ID in game.starclan.influencing_cats:
                game.starclan.adjust_facets_by_cat(c, do_removal=True)

    game.updated_afterlife_cats.clear()


def trigger_future_events(clan):
    """
    Handles aging and triggering future events.
    """
    removals = []

    for event in game.clan.future_events:
        if event.clan != clan.group_ID:
            continue
        event.moon_delay -= 1
        # we give events a buffer of 12 moons to allow any season-locked events a chance to trigger, then we remove
        if event.moon_delay <= -12:
            removals.append(event)
            continue
        # attempt to trigger event
        if event.moon_delay <= 0:
            create_short_event(
                event_type=event.event_type,
                main_cat=Cat.fetch_cat(event.involved_cats.get("m_c")),
                random_cat=Cat.fetch_cat(event.involved_cats.get("r_c")),
                victim_cat=Cat.fetch_cat(event.involved_cats.get("mur_c")),
                sub_type=event.pool.get("sub_type"),
                future_event=event,
                clan=clan
            )
            if event.triggered:
                removals.append(event)

    for event in removals:
        if event in game.clan.future_events:
            game.clan.future_events.remove(event)

def handle_lead_den_event():
    """
    Handles the events that are chosen in the leaders den the previous moon and resets the relevant clan settings
    """
    if get_clan_setting("lead_den_clan_event"):
        info_dict = get_clan_setting("lead_den_clan_event")
        gathering_cat = Cat.fetch_cat(info_dict["cat_ID"])

        # drop the event if the gathering cat is no longer available
        if not gathering_cat.status.alive_in_player_clan:
            return

        other_clan = get_other_clan(info_dict["other_clan"])

        # get events
        events = generate_events.possible_lead_den_events(
            cat=gathering_cat,
            other_clan_temper=other_clan.temperament,
            player_clan_temper=info_dict["player_clan_temper"],
            event_type="other_clan",
            interaction_type=info_dict["interaction_type"],
            success=info_dict["success"],
        )
        chosen_event = random.choice(events)

        # get text
        event_text = chosen_event["event_text"]

        # change relations and append relation text
        rel_change = chosen_event["rel_change"]
        game.clan.set_relations(game.clan, other_clan, None, rel_change)
        if rel_change > 0:
            event_text += i18n.t("hardcoded.relations_improved")
        elif rel_change == 0:
            event_text += i18n.t("hardcoded.relations_neutral")
        else:
            event_text += i18n.t("hardcoded.relations_worsened")

        # adjust text and add to event list
        event_text = event_text_adjust(
            Cat,
            event_text,
            main_cat=gathering_cat,
            other_clan=other_clan,
            clan=game.clan,
        )
        game.cur_events_list.insert(
            4, Single_Event(event_text, "other_clans", [gathering_cat.ID], clan=game.clan.group_ID)
        )

        set_clan_setting("lead_den_clan_event", {})

    if get_clan_setting("lead_den_outsider_event"):
        info_dict = get_clan_setting("lead_den_outsider_event")
        outsider_cat = Cat.fetch_cat(info_dict["cat_ID"])
        involved_cats = [outsider_cat.ID]
        invited_cats = []

        events = generate_events.possible_lead_den_events(
            cat=outsider_cat,
            event_type="outsider",
            interaction_type=info_dict["interaction_type"],
            success=info_dict["success"],
        )
        chosen_event = random.choice(events)

        # get event text
        event_text = chosen_event["event_text"]
        cat_dict = chosen_event["m_c"]

        # ADJUST REP
        game.clan.reputation += chosen_event["rep_change"]

        additional_kits = None
        # SUCCESS/FAIL
        if info_dict["success"]:
            if info_dict["interaction_type"] == "hunt":
                outsider_cat.history.add_death(
                    death_text=history_text_adjust(
                        i18n.t("hardcoded.lead_den_killed"),
                        other_clan_name=None,
                        clan=game.clan,
                    ),
                )
                outsider_cat.die()

            elif info_dict["interaction_type"] == "drive":
                outsider_cat.status.change_group_nearness(CatGroup.PLAYER_CLAN_ID)

            elif info_dict["interaction_type"] in ("invite", "search"):
                # ADD TO CLAN AND CHECK FOR KITS
                additional_kits = outsider_cat.add_to_clan()

                if additional_kits:
                    event_text += i18n.t(
                        "hardcoded.event_lost_kits", count=len(additional_kits)
                    )

                    for kit_ID in additional_kits:
                        # add to involved cat list
                        involved_cats.append(kit_ID)

                invited_cats = [outsider_cat.ID]
                invited_cats.extend(additional_kits)

                for cat_ID in invited_cats:
                    invited_cat = Cat.fetch_cat(cat_ID)
                    # some things to handle if the cat has not been in the clan before
                    if (
                        CatStanding.EXILED
                        not in invited_cat.status.get_standing_with_group(
                            CatGroup.PLAYER_CLAN_ID
                        )
                    ):
                        # reset to make sure backstory makes sense
                        if "guided" in invited_cat.backstory:
                            invited_cat.backstory = "outsider1"
                        # if the cat is a healer, give healer rank
                        elif (
                            invited_cat.backstory
                            in BACKSTORIES["backstory_categories"][
                                "healer_backstories"
                            ]
                        ):
                            if invited_cat.age == CatAge.ADOLESCENT:
                                invited_cat.status._change_rank(CatRank.MEDICINE_APPRENTICE)
                            else:
                                invited_cat.status._change_rank(CatRank.MEDICINE_CAT)
                        # if cat is a little baby, check name
                        elif invited_cat.age in (CatAge.NEWBORN, CatAge.KITTEN):
                            if not invited_cat.name.suffix:
                                invited_cat.name = Name(
                                    invited_cat,
                                    invited_cat.name.prefix,
                                    invited_cat.name.suffix,
                                    biome=game.clan.biome,
                                )
                                invited_cat.name.give_suffix(
                                    skills=invited_cat.skills,
                                    personality=invited_cat.personality,
                                    biome=game.clan.biome
                                    if not game.clan.override_biome
                                    else game.clan.override_biome,
                                )
                                invited_cat.specsuffix_hidden = False
                        # if cat is an apprentice, make sure they get a mentor!
                        if invited_cat.status.rank.is_any_apprentice_rank():
                            invited_cat.update_mentor()
                        # if the cat chose to become a mediator but the settings don't allow it, make them a warrior instead
                        if (
                            invited_cat.status.rank == CatRank.MEDIATOR
                            and not get_clan_setting("become_mediator")
                        ):
                            invited_cat.status._change_rank(CatRank.WARRIOR)

                    invited_cat.create_relationships_new_cat()

            # this handles ceremonies for cats coming into the clan
            if invited_cats:
                handle_lost_cats_return(invited_cats)

        # give new thought to cats
        if "new_thought" in cat_dict:
            outsider_cat.thought = event_text_adjust(
                Cat,
                text=cat_dict["new_thought"],
                main_cat=outsider_cat,
                clan=game.clan)

        if "kit_thought" in cat_dict:
            if additional_kits is None:
                additional_kits = outsider_cat.get_children()
            if additional_kits:
                for kit_ID in additional_kits:
                    kit = Cat.fetch_cat(kit_ID)
                    if kit.dead:
                        continue
                    kit.thought = event_text_adjust(
                        Cat,
                        text=cat_dict["kit_thought"],
                        main_cat=kit,
                        clan=game.clan)

        if "relationships" in cat_dict:
            unpack_rel_block(Cat, cat_dict["relationships"], extra_cat=outsider_cat, clan=game.clan)

        # adjust text and add to event list
        event_text = event_text_adjust(
            Cat,
            text=event_text,
            main_cat=outsider_cat,
            clan=game.clan,
        )

        game.cur_events_list.insert(
            4, Single_Event(event_text, "misc", involved_cats, clan=game.clan.group_ID)
        )
        set_clan_setting("lead_den_outsider_event", {})

    set_clan_setting("lead_den_interaction", False)
    
def auto_freshkill():
    """Adds amount of freshkill needed for the Clan"""
    # auto freshkill toggle btw
    # TODO: use this function to update the freshkill pile when
    # the MC switches groups
    if not game.clan.freshkill_pile:
        game.clan.freshkill_pile = FreshkillPile()

    current_amount = game.clan.freshkill_pile.total_amount
    needed_amount = game.clan.freshkill_pile.amount_food_needed()
    target_amount = needed_amount * 2
    amount_to_add = 0
    if current_amount < target_amount:
        amount_to_add = target_amount - current_amount
    return amount_to_add

def generate_dialogue_focus():
    """Handles dialogue focus for each moon, generating conditional focuses for specific events (war, starving) or random chance focuses (valentines, quality of leadership)"""
    resource_dir = "resources/dicts/"
    with open(f"{resource_dir}dialogue_focuses.json",
            encoding="ascii") as read_file:
        dialogue_focuses = ujson.loads(read_file.read())
    
    # Handle lost focus for conditional focuses that have no set duration
    if game.clan.focus == "war" and not get_warring_clan():
        game.clan.focus = ""
        game.clan.focus_moons = 0
    # LG: classic mode has no fresh-kill pile, so there's no starving focus there
    pile = game.clan.freshkill_pile
    if game.clan.focus == "starving" and (not pile or pile.total_amount > pile.amount_food_needed()*0.5):
        game.clan.focus = ""
        game.clan.focus_moons = 0
        for clan_cat in game.clan.clan_cats:
            clan_cat_cat = Cat.fetch_cat(clan_cat)
            if clan_cat_cat:
                clan_cat_cat.faith -= round(random.uniform(-1,0), 2)

    # Handle lost focus for focuses that have set duration
    if game.clan.focus and dialogue_focuses[game.clan.focus]["duration"] != -1 and game.clan.focus_moons >= dialogue_focuses[game.clan.focus]["duration"]:
        if "focus_loss" in dialogue_focuses[game.clan.focus]:
            game.cur_events_list.append(Single_Event(lifegen_process_text(random.choice(dialogue_focuses[game.clan.focus]["focus_loss"])), "misc"))
        game.clan.focus = ""
        game.clan.focus_moons = 0
        game.clan.focus_cat = None
        
    if not game.clan.focus:
        debug_focus = constants.CONFIG["lifegen"]["debug"]["debug_ensure_focus"]
        if debug_focus and debug_focus in dialogue_focuses:
            game.clan.focus = debug_focus
        elif get_warring_clan():
            game.clan.focus = "war"
        elif pile and pile.total_amount < pile.amount_food_needed()*0.5:
            game.clan.focus = "starving"
        elif random.randint(1,30) == 1:
            possible_focuses = ["valentines", "hailstorm"]
            if game.clan.leader and game.clan.leader.status.alive_in_player_clan and game.clan.leader.ID != game.clan.your_cat.ID:
                possible_focuses.append("leader")
            focus_chosen = random.choice(possible_focuses)
            if dialogue_focuses[focus_chosen]["season"] == "Any" or dialogue_focuses[focus_chosen]["season"] == game.clan.current_season:
                game.clan.focus = focus_chosen

    if game.clan.focus:
        game.clan.focus_moons += 1
        if game.clan.focus_moons == 1 and dialogue_focuses[game.clan.focus]["moon_event"]:
            game.cur_events_list.insert(0, Single_Event(lifegen_process_text(random.choice(dialogue_focuses[game.clan.focus]["moon_event"])), "misc"))

            
def gain_acc():
    if get_clan_setting("all accessories"):
        return
    acc_list = []
    if game_setting_get("lifegen_sprite_changes"):
        acc_list.extend(Pelt.all_lifegen_accessories)
    else:
        acc_list.extend(Pelt.all_clangen_accessories)

    if not game.clan.your_cat.pelt.inventory:
        game.clan.your_cat.pelt.inventory = []
    acc = random.choice(acc_list)
    counter = 0
    while acc in game.clan.your_cat.pelt.inventory:
        counter+=1
        if counter == 30:
            break
        acc = random.choice(acc_list)
    game.clan.your_cat.pelt.inventory.append(acc)
    string = f"You found a new accessory, acc_singular! You choose to store it in a safe place for now."
    string = string.replace("acc_singular", str(i18n.t(get_acc_name(acc).lower(), count=1)))
    game.cur_events_list.insert(0, Single_Event(string, "alert", game.clan.your_cat.ID))

def get_acc_name(acc):
    """ grabs accessory names for display in the customiser """
    acc_name = str(i18n.t(f"cat.accessories.{acc}", count=0)).capitalize()
    collar_found = False
    if acc in Pelt.collar_accessories:
        for style_type in sprites.COLLAR_DATA["style_data"]:
            for style, color_list in style_type.items():
                for colour in color_list:
                    if f"{style}_{colour}" == acc:
                        collar_found = True
                        acc_name = str(i18n.t(f"cat.accessories.{style}", count=0)).capitalize()
                        break
                    if collar_found:
                        break
                if collar_found:
                    break
            if collar_found:
                break

            # wtaf

    return acc_name

# LG: genes for the parents made up for your cat's birth. Your cat's genes come first (you pick
# their look), so the made-up parents are given genes that could have made your cat
PARENT_GENE_PAIRS = [
    "furLength", "eumelanin", "dilute", "white", "pointgene", "silver", "agouti", "mack", "ticked",
    "wirehair", "laperm", "cornish", "urals", "tenn", "fleece", "sedesp", "ruhr", "ruhrmod", "lykoi",
    "pinkdilute", "dilutemd", "ext", "corin", "karp", "bleach", "ghosting", "satin", "glitter",
    "curl", "fold", "fourear", "manx", "kab", "toybob", "jbob", "kub", "ring", "munch", "poly", "pax3",
]
PARENT_POLYGENES = ["wideband", "rufousing", "unders_ruf", "bengal", "sokoke", "spotted", "tickgenes"]


def _is_pair(genes):
    return isinstance(genes, list) and len(genes) == 2


def _match_gene_pair(kit_pair, parent_pairs):
    """Each parent gets one of the kit's two copies (changing as few as possible)"""
    if len(parent_pairs) == 1:
        pair = parent_pairs[0]
        if kit_pair[0] not in pair and kit_pair[1] not in pair:
            pair[random.randint(0, 1)] = random.choice(kit_pair)
        return
    a, b = kit_pair
    orders = [(a, b), (b, a)]
    random.shuffle(orders)
    first, second = min(
        orders,
        key=lambda o: (o[0] not in parent_pairs[0]) + (o[1] not in parent_pairs[1]),
    )
    for allele, pair in ((first, parent_pairs[0]), (second, parent_pairs[1])):
        if allele not in pair:
            pair[random.randint(0, 1)] = allele


def _match_sex_genes(kit_genes, parent_genes):
    """X genes (like orange): a mother passes one of hers, a father his only X (or his Y)"""
    if len(kit_genes.sexgene) != 2 or any(len(g.sexgene) != 2 for g in parent_genes):
        return
    fathers = [g for g in parent_genes if "Y" in g.sexgene]
    if len(parent_genes) == 2:
        if len(fathers) == 1:
            father = fathers[0]
            mother = parent_genes[0] if parent_genes[1] is father else parent_genes[1]
        else:
            # same sex parents
            mother, father = random.sample(parent_genes, 2)
    elif fathers:
        mother, father = None, parent_genes[0]
    else:
        mother, father = parent_genes[0], None

    def mother_slots():
        return [i for i, x in enumerate(mother.sexgene) if x != "Y"] or [0]

    def mother_xs():
        return [mother.sexgene[i] for i in mother_slots()]

    def father_slot():
        return 1 if father.sexgene[0] == "Y" else 0

    if "Y" in kit_genes.sexgene:
        # the X came from the mother, the Y from the father
        kit_x = kit_genes.sexgene[1] if kit_genes.sexgene[0] == "Y" else kit_genes.sexgene[0]
        if mother and kit_x not in mother_xs():
            mother.sexgene[random.choice(mother_slots())] = kit_x
        return

    a, b = kit_genes.sexgene
    if mother and father:
        orders = [(a, b), (b, a)]
        random.shuffle(orders)
        from_mother, from_father = min(
            orders,
            key=lambda o: (o[0] not in mother_xs()) + (o[1] != father.sexgene[father_slot()]),
        )
        if from_mother not in mother_xs():
            mother.sexgene[random.choice(mother_slots())] = from_mother
        father.sexgene[father_slot()] = from_father
    elif mother:
        if a not in mother_xs() and b not in mother_xs():
            mother.sexgene[random.choice(mother_slots())] = random.choice([a, b])
    elif father.sexgene[father_slot()] not in (a, b):
        father.sexgene[father_slot()] = random.choice([a, b])


def _match_polygene(kit_value, parent_values):
    """Polygenes are counts (0-2) at each spot: a 0 passes nothing, a 2 always passes one, a 1 either"""

    def passes(value):
        return {0: (0,), 1: (0, 1), 2: (1,)}[value]

    def possible(values):
        if len(values) == 1:
            return any(0 <= kit_value - g <= 1 for g in passes(values[0]))
        return any(g1 + g2 == kit_value for g1 in passes(values[0]) for g2 in passes(values[1]))

    if possible(parent_values):
        return parent_values
    if len(parent_values) == 1:
        options = [[v] for v in range(3)]
    else:
        options = [[v1, v2] for v1 in range(3) for v2 in range(3)]
    options = [o for o in options if possible(o)]
    random.shuffle(options)
    return min(options, key=lambda o: sum(abs(new - old) for new, old in zip(o, parent_values)))


def _redraw_from_genes(cat):
    """Remakes a cat's look from their (changed) genes, the same way a new cat gets it"""
    genes = cat.phenotype
    genes.GeneSort()
    genes.PolyEval()
    # eye color depends on genes like dilute and colorpoint too (keeps their eye grades)
    genes.deaf = False
    genes.EyeColourFinder()
    genes.white_pattern = []
    genes.PhenotypeOutput(genes.white_pattern)
    genes.SpriteInfo(cat.moons)
    genes.white_pattern = Pelt.generate_white(
        genes.white, genes.pointgene, genes.whitegrade, genes.vitiligo, None, genes.pax3
    )
    if genes.maincolour == "white" and not genes.patchmain:
        genes.white_pattern = "No"
    old_pelt = cat.pelt
    cat.pelt = Pelt.generate_new_pelt(genes, cat.age)
    for attr in ("scars", "accessory", "inventory", "reverse"):
        if hasattr(old_pelt, attr):
            setattr(cat.pelt, attr, getattr(old_pelt, attr))
    cat.genetic_conditions()


def match_parents_to_kit(kit, parents):
    """Gives parents made up for your cat's birth genes that could have made your cat.
    Only the parents change, your cat keeps the look you picked."""
    parents = [p for p in parents if p]
    if not parents:
        return
    # a chimera parent passes on their main genes
    for parent in parents:
        if parent.chimerapheno:
            parent.passes = 1
    kit_genes = kit.phenotype
    parent_genes = [p.phenotype for p in parents]

    for gene in PARENT_GENE_PAIRS:
        kit_pair = kit_genes[gene]
        parent_pairs = [g[gene] for g in parent_genes]
        if _is_pair(kit_pair) and all(_is_pair(pair) for pair in parent_pairs):
            _match_gene_pair(kit_pair, parent_pairs)

    _match_sex_genes(kit_genes, parent_genes)

    for gene in PARENT_POLYGENES:
        kit_string = kit_genes[gene]
        # (newer Genemod keeps some of these as a blended number instead)
        if not isinstance(kit_string, str) or any(
            not isinstance(g[gene], str) or len(g[gene]) != len(kit_string) for g in parent_genes
        ):
            continue
        new_strings = [""] * len(parent_genes)
        for i, kit_value in enumerate(kit_string):
            values = _match_polygene(int(kit_value), [int(g[gene][i]) for g in parent_genes])
            for j, value in enumerate(values):
                new_strings[j] += str(value)
        for g, new_string in zip(parent_genes, new_strings):
            setattr(g, gene, new_string)

    for parent in parents:
        _redraw_from_genes(parent)


def generate_birth_event():
    '''Handles birth event generation and creation of inheritance for your cat'''

    # idk how to do weights the real way. dont look at me
    weighted_birth_types = []
    if get_your_cat_group_count(Cat) == 1:
        birth_type = BirthType.ALONE
    else:
        mc_group = game.clan.your_cat.status.group_ID
        for birthtype, weight in BirthType.birth_type_weights(BirthType, mc_group=mc_group).items():
            if not get_clan_setting("single parentage"):
                if birthtype in [BirthType.ONE_PARENT, BirthType.ONE_OUTSIDER_PARENT]:
                    continue
            if get_your_cat_group_count(Cat) < 3:
                if birthtype in [BirthType.TWO_ADOPTIVE_PARENTS, BirthType.TWO_PARENTS]:
                    continue
            for i in range(weight):
                weighted_birth_types.append(birthtype)

        birth_type = random.choice(weighted_birth_types)
    # debug
    # birth_type = BirthType.TWO_PARENTS

    outside_groups = game.clan.your_cat.status.group.get_all_outside_groups_IDs()
    made_up_parents = []

    def create_siblings(parent1, parent2, adoptive_parents):
        '''Creates siblings for your cat'''
        num_siblings = random.randint(1,4)
        kits = Pregnancy_Events.get_kits(kits_amount=num_siblings, cat=parent1, other_cat=[parent2] if parent2 else None, adoptive_parents=adoptive_parents, clan=game.clan)
        for kit in kits:
            kit.status = deepcopy(game.clan.your_cat.status)
            if kit.status.is_clancat and kit.status.rank != CatRank.NEWBORN:
                kit.status._change_rank(CatRank.NEWBORN)
            kit.age = CatAge.NEWBORN
            kit.backstory = game.clan.your_cat.backstory
            if not game.clan.your_cat.status.group.is_any_clan_group():
                kit.specsuffix_hidden = True
                kit.change_name(new_prefix=kit.name.prefix, new_suffix="")
        return kits
    
    def generate_outsider_parent(group=None, mate=None, dead=False, arrived=False):
        """
        Generates an outsider parent for the MC
        
        :param group: The group the parent will be a part of. Will be a random non-MC group if unspecified.
        :param mate: The Cat object of the first parent, if there is one.
        :param dead: If the parent is dead before MC is born.
        :param arrived: If the parent comes to the Clan from outside with the MC (the one outsider parent birth).
        """
        if group:
            parent_group = group
        elif mate:
            if mate.dead:
                parent_group = mate.status.group_history[-2]["group"]
            else:
                parent_group = mate.status.group_ID
        else:
            parent_group = random.choice(outside_groups)
        
        # a dictionary containing certain attributes that will change
        # depending on which group the parent is a part of.
        # TODO: choose an existing clan cat to be parent if playerclan is chosen
        attribute_dict = {
            CatGroup.PLAYER_CLAN_ID: {
                "possible_ranks": [
                    CatRank.WARRIOR,
                    CatRank.WARRIOR,
                    CatRank.WARRIOR,
                    CatRank.WARRIOR,
                    CatRank.MEDIATOR,
                    CatRank.QUEEN,
                    CatRank.MEDICINE_CAT,
                    CatRank.MEDICINE_CAT
                    ],
                "cat_social": CatSocial.CLANCAT,
                "outside": False,
                "possible_backstories": BACKSTORIES["backstory_categories"]["clanborn_backstories"]
            },
            CatGroup.ROGUE_GROUP_ID: {
                "possible_ranks": [CatRank.ROGUE],
                "cat_social": CatSocial.ROGUE,
                "outside": True,
                "possible_backstories": BACKSTORIES["backstory_categories"]["current_rogue_backstories"]
            },
            CatGroup.LONER_GROUP_ID: {
                "possible_ranks": [CatRank.LONER],
                "cat_social": CatSocial.LONER,
                "outside": True,
                "possible_backstories": BACKSTORIES["backstory_categories"]["current_loner_backstories"]
            },
            CatGroup.HOUSEHOLD_ID: {
                "possible_ranks": [CatRank.KITTYPET],
                "cat_social": CatSocial.KITTYPET,
                "outside": True,
                "possible_backstories": BACKSTORIES["backstory_categories"]["current_kittypet_backstories"]
            },
            None: {
                "possible_ranks": [CatRank.LONER],
                "cat_social": CatSocial.LONER,
                "outside": True,
                "possible_backstories": BACKSTORIES["backstory_categories"]["current_loner_backstories"]
            }
        }

        parent1_rank = random.choice(attribute_dict[parent_group]["possible_ranks"])
        parent1_outside = attribute_dict[parent_group]["outside"]
        parent1_social = attribute_dict[parent_group]["cat_social"]
        parent1_backstory = random.choice(attribute_dict[parent_group]["possible_backstories"])
        # LG: a parent made inside your Clan was always Clanborn
        if parent_group == CatGroup.PLAYER_CLAN_ID:
            if arrived:
                # they come to the Clan from outside, with your cat
                parent1_backstory = random.choice(["loner1", "rogue1", "kittypet1"])
            elif game.clan.clan_age == "new" and game.clan.age < 1:
                # a brand new Clan's first cats are its founders
                parent1_backstory = random.choice(BACKSTORIES["backstory_categories"]["clan_founder_backstories"])

        parent1_gender = None
        if mate and not get_clan_setting("same sex birth"):
            if mate.gender in ("female", "molly"):
                parent1_gender = "male"
            else:
                parent1_gender = "female"

        parent1 = create_new_cat(
            Cat,
            alive=True,
            new_name=True if parent_group == CatGroup.PLAYER_CLAN_ID else False,
            moons=random.randint(15,120) if not mate else (mate.moons),
            original_social=parent1_social,
            rank=parent1_rank,
            gender=parent1_gender,
            original_group=parent_group,
            backstory=parent1_backstory,
            outside=parent1_outside
            )[0]
        parent1.thought = event_text_adjust(
            Cat,
            text = "Is glad that {PRONOUN/m_c/poss} kits are safe",
            main_cat = parent1
        )
        if dead:
            parent1.die()
        made_up_parents.append(parent1)
        return parent1

    def is_valid_parent(cat, other_parent, adoptive=False):

        is_relation_compatible = (other_parent is None) or (other_parent and cat.is_potential_mate(other_parent))
        is_gender_compatible = True
        if not get_clan_setting("same sex birth") and not adoptive:
            is_gender_compatible = (other_parent is None) or (other_parent and cat.gender != other_parent.gender)

        valid = (
            cat.ID != game.clan.your_cat.ID
            and (
                not other_parent or
                    (
                        other_parent and
                        cat.ID != other_parent.ID
                    )
                )
            and cat.status.alive_in_your_cat_group
            and cat.age.can_have_mate()
            and is_gender_compatible
            and is_relation_compatible
        )
        return valid

    def pick_valid_parent(other_parent=None, adoptive=False):
        cat_options = game.clan.your_cat.get_cats_in_your_group()

        valid_parents = [
            cat for cat in cat_options
            if is_valid_parent(cat, other_parent, adoptive)
        ]
        if valid_parents:
            return random.choice(valid_parents)
        return None

    def get_parents(birth_type):
        '''Handles creating inheritance for your cat'''
        # try:
        parent1 = None
        parent2 = None
        adoptive_parents = []
        if birth_type in [BirthType.NO_PARENTS, BirthType.ALONE]:
            parent1 = generate_outsider_parent(dead=True)

        elif birth_type == BirthType.ONE_PARENT:
            parent1 = pick_valid_parent()
            if parent1.mate:
                parent2 = Cat.fetch_cat(parent1.mate[-1])
                birth_type = BirthType.TWO_PARENTS
            if not parent1:
                birth_type = BirthType.NO_PARENTS

        elif birth_type == BirthType.TWO_PARENTS:
            parent1 = pick_valid_parent()
            parent2 = pick_valid_parent(parent1)
            if parent2 and parent2.ID not in parent1.mate:
                parent1.set_mate(parent2)
            elif not parent2:
                parent2 = pick_valid_parent(parent1, adoptive=True)
                if parent2:
                    birth_type = BirthType.TWO_ADOPTIVE_PARENTS
                    adoptive_parents = [parent1, parent2]
                    parent1 = None
                    parent2 = None
                else:
                    birth_type = BirthType.ONE_PARENT

        elif birth_type in [BirthType.ONE_ADOPTIVE_PARENT, BirthType.TWO_ADOPTIVE_PARENTS]:
            if birth_type == BirthType.ONE_ADOPTIVE_PARENT:
                adoptive_parent1 = pick_valid_parent(adoptive=True)
                adoptive_parents = [adoptive_parent1.ID]
                if adoptive_parent1.mate:
                    for cat in adoptive_parent1.mate:
                        adoptive_parents.append(cat)
                    birth_type = BirthType.TWO_ADOPTIVE_PARENTS
            else:
                adoptive_parent1 = pick_valid_parent(adoptive=True)
                adoptive_parent2 = pick_valid_parent(adoptive_parent1, adoptive=True)
                if adoptive_parent2:
                    adoptive_parent1.set_mate(adoptive_parent2)
                    adoptive_parents = [adoptive_parent1.ID, adoptive_parent2.ID]
                else:
                    birth_type = BirthType.ONE_ADOPTIVE_PARENT
                    adoptive_parents = [adoptive_parent1.ID]

            # dead outsider parents
            # create parent, assign thought
            parent1 = generate_outsider_parent(dead=True)
            parent1.thought = event_text_adjust(
                Cat,
                text="Is glad {PRONOUN/m_c/poss} kits are safe",
                main_cat=parent1
            )
            parent2 = generate_outsider_parent(
                group=parent1.status.group_history[-2]["group"],
                mate=parent1,
                dead=True
            )
            parent2.thought = event_text_adjust(
                Cat,
                text="Is glad {PRONOUN/m_c/poss} kits are safe",
                main_cat=parent2
            )
            parent1.set_mate(parent2)

        elif birth_type == BirthType.ONE_OUTSIDER_PARENT:
            parent1 = generate_outsider_parent(group=game.clan.your_cat.status.group_ID, dead=False, arrived=True)

        elif birth_type == BirthType.TWO_OUTSIDER_PARENTS:
            parent1 = generate_outsider_parent(group=game.clan.your_cat.status.group_ID, dead=False)
            parent2 = generate_outsider_parent(
                group=game.clan.your_cat.status.group_ID,
                mate=parent1,
                dead=False
                )
            parent1.set_mate(parent2)
            parent1.init_all_relationships()
            parent2.init_all_relationships()

        elif birth_type in (
            BirthType.TWO_KITTYPET_PARENTS,
            BirthType.TWO_LONER_PARENTS,
            BirthType.TWO_ROGUE_PARENTS,
            BirthType.MIXED_OUTSIDER_PARENTS,
        ):
            same_group_map = {
                BirthType.TWO_KITTYPET_PARENTS: CatGroup.HOUSEHOLD_ID,
                BirthType.TWO_LONER_PARENTS: CatGroup.LONER_GROUP_ID,
                BirthType.TWO_ROGUE_PARENTS: CatGroup.ROGUE_GROUP_ID,
            }
            if birth_type == BirthType.MIXED_OUTSIDER_PARENTS:
                group1, group2 = random.sample(
                    [CatGroup.HOUSEHOLD_ID, CatGroup.LONER_GROUP_ID, CatGroup.ROGUE_GROUP_ID],
                    2,
                )
            else:
                group1 = group2 = same_group_map[birth_type]

            parent1 = generate_outsider_parent(group=group1, dead=False)
            parent2 = generate_outsider_parent(group=group2, mate=parent1, dead=False)
            parent1.set_mate(parent2)
            parent1.init_all_relationships()
            parent2.init_all_relationships()

        return birth_type, parent1, parent2, adoptive_parents

    def handle_backstory(siblings):
        '''Handles creating backstories for your cat'''
        backstory = ""

        # LG: outsider MCs (kittypet/loner/rogue) get a "current" backstory
        mc_group = game.clan.your_cat.status.group_ID
        outsider_bs_categories = {
            CatGroup.HOUSEHOLD_ID: "current_kittypet_backstories",
            CatGroup.LONER_GROUP_ID: "current_loner_backstories",
            CatGroup.ROGUE_GROUP_ID: "current_rogue_backstories",
        }
        if mc_group in outsider_bs_categories:
            backstory = random.choice(
                BACKSTORIES["backstory_categories"][outsider_bs_categories[mc_group]]
            )
        elif birth_type in [BirthType.NO_PARENTS, BirthType.ONE_ADOPTIVE_PARENT, BirthType.TWO_ADOPTIVE_PARENTS]:
            backstory = random.choice(["abandoned1", "abandoned2", "abandoned4", "loner3", "orphaned1", "orphaned2", "orphaned3", "orphaned4", "orphaned5", "orphaned6", "orphaned7", "outsider1"])
        elif birth_type == BirthType.ONE_PARENT:
            backstory = random.choice(["halfclan1", "halfclan4", "halfclan4", "halfclan5", "halfclan6", "halfclan7", "halfclan8", "halfclan9", "halfclan10", "outsider_roots1", "outsider_roots3", "outsider_roots4", "outsider_roots5", "outsider_roots6", "outsider_roots7", "outsider_roots8", "clanborn"])
        elif birth_type == BirthType.TWO_PARENTS:
            backstory = "clanborn"
        elif birth_type == BirthType.ONE_OUTSIDER_PARENT:
            backstory = "outsider1"
        elif birth_type == BirthType.TWO_KITTYPET_PARENTS:
            backstory = random.choice(["kittypet1", "kittypet2", "kittypet3", "kittypet4", "kittypet5"])
        elif birth_type == BirthType.TWO_LONER_PARENTS:
            backstory = random.choice(["loner1", "loner2", "outsider1", "outsider4"])
        elif birth_type == BirthType.TWO_ROGUE_PARENTS:
            backstory = random.choice(["rogue1", "rogue2", "rogue3", "rogue4", "rogue5"])
        elif birth_type == BirthType.MIXED_OUTSIDER_PARENTS:
            backstory = random.choice(["outsider1", "outsider2", "outsider3", "outsider4", "outsider5", "outsider6"])
        else:
            backstory = "outsider1"

        game.clan.your_cat.backstory = backstory
        if siblings:
            for sibling in siblings:
                sibling.backstory = backstory
    
    def handle_inheritance(parent1, parent2, adoptive_parents, siblings):            
        for c in siblings + [game.clan.your_cat]:
            if parent1:
                c.parent1 = parent1.ID
            if parent2:
                c.parent2 = parent2.ID
            if adoptive_parents:
                c.adoptive_parents = adoptive_parents
            c.create_inheritance_new_cat()
            c.init_all_relationships()
        
    def handle_birth_event(birth_type, parent1, parent2, adoptive_parents, siblings):

        global b_txt

        birth_value = birth_type.value

        key_dict = {
            CatGroup.PLAYER_CLAN.value: "clan",
            CatGroup.ROGUE_GROUP.value: "rogue_group",
            CatGroup.LONER_GROUP.value: "loner_group",
            CatGroup.HOUSEHOLD.value: "kittypet",
            None: "none"
        }

        possible_birth_events = []

        possible_birth_events.extend(b_txt[birth_value]["gen"])
        possible_birth_events.extend(b_txt[birth_value][key_dict[game.clan.your_cat.status.group]])


        birth_txt = random.choice(possible_birth_events)

        parent_dict = {
            BirthType.NO_PARENTS: [None, None],
            BirthType.ONE_PARENT: [parent1, None],
            BirthType.TWO_PARENTS: [parent1, parent2],
            BirthType.ONE_ADOPTIVE_PARENT: [
                Cat.fetch_cat(adoptive_parents[0]), None
                ] if adoptive_parents else [None, None],
            BirthType.TWO_ADOPTIVE_PARENTS: [
                Cat.fetch_cat(adoptive_parents[0]), Cat.fetch_cat(adoptive_parents[1])
                ] if adoptive_parents and len(adoptive_parents) > 1 else [None, None],
            BirthType.ONE_OUTSIDER_PARENT: [parent1, None],
            BirthType.TWO_OUTSIDER_PARENTS: [parent1, parent2],
            BirthType.TWO_KITTYPET_PARENTS: [parent1, parent2],
            BirthType.TWO_LONER_PARENTS: [parent1, parent2],
            BirthType.TWO_ROGUE_PARENTS: [parent1, parent2],
            BirthType.MIXED_OUTSIDER_PARENTS: [parent1, parent2],
            BirthType.ALONE: [parent1, None]
        }
        # this sucks

        your_parent_1 = parent_dict[birth_type][0]
        your_parent_2 = parent_dict[birth_type][1]

        adjusted_birth_txt = event_text_adjust(
            Cat,
            text=birth_txt,
            main_cat=your_parent_1,
            random_cat=your_parent_2,
            clan=game.clan,
            other_clan=get_warring_clan() if game.clan.war else None
        )

        siblings_insert = adjust_list_text([str(i.name) for i in siblings])

        if siblings:
            if len(siblings) == 1:
                insert = "you and your {PRONOUN/m_c/sibling}, " + siblings_insert
                cap_insert = "You and your {PRONOUN/m_c/sibling}, " + siblings_insert
                insert = event_text_adjust(Cat, text=insert, main_cat=siblings[0])
                cap_insert = event_text_adjust(Cat, text=cap_insert, main_cat=siblings[0])
            else:
                insert = f"you, {game.clan.your_cat.name}, and your siblings, {siblings_insert}"
                cap_insert = f"You, {game.clan.your_cat.name}, and your siblings, {siblings_insert}"
        else:
            insert = f"you, {game.clan.your_cat.name}"
            cap_insert = f"You, {game.clan.your_cat.name}"

        # adjusted_birth_txt = adjusted_birth_txt.replace("insert_siblings", sibling_insert)
        adjusted_birth_txt = adjusted_birth_txt.replace("{insert}", insert)
        adjusted_birth_txt = adjusted_birth_txt.replace("{cap_insert}", cap_insert)

        adjusted_birth_txt = adjusted_birth_txt.replace("y_c", str(game.clan.your_cat.name))

        if (
            game.clan.your_cat.status.is_clancat and
            game.clan.your_cat.status.rank != CatRank.NEWBORN
            ):
            game.clan.your_cat.rank_change(CatRank.NEWBORN)
        if game.clan.your_cat.age != CatAge.NEWBORN:
            game.clan.your_cat.age = CatAge.NEWBORN
        
        game.cur_events_list.insert(0, Single_Event(adjusted_birth_txt, ["alert", "birth_death"], game.clan.your_cat.ID))

    birth_type, parent1, parent2, adoptive_parents = get_parents(birth_type)
    match_parents_to_kit(
        game.clan.your_cat, [p for p in (parent1, parent2) if p in made_up_parents]
    )
    siblings = create_siblings(parent1, parent2, adoptive_parents) if random.randint(1,4) != 1 else []
    handle_inheritance(parent1, parent2, adoptive_parents, siblings)
    handle_backstory(siblings)
    handle_birth_event(birth_type, parent1, parent2, adoptive_parents, siblings)

    if parent1 and not parent1.dead and parent1.gender in ("female", "molly"):
        parent1.get_injured("recovering from birth")
    elif parent2 and not parent2.dead and parent2.gender in ("female", "molly"):
        parent2.get_injured("recovering from birth")
    adoptive_parents_cats = []
    
    for c in adoptive_parents:
        adoptive_parents_cats.append(Cat.fetch_cat(c))

    for c in [parent1, parent2] + adoptive_parents_cats:
        for s in siblings + [game.clan.your_cat]:
            if s and c and c.status.alive_in_your_cat_group:
                y = random.randrange(0, 20)
                start_relation = Relationship(c, s, False, True)
                start_relation.like += 30 + y
                start_relation.comfort = 10 + y
                start_relation.trust = 10 + y
                c.relationships[s.ID] = start_relation
                y = random.randrange(0, 20)
                start_relation = Relationship(s, c, False, True)
                start_relation.like += 30 + y
                start_relation.comfort = 10 + y
                start_relation.trust = 10 + y
                s.relationships[c.ID] = start_relation

    game.clan.your_cat.w_done = False
    game.clan.your_cat.age = CatAge.NEWBORN
    switch_set_value(Switch.continue_after_death, False)
    
def get_living_cats():
    living_cats = []
    for the_cat in Cat.all_cats_list:
        if not the_cat.dead and not the_cat.status.is_outsider and not the_cat.moons == -1:
            living_cats.append(the_cat)
    return living_cats

def lifegen_process_text(text):
    cat_dict.clear()
    process_text_dict = cat_dict.copy()
    for abbrev in process_text_dict.keys():
        abbrev_cat = process_text_dict[abbrev]
        process_text_dict[abbrev] = (abbrev_cat, random.choice(abbrev_cat.pronouns))

    text = re.sub(r"\{(.*?)\}", lambda x: pronoun_repl(x, process_text_dict, False), text)

    text = text.replace("c_n", str(game.clan.displayname) + "Clan")
    if game.clan.leader:
        text = re.sub(r'(?<!\/)l_n(?!\/)', str(game.clan.leader.name), text)
    if "w_c" in text:
        enemy_clan = get_warring_clan()
        if enemy_clan:
            text = text.replace("w_c", str(enemy_clan.name))

    return text

def generate_lifegen_events():
    """
    LIFEGEN: Random flavour events on moonskip!
    """

    resource_dir = "events/lifegen_events/moon_events/living/"

    if game.clan.your_cat.dead:
        if game.clan.your_cat.status.group == CatGroup.STARCLAN:
            resource_dir = "events/lifegen_events/moon_events/starclan/"
        elif game.clan.your_cat.status.group == CatGroup.DARK_FOREST:
            resource_dir = "events/lifegen_events/moon_events/dark_forest/"
        elif game.clan.your_cat.status.group == CatGroup.UNKNOWN_RESIDENCE:
            resource_dir = "events/lifegen_events/moon_events/unknown_residence/"

    loaded_events = {}    
    loaded_events.update(load_lang_resource(resource_dir + "general.json"))

    if game.clan.your_cat.status.rank.is_any_clancat_rank():
        loaded_events.update(load_lang_resource(resource_dir + "general_no_kit.json"))
    
    if (
        game.clan.your_cat.status.rank.is_any_clancat_rank() or
        game.clan.your_cat.status.rank in (
            CatRank.ROGUE, CatRank.KITTYPET, CatRank.LONER
            )
        ):    
        try:
            loaded_events.update(load_lang_resource(resource_dir + game.clan.your_cat.status.rank.lifegen_name() + ".json"))
        except FileNotFoundError:
            # some ranks (newborn) have no file, can happen if the cat editor changed the rank
            pass

    if game.clan.your_cat.status.is_exiled():
        loaded_events.update(load_lang_resource(resource_dir + "exiled.json"))
    
    if game.clan.your_cat.status.rank == CatRank.ELDER and game.clan.your_cat.moons < 100:
        loaded_events.update(load_lang_resource(resource_dir + "young elder.json"))

    possible_events = []

    possible_types = ["general"]
    if game.clan.your_cat.joined_df:
        possible_types.append("df")
    if game.clan.your_cat.status.is_shunned():
        possible_types.append("shunned")
    if random.randint(1,20) == 1:
        possible_types.append("rare")
    if random.randint(1,20) == 1:
        possible_types.append("affair")

    # try:
    for key, event in loaded_events.items():
        if "season" in event and game.clan.current_season not in event["season"]:
            continue
        if "biome" in event and game.clan.biome not in event["biome"]:
            continue
        involved_cats = []
        lg_cat_dict = choose_random_cats(
            cats_block=event['cats'],
            rel_block=event['relationships'] if "relationships" in event else [],
            your_cat=game.clan.your_cat,
            the_cat=None
        )
        if not lg_cat_dict:
            continue

        process_text_dict = {}
        for abbrev in lg_cat_dict:
            abbrev_cat = lg_cat_dict[abbrev]
            if not abbrev_cat:
                continue
            involved_cats.append(abbrev_cat.ID)
            process_text_dict[abbrev] = (str(abbrev_cat.name), random.choice(abbrev_cat.pronouns))

        # process_text_dict["y_c"] = (str(game.clan.your_cat.name), random.choice(game.clan.your_cat.pronouns))

        processed_text = process_text(event["event"], process_text_dict)
        processed_text = event_text_adjust(
            Cat=Cat,
            text=processed_text,
            clan=game.clan,
            other_clan=random.choice(game.clan.all_other_clans)
            )

        possible_events.append(
            [
                processed_text,
                event["types"],
                involved_cats
            ]
        )
   
    # except Exception as e:
    #     print("ERROR Generating LifeGen Events:", e)

    if not possible_events:
        print("No possible events.")
        return

    for i in range(random.randint(0,5)):
        chosen_type = random.choice(possible_types)
        events_for_type = [
            event for event in possible_events if
            chosen_type in event[1]
        ]
        if not events_for_type:
            continue
        chosen_event = random.choice(events_for_type)

        if chosen_event[0] not in [event.text for event in game.cur_events_list]:
            game.cur_events_list.insert(0, Single_Event(chosen_event[0], "alert", chosen_event[2]))

        
def generate_kit_events():
    global kit_events

    # Parent events for moons 1-5
    if game.clan.your_cat.parent1:
        parents_txt = {1: "one_parent", 2: "two_parents"}

        alive_parents = 0
        if (
            game.clan.your_cat.parent1 and
            Cat.fetch_cat(game.clan.your_cat.parent1).status.alive_in_player_clan
            ):
            alive_parents += 1
        if (
            game.clan.your_cat.parent2 and
            Cat.fetch_cat(game.clan.your_cat.parent2).status.alive_in_player_clan
            ):
            alive_parents += 1


        if not alive_parents:
            return

        moons = str(game.clan.your_cat.moons)

        full_string = f"moon_{moons}_{parents_txt[alive_parents]}"
        if full_string not in kit_events:
            return

        kit_event1 = random.choice(kit_events["kit_events"][full_string])

        if game.clan.your_cat.parent1:
            kit_event1 = re.sub(r'(?<!\/)parent1(?!\/)', str(Cat.all_cats[game.clan.your_cat.parent1].name), kit_event1)
            cat_dict["parent1"] = Cat.all_cats[game.clan.your_cat.parent1]
        if game.clan.your_cat.parent2:
            kit_event1 = re.sub(r'(?<!\/)parent2(?!\/)', str(Cat.all_cats[game.clan.your_cat.parent2].name), kit_event1)
            cat_dict["parent2"] = Cat.all_cats[game.clan.your_cat.parent2]

        game.cur_events_list.insert(0, Single_Event(kit_event1, "alert", game.clan.your_cat.ID))

def generate_app_ceremony():
    global lifegen_ceremonies
    try:
        ceremony_txt = ""
        if game.clan.your_cat.status.is_shunned():
            ceremony_txt = ceremony_txt = random.choice(lifegen_ceremonies['apprentice ceremony shunned'])
        else:
            no_leader = False
            no_deputy = False
            no_medcat = False
            if (not game.clan.leader) or (not game.clan.leader.status.alive_in_player_clan):
                no_leader = True
            if (not game.clan.deputy) or (not game.clan.deputy.status.alive_in_player_clan):
                no_deputy = True
            if len(find_alive_cats_with_rank(Cat, [CatRank.MEDICINE_CAT, CatRank.MEDICINE_APPRENTICE])) == 0:
                no_medcat = True

            add_on_lead = ""
            if len(game.clan.clan_cats) == 1:
                add_on_lead = " no one"
            elif no_leader and no_deputy and no_medcat:
                add_on_lead = " no leader no deputy no med"
            elif no_leader and no_deputy:
                add_on_lead = " no leader no deputy"
            elif no_leader:
                add_on_lead = " no leader"

            add_on_mentor = " no mentor" if not game.clan.your_cat.mentor else ""
            ceremony_txt = random.choice(lifegen_ceremonies[f"{game.clan.your_cat.status.rank.lifegen_name()} ceremony{add_on_lead}{add_on_mentor}"])

        ceremony_txt = ceremony_txt.replace('c_n', str(game.clan.displayname) + "Clan")
        ceremony_txt = ceremony_txt.replace('y_c', str(game.clan.your_cat.name))
        if (game.clan.leader) and (game.clan.leader.status.alive_in_player_clan):
            ceremony_txt = re.sub(r'(?<!\/)l_n(?!\/)', str(game.clan.leader.name), ceremony_txt)
            cat_dict["l_n"] = game.clan.leader
        if (game.clan.deputy) and (game.clan.deputy.status.alive_in_player_clan):
            ceremony_txt = re.sub(r'(?<!\/)d_n(?!\/)', str(game.clan.deputy.name), ceremony_txt)
            cat_dict["d_n"] = game.clan.deputy
        if len(find_alive_cats_with_rank(Cat, CatRank.MEDICINE_APPRENTICE, CatRank.MEDICINE_CAT)) > 0:
            random_med = random.choice(find_alive_cats_with_rank(Cat, CatRank.MEDICINE_APPRENTICE, CatRank.MEDICINE_CAT))
            ceremony_txt = re.sub(r'(?<!\/)r_m(?!\/)', str(random_med.name), ceremony_txt)
            cat_dict["r_m"] = random_med
        if game.clan.your_cat.mentor:
            ceremony_txt = re.sub(r'(?<!\/)m_n(?!\/)', str(Cat.all_cats[game.clan.your_cat.mentor].name), ceremony_txt)
            cat_dict["m_n"] = Cat.all_cats[game.clan.your_cat.mentor]

        process_text_dict = cat_dict.copy()
        for abbrev in process_text_dict.keys():
            abbrev_cat = process_text_dict[abbrev]
            process_text_dict[abbrev] = (abbrev_cat, random.choice(abbrev_cat.pronouns))
        ceremony_txt = re.sub(r"\{(.*?)\}", lambda x: pronoun_repl(x, process_text_dict, False), ceremony_txt)
        
        game.cur_events_list.insert(0, Single_Event(ceremony_txt, ["alert", "ceremony"], game.clan.your_cat.ID))
    except Exception as e:
        print("ERROR with app ceremony" + str(e))
            
def generate_ceremony():
    if game.clan.your_cat.former_mentor:
        if Cat.all_cats[game.clan.your_cat.former_mentor[-1]].dead and game.clan.your_cat.status.rank == CatRank.MEDICINE_CAT:
            ceremony_txt = random.choice(lifegen_ceremonies[game.clan.your_cat.status.rank.lifegen_name() + '_ceremony_no_mentor'])

        if game.clan.your_cat.status.is_forgiven():
            try:
                ceremony_txt = random.choice(lifegen_ceremonies[game.clan.your_cat.status.rank.lifegen_name() + '_ceremony forgiven'])
            except:
                ceremony_txt = random.choice(lifegen_ceremonies[game.clan.your_cat.status.rank.lifegen_name() + '_ceremony'])
        else:
            ceremony_txt = random.choice(lifegen_ceremonies[game.clan.your_cat.status.rank.lifegen_name() + '_ceremony'])
        former_mentor = Cat.all_cats[game.clan.your_cat.former_mentor[-1]]
        ceremony_txt = re.sub(r'(?<!\/)m_n(?!\/)', str(former_mentor.name), ceremony_txt)
        cat_dict["m_n"] = former_mentor
    else:
        if game.clan.your_cat.status.is_forgiven():
            try:
                ceremony_txt = random.choice(lifegen_ceremonies[game.clan.your_cat.status.rank.lifegen_name() + '_ceremony_no_mentor forgiven'])
            except:
                ceremony_txt = random.choice(lifegen_ceremonies[game.clan.your_cat.status.rank.lifegen_name() + '_ceremony_no_mentor'])
        else:
            ceremony_txt = random.choice(lifegen_ceremonies[game.clan.your_cat.status.rank.lifegen_name() + '_ceremony_no_mentor'])
    
    ceremony_txt = ceremony_txt.replace('c_n', str(game.clan.displayname) + "Clan")
    ceremony_txt = ceremony_txt.replace('y_c', str(game.clan.your_cat.name))
    
    if game.clan.leader and game.clan.leader.status.alive_in_player_clan:
        ceremony_txt = re.sub(r'(?<!\/)l_n(?!\/)', str(game.clan.leader.name), ceremony_txt)
        cat_dict["l_n"] = game.clan.leader
    elif game.clan.deputy and game.clan.deputy.status.alive_in_player_clan:
        ceremony_txt = re.sub(r'(?<!\/)l_n(?!\/)', str(game.clan.deputy.name), ceremony_txt)
        cat_dict["d_n"] = game.clan.deputy


    random_honor = None

    TRAITS = load_lang_resource("events/ceremonies/ceremony_traits.json")
    try:
        random_honor = random.choice(TRAITS[game.clan.your_cat.personality.trait])
    except KeyError:
        random_honor = "hard work"
    ceremony_txt = ceremony_txt.replace('honor1', random_honor)
    process_text_dict = cat_dict.copy()
    for abbrev in process_text_dict.keys():
        abbrev_cat = process_text_dict[abbrev]
        process_text_dict[abbrev] = (abbrev_cat, random.choice(abbrev_cat.pronouns))
    ceremony_txt = re.sub(r"\{(.*?)\}", lambda x: pronoun_repl(x, process_text_dict, False), ceremony_txt)
    game.cur_events_list.insert(0, Single_Event(ceremony_txt, ["alert", "ceremony"], game.clan.your_cat.ID))
    game.clan.your_cat.w_done = True
    
def generate_elder_ceremony():
    ceremony_txt = random.choice(lifegen_ceremonies['elder_ceremony'])
    ceremony_txt = ceremony_txt.replace('c_n', str(game.clan.displayname) + "Clan")
    ceremony_txt = ceremony_txt.replace('y_c', str(game.clan.your_cat.name))
    if game.clan.leader and game.clan.leader.status.alive_in_player_clan:
        ceremony_txt = re.sub(r'(?<!\/)l_n(?!\/)', str(game.clan.leader.name), ceremony_txt)
        cat_dict["l_n"] = game.clan.leader
    elif game.clan.deputy and game.clan.deputy.status.alive_in_player_clan:
        ceremony_txt = re.sub(r'(?<!\/)l_n(?!\/)', str(game.clan.deputy.name), ceremony_txt)
        cat_dict["l_n"] = game.clan.deputy
    process_text_dict = cat_dict.copy()
    for abbrev in process_text_dict.keys():
        abbrev_cat = process_text_dict[abbrev]
        process_text_dict[abbrev] = (abbrev_cat, random.choice(abbrev_cat.pronouns))
    ceremony_txt = re.sub(r"\{(.*?)\}", lambda x: pronoun_repl(x, process_text_dict, False), ceremony_txt)
    game.cur_events_list.insert(0, Single_Event(ceremony_txt, ["alert", "ceremony"], game.clan.your_cat.ID))

def generate_outsider_age_ceremony():
    """lg: shows a short milestone message when the player cat reaches a new
    age while living as a kittypet, loner, or rogue, instead of a Clan ceremony."""
    your_cat = game.clan.your_cat

    stage_by_moons = {6: "adol", 12: "adult", 120: "senior"}
    stage = stage_by_moons.get(your_cat.moons)
    social = str(your_cat.status.social)
    if stage is None or social not in ("kittypet", "loner", "rogue"):
        return

    load_ceremonies()

    key = f"{social}_{stage}"
    if key not in CEREMONY_TXT:
        return

    ceremony_txt = event_text_adjust(Cat, CEREMONY_TXT[key][1], main_cat=your_cat)
    game.cur_events_list.insert(0, Single_Event(ceremony_txt, ["alert", "ceremony"], your_cat.ID))

def check_gain_app(checks):
    if game.clan.your_cat.dead or game.clan.your_cat.status.is_outsider:
        return
    if len(game.clan.your_cat.apprentice) == checks[0] + 1:
        switch_set_value(Switch.request_apprentice, False)
        d_txt = lifegen_ceremonies
        ceremony_txt = random.choice(d_txt['gain_app ' + game.clan.your_cat.status.rank.lifegen_name()])
        if game.clan.leader and game.clan.leader.status.alive_in_player_clan:
            ceremony_txt = re.sub(r'(?<!\/)l_n(?!\/)', str(game.clan.leader.name), ceremony_txt)
            cat_dict["l_n"] = game.clan.leader
        elif game.clan.deputy and game.clan.deputy.status.alive_in_player_clan:
            ceremony_txt = re.sub(r'(?<!\/)l_n(?!\/)', str(game.clan.deputy.name), ceremony_txt)
            cat_dict["l_n"] = game.clan.deputy
        app = Cat.all_cats[game.clan.your_cat.apprentice[-1]]
        cat_dict["app1"] = app
        ceremony_txt = re.sub(r'(?<!\/)app1(?!\/)', str(app.name), ceremony_txt)
        process_text_dict = cat_dict.copy()
        for abbrev in process_text_dict.keys():
            abbrev_cat = process_text_dict[abbrev]
            process_text_dict[abbrev] = (abbrev_cat, random.choice(abbrev_cat.pronouns))
        ceremony_txt = re.sub(r"\{(.*?)\}", lambda x: pronoun_repl(x, process_text_dict, False), ceremony_txt)
        game.cur_events_list.insert(0, Single_Event(ceremony_txt, ["alert", "ceremony"], game.clan.your_cat.ID))

def check_gain_mate(checks):
    
    if len(game.clan.your_cat.mate) == checks[1] + 1:
        try:
            d_txt = lifegen_ceremonies
            try:
                ceremony_txt = random.choice(d_txt["gain_mate " + game.clan.your_cat.status.rank.lifegen_name().replace(" ", "") + " " + Cat.all_cats[game.clan.your_cat.mate[-1]].status.rank.lifegen_name().replace(" ", "")])
            except:
                ceremony_txt = random.choice(d_txt["gain_mate general"])
            mate = Cat.all_cats[game.clan.your_cat.mate[-1]]
            cat_dict["mate1"] = mate
            ceremony_txt = re.sub(r'(?<!\/)mate1(?!\/)', str(mate.name), ceremony_txt)
            process_text_dict = cat_dict.copy()
            for abbrev in process_text_dict.keys():
                abbrev_cat = process_text_dict[abbrev]
                process_text_dict[abbrev] = (abbrev_cat, random.choice(abbrev_cat.pronouns))
            ceremony_txt = re.sub(r"\{(.*?)\}", lambda x: pronoun_repl(x, process_text_dict, False), ceremony_txt)
            game.cur_events_list.insert(0, Single_Event(ceremony_txt, "alert", game.clan.your_cat.ID))
        except:
            print("You gained a new mate but an event could not be shown1")
    elif switch_get_value(Switch.accept):
        try:
            d_txt = lifegen_ceremonies
            try:
                ceremony_txt = random.choice(d_txt["gain_mate " + game.clan.your_cat.status.rank.lifegen_name().replace(" ", "") + " " + Cat.all_cats[game.clan.your_cat.mate[-1]].status.rank.lifegen_name().replace(" ", "")])
            except:
                ceremony_txt = random.choice(d_txt["gain_mate general"])
            mate = Cat.all_cats[game.clan.your_cat.mate[-1]]
            cat_dict["mate1"] = mate
            ceremony_txt = re.sub(r'(?<!\/)mate1(?!\/)', str(mate.name), ceremony_txt)
            process_text_dict = cat_dict.copy()
            for abbrev in process_text_dict.keys():
                abbrev_cat = process_text_dict[abbrev]
                process_text_dict[abbrev] = (abbrev_cat, random.choice(abbrev_cat.pronouns))
            ceremony_txt = re.sub(r"\{(.*?)\}", lambda x: pronoun_repl(x, process_text_dict, False), ceremony_txt)
            game.cur_events_list.insert(0, Single_Event(ceremony_txt, "alert", game.clan.your_cat.ID))
            switch_set_value(Switch.accept, False)
            checks[1] = len(game.clan.your_cat.mate)
        except:
            print("You gained a new mate but an event could not be shown1")

    elif switch_get_value('reject'):
        try:
            new_mate = switch_get_value(Switch.new_mate)
            f_txt = load_lang_resource("events/lifegen_events/mate_lifegen.json")
            r = random.randint(1,3)
            if r == 1:
                new_mate.relationships[game.clan.your_cat.ID].romance -= 8
            elif r == 2:
                new_mate.relationships[game.clan.your_cat.ID].romance -= 8
                new_mate.relationships[game.clan.your_cat.ID].like -= 8
                game.clan.your_cat.relationships[new_mate.ID].comfort -= 5
            elif r == 3:
                new_mate.relationships[game.clan.your_cat.ID].romance -= 5
                new_mate.relationships[game.clan.your_cat.ID].like -= 10
                game.clan.your_cat.relationships[new_mate.ID].like -= 10

            ceremony_txt = random.choice(f_txt['reject' + str(r)])
            cat_dict["mate1"] = new_mate
            ceremony_txt = re.sub(r'(?<!\/)mate1(?!\/)', str(new_mate.name), ceremony_txt)
            process_text_dict = cat_dict.copy()
            for abbrev in process_text_dict.keys():
                abbrev_cat = process_text_dict[abbrev]
                process_text_dict[abbrev] = (abbrev_cat, random.choice(abbrev_cat.pronouns))
            ceremony_txt = re.sub(r"\{(.*?)\}", lambda x: pronoun_repl(x, process_text_dict, False), ceremony_txt)
            game.cur_events_list.insert(0, Single_Event(ceremony_txt, "alert", game.clan.your_cat.ID))
            switch_set_value(Switch.reject, False)
        except:
            print("You rejected a cat but an event could not be shown")

def check_gain_kits(checks):
    if not game.clan.your_cat.inheritance:
        from scripts.cat_relations.inheritance import Inheritance
        game.clan.your_cat.inheritance = Inheritance(game.clan.your_cat)
    if len(game.clan.your_cat.inheritance.get_blood_kits()) > checks[2]:
        if 'name kits' not in switch_get_value(Switch.windows_dict):
            switch_append_list_value(Switch.windows_dict, 'name kits')
            
def check_retire():
    if switch_get_value(Switch.retire):
        switch_set_value(Switch.retire, False)

def generate_death_event():
    global lifegen_ceremonies

    def death_pool(key):
        return lifegen_ceremonies.get(key, []) + lifegen_ceremonies['death']

    rank = game.clan.your_cat.status.rank
    if rank == CatRank.KITTEN:
        ceremony_txt = random.choice(lifegen_ceremonies.get('death_kit') or lifegen_ceremonies['death'])
        game.cur_events_list.insert(1, Single_Event(ceremony_txt, game.clan.your_cat.ID))
    elif rank == CatRank.MEDICINE_APPRENTICE:
        ceremony_txt = random.choice(death_pool('death_medapp'))
        game.cur_events_list.insert(1, Single_Event(ceremony_txt, game.clan.your_cat.ID))
    elif rank == CatRank.APPRENTICE:
        ceremony_txt = random.choice(death_pool('death_app'))
        game.cur_events_list.insert(1, Single_Event(ceremony_txt, game.clan.your_cat.ID))
    elif rank == CatRank.MEDIATOR_APPRENTICE:
        ceremony_txt = random.choice(death_pool('death_mediapp'))
        game.cur_events_list.insert(1, Single_Event(ceremony_txt, game.clan.your_cat.ID))
    elif rank == CatRank.QUEENS_APPRENTICE:
        ceremony_txt = random.choice(death_pool('death_queenapp'))
        game.cur_events_list.insert(1, Single_Event(ceremony_txt, game.clan.your_cat.ID))
    elif rank == CatRank.WARRIOR:
        ceremony_txt = random.choice(death_pool('death_warrior'))
        game.cur_events_list.insert(1, Single_Event(ceremony_txt, game.clan.your_cat.ID))
    elif rank == CatRank.MEDICINE_CAT:
        ceremony_txt = random.choice(death_pool('death_medcat'))
        game.cur_events_list.insert(1, Single_Event(ceremony_txt, game.clan.your_cat.ID))
    elif rank == CatRank.MEDIATOR:
        ceremony_txt = random.choice(death_pool('death_mediator'))
        game.cur_events_list.insert(1, Single_Event(ceremony_txt, game.clan.your_cat.ID))
    elif rank == CatRank.QUEEN:
        ceremony_txt = random.choice(death_pool('death_queen'))
        game.cur_events_list.insert(1, Single_Event(ceremony_txt, game.clan.your_cat.ID))
    elif rank == CatRank.ELDER:
        ceremony_txt = random.choice(death_pool('death_elder'))
        game.cur_events_list.insert(1, Single_Event(ceremony_txt, "alert", game.clan.your_cat.ID))
    elif rank == CatRank.LEADER:
        ceremony_txt = random.choice(death_pool('death_leader'))
        game.cur_events_list.insert(1, Single_Event(ceremony_txt, game.clan.your_cat.ID))
    elif rank == CatRank.DEPUTY:
        ceremony_txt = random.choice(death_pool('death_deputy'))
        game.cur_events_list.insert(1, Single_Event(ceremony_txt, game.clan.your_cat.ID))
    elif rank == CatRank.ROGUE:
        ceremony_txt = random.choice(death_pool('death_rogue'))
        game.cur_events_list.insert(1, Single_Event(ceremony_txt, game.clan.your_cat.ID))
    elif rank == CatRank.KITTYPET:
        ceremony_txt = random.choice(death_pool('death_kittypet'))
        game.cur_events_list.insert(1, Single_Event(ceremony_txt, game.clan.your_cat.ID))
    elif rank == CatRank.LONER:
        ceremony_txt = random.choice(death_pool('death_loner'))
        game.cur_events_list.insert(1, Single_Event(ceremony_txt, game.clan.your_cat.ID))
    else:
        ceremony_txt = random.choice(lifegen_ceremonies['death'])
        game.cur_events_list.insert(1, Single_Event(ceremony_txt, game.clan.your_cat.ID))

def mediator_events(cat, clan):
    """Check for mediator events"""
    if get_clan_setting("become_mediator"):
        # Note: These chances are large since it triggers every moon.
        # Checking every moon has the effect giving older cats more chances to become a mediator
        _ = constants.CONFIG["roles"]["become_mediator_chances"]
        if cat.status.rank in _ and not int(random.random() * _[cat.status.rank]):
            game.cur_events_list.append(
                Single_Event(
                    event_text_adjust(
                        Cat, i18n.t("hardcoded.event_mediator_app"), main_cat=cat
                    ),
                    "ceremony",
                    cat.ID,
                    clan=clan.group_ID
                )
            )
            cat.rank_change(CatRank.MEDIATOR)

def become_healer_events(cat, clan):
    """Check for queen events"""
    if get_clan_setting("become_healer"):
        # Note: These chances are large since it triggers every moon.
        # Checking every moon has the effect giving older cats more chances to become a mediator
        _ = constants.CONFIG["roles"]["become_healer_chances"]
        if cat.status.rank in _ and not int(random.random() * _[cat.status.rank]):
            game.cur_events_list.append(
                Single_Event(
                    event_text_adjust(
                        Cat, i18n.t("hardcoded.event_healer_app"), main_cat=cat
                    ),
                    "ceremony",
                    cat.ID,
                    clan=clan.group_ID
                )
            )
            cat.rank_change(CatRank.MEDICINE_APPRENTICE if cat.status.rank.is_any_apprentice_rank() else CatRank.MEDICINE_CAT)
            cat.experience = int(cat.experience * 0.75)

def become_queen_events(cat, clan):
    """Check for queen events"""
    if get_clan_setting("become_queen"):
        # Note: These chances are large since it triggers every moon.
        # Checking every moon has the effect giving older cats more chances to become a mediator
        _ = constants.CONFIG["roles"]["become_queen_chances"]
        if cat.status.rank in _ and not int(random.random() * _[cat.status.rank]):
            game.cur_events_list.append(
                Single_Event(
                    event_text_adjust(
                        Cat, i18n.t("hardcoded.event_queen_app"), main_cat=cat
                    ),
                    "ceremony",
                    cat.ID,
                    clan=clan.group_ID
                )
            )
            cat.rank_change(CatRank.QUEEN)
            cat.experience = int(cat.experience * 0.75)

def get_moon_freshkill():
    """Adding auto freshkill for the current moon."""
    healthy_hunter = list(
        filter(
            lambda c: c.status.rank
            in (CatRank.WARRIOR, CatRank.APPRENTICE, CatRank.LEADER, CatRank.DEPUTY)
            and c.status.alive_in_player_clan
            and not c.not_working(),
            Cat.all_cats.values(),
        )
    )

    prey_amount = 0
    for cat in healthy_hunter:
        lower_value = constants.PREY_CONFIG["auto_warrior_prey"][0]
        upper_value = constants.PREY_CONFIG["auto_warrior_prey"][1]
        if cat.status.rank == CatRank.APPRENTICE:
            lower_value = constants.PREY_CONFIG["auto_apprentice_prey"][0]
            upper_value = constants.PREY_CONFIG["auto_apprentice_prey"][1]

        prey_amount += random.randint(lower_value, upper_value)
    game.freshkill_event_list.append(
        i18n.t("hardcoded.prey_catch_count", count=prey_amount)
    )
    used_auto = False
    if get_clan_setting("freshkill"):
        if game.clan.your_cat.status.group != CatGroup.HOUSEHOLD:
            prey_amount = auto_freshkill()
            used_auto = True
    game.clan.freshkill_pile.add_freshkill(
        prey_amount, apply_outsider_yield=not used_auto
    )

def handle_focus():
    """
    This function should be called late in the 'one_moon' function and handles all focuses which are possible to handle here:
        - business as usual
        - hunting
        - herb gathering
        - threaten outsiders
        - seek outsiders
        - sabotage other clans
        - aid other clans
        - raid other clans
        - hoarding
    Focus which are not able to be handled here:
        rest_and_recover - handled in:
            - 'handle_outbreaks'
            - 'condition_events.handle_injuries'
            - 'condition_events.handle_illnesses'
            - 'cat.moon_skip_illness'
            - 'cat.moon_skip_injury'
    """
    # if no focus is selected, skip all other
    focus_text = i18n.t("defaults.focus_text")
    if get_clan_setting("business_as_usual") or get_clan_setting("rest_and_recover"):
        return
    elif get_clan_setting("hunting"):
        # handle warrior
        healthy_warriors = [
            cat
            for cat in Cat.all_cats.values()
            if cat.status.rank.is_any_adult_warrior_like_rank()
            and cat.status.alive_in_player_clan
            and cat.available_to_work()
        ]

        warrior_amount = (
            len(healthy_warriors)
            * constants.CONFIG["focus"]["hunting"][CatRank.WARRIOR]
        )

        # handle apprentices
        healthy_apprentices = [
            cat
            for cat in Cat.all_cats.values()
            if cat.status.rank == CatRank.APPRENTICE and cat.available_to_work()
            and cat.status.alive_in_player_clan
        ]

        app_amount = (
            len(healthy_apprentices)
            * constants.CONFIG["focus"]["hunting"][CatRank.APPRENTICE]
        )

        if warrior_amount + app_amount == 0:
            healthy_other = list(
                filter(
                    lambda c: c.moons > 3
                    and c.status.alive_in_player_clan
                    and not c.not_working(),
                    Cat.all_cats.values(),
                )
            )
            warrior_amount = (
                len(healthy_other) * constants.CONFIG["focus"]["hunting"]["emergency"]
            )

        # finish
        total_amount = warrior_amount + app_amount
        game.clan.freshkill_pile.add_freshkill(total_amount)
        focus_text = i18n.t("hardcoded.focus_prey", count=total_amount)
        game.freshkill_event_list.append(focus_text)

    elif get_clan_setting("herb_gathering"):
        # get medicine cats
        healthy_meds = find_alive_cats_with_rank(
            Cat,
            ranks=[CatRank.MEDICINE_CAT, CatRank.MEDICINE_APPRENTICE],
            working=True,
        )
        # get warriors to help
        healthy_warriors = find_alive_cats_with_rank(
            Cat,
            ranks=[CatRank.WARRIOR, CatRank.DEPUTY, CatRank.LEADER],
            working=True,
        )

        focus_text = game.clan.herb_supply.handle_focus(
            healthy_meds, healthy_warriors
        )

    elif get_clan_setting("threaten_outsiders"):
        amount = constants.CONFIG["focus"]["outsiders"]["reputation"]
        change_clan_reputation(-amount, game.clan)
        focus_text = None

    elif get_clan_setting("seek_outsiders"):
        amount = constants.CONFIG["focus"]["outsiders"]["reputation"]
        change_clan_reputation(amount, game.clan)
        focus_text = None

    elif get_clan_setting("sabotage_other_clans") or get_clan_setting(
        "aid_other_clans"
    ):
        amount = constants.CONFIG["focus"]["other_clans"]["relation"]
        if get_clan_setting("sabotage_other_clans"):
            amount = amount * -1
        for name in game.clan.clans_in_focus:
            clan = [clan for clan in game.clan.all_other_clans if clan.displayname == name][0]
            change_clan_relations(game.clan, clan, amount)
        focus_text = None

    elif get_clan_setting("hoarding") or get_clan_setting("raid_other_clans"):
        info_dict = constants.CONFIG["focus"]["hoarding"]
        if get_clan_setting("raid_other_clans"):
            info_dict = constants.CONFIG["focus"]["raid_other_clans"]

        involved_cats = {"injured": [], "sick": []}
        # handle prey
        healthy_warriors = list(
            filter(
                lambda c: c.status.rank.is_any_adult_warrior_like_rank()
                and c.status.alive_in_player_clan
                and not c.not_working(),
                Cat.all_cats.values(),
            )
        )
        warrior_amount = len(healthy_warriors) * info_dict["prey_warrior"]
        game.clan.freshkill_pile.add_freshkill(warrior_amount)
        game.freshkill_event_list.append(
            i18n.t("hardcoded.focus_raid_prey", count=warrior_amount)
        )

        # handle herbs
        healthy_meds = list(
            filter(
                lambda c: c.status.rank == CatRank.MEDICINE_CAT
                and c.status.alive_in_player_clan
                and not c.not_working(),
                Cat.all_cats.values(),
            )
        )

        herb_focus_text = game.clan.herb_supply.handle_focus(healthy_meds)

        # handle injuries / illness
        relevant_cats = healthy_warriors + healthy_meds
        if get_clan_setting("raid_other_clans"):
            chance = info_dict[f"injury_chance_warrior"]
            # increase the chance of injuries depending on how many clans are raided
            increase = info_dict["chance_increase_per_clan"]
            chance -= increase * len(game.clan.clans_in_focus)
        for cat in relevant_cats:
            # if the raid setting or 50/50 for hoarding to get to the injury part
            if get_clan_setting("raid_other_clans") or random.getrandbits(1):
                status_use = cat.status.rank
                if status_use in (CatRank.DEPUTY, CatRank.LEADER):
                    status_use = CatRank.WARRIOR
                chance = info_dict[f"injury_chance_{status_use}"]
                if get_clan_setting("raid_other_clans"):
                    # increase the chance of injuries depending on how many clans are raided
                    increase = info_dict["chance_increase_per_clan"]
                    chance -= increase * len(game.clan.clans_in_focus)

                if not int(random.random() * chance):  # 1/chance
                    possible_injuries = []
                    injury_dict = info_dict["injuries"]
                    for injury, amount in injury_dict.items():
                        possible_injuries.extend([injury] * amount)
                    chosen_injury = random.choice(possible_injuries)
                    cat.get_injured(chosen_injury)
                    involved_cats["injured"].append(cat.ID)
                else:
                    chance = constants.CONFIG["focus"]["hoarding"]["illness_chance"]
                    if not int(random.random() * chance):  # 1/chance
                        possible_illnesses = []
                        injury_dict = constants.CONFIG["focus"]["hoarding"][
                            "illnesses"
                        ]
                        for illness, amount in injury_dict.items():
                            possible_illnesses.extend([illness] * amount)
                        chosen_illness = random.choice(possible_illnesses)
                        cat.get_ill(chosen_illness)
                        involved_cats["sick"].append(cat.ID)

        # if it is raiding, lower the relation to other clans
        if get_clan_setting("raid_other_clans"):
            for name in game.clan.clans_in_focus:
                clan = [clan for clan in game.clan.all_other_clans if clan.displayname == name][0]
                amount = -constants.CONFIG["focus"]["raid_other_clans"]["relation"]
                change_clan_relations(game.clan, clan, amount)

        # finish
        text_snippet = "hardcoded.focus_injury_hoarding"
        if get_clan_setting("raid_other_clans"):
            text_snippet = "hardcoded.focus_injury_raiding"
        for condition_type, value in involved_cats.items():
            if len(value) > 0:
                game.cur_events_list.append(
                    Single_Event(
                        i18n.t(text_snippet, condition=condition_type, count=len(value)),
                        "health",
                        value,
                        clan=game.clan.group_ID
                    )
                )

        focus_text = i18n.t("hardcoded.focus_prey", count=warrior_amount)

        if herb_focus_text:
            focus_text += f" {herb_focus_text}"

    if focus_text:
        game.cur_events_list.insert(0, Single_Event(focus_text, "misc", clan=game.clan.group_ID))

def handle_tnr_return(clan=None):
    if clan is None:
        clan = game.clan
    eligible_cats = []
    cat_IDs = []
    for cat in Cat.all_cats.values():
        if not cat.status.is_lost(clan.group_ID) or not cat.status.is_outsider:
            continue
        TNRed = True if ('sterile' in cat.permanent_condition and 'TNR' in cat.pelt.scars and 
        game.clan.age - cat.permanent_condition['sterile']['moon_start'] == 1) else False
        if (cat.status.is_outsider
        and not cat.dead
        and TNRed):
            rejoin_upperbound = constants.CONFIG["lost_cat"]["rejoin_tnr_chance"]
            if random.randint(1, rejoin_upperbound) == 1 or "recovering from birth" in cat.injuries:
                Cat.outside_cats.update({cat.ID: cat})
                eligible_cats.append(cat)
                cat_IDs.append(cat.ID)
    
    if len(eligible_cats) == 0:
        return

    names = ', '.join([str(x.name) for x in eligible_cats[:-1]]) + ' and ' + str(eligible_cats[-1].name) if len(eligible_cats) > 1 else eligible_cats[0].name

    text = i18n.t('hardcoded.event_tnr_return', cats=names, count=len(eligible_cats))   
    for cat in eligible_cats:
        additional = cat.add_to_clan(clan.group_ID, False)
        for x in additional:
            if x in Cat.all_cats:
                Cat.all_cats[x].backstory = 'kittypet' + str(random.randint(1, 4))
                Cat.all_cats[x].name.suffix = ''
                Cat.all_cats[x].get_permanent_condition("sterile", False, custom_reveal=4)
    text = event_text_adjust(Cat, text, main_cat=eligible_cats[0], clan=clan)
    game.cur_events_list.append(Single_Event(text, "misc", cat_IDs, clan=clan.group_ID))
    
    handle_lost_cats_return(cat_IDs, clan)

def handle_lost_cats_return(predetermined_cat_IDs: list = None, clan=None):
    """
    TODO: DOCS
    """
    if clan is None:
        clan = game.clan
    cat_IDs = []
    if predetermined_cat_IDs:
        cat_IDs = predetermined_cat_IDs

    if not predetermined_cat_IDs:
        eligible_cats = []
        for cat in Cat.all_cats.values():
            if cat.dead or not cat.status.is_lost(clan.group_ID) or not cat.status.is_outsider:
                continue

            if "sterile" not in cat.permanent_condition or game.clan.age - cat.permanent_condition["sterile"]["moon_start"] > -1:
                eligible_cats.append(cat)

        if not eligible_cats:
            return

        lost_cat = random.choice(eligible_cats)
        if lost_cat.age in (CatAge.NEWBORN, CatAge.KITTEN):
            return

        cat_IDs.append(lost_cat.ID)

        if lost_cat.status.is_former_clancat or lost_cat.status.is_outsider:
            text = i18n.t(f"hardcoded.event_lost{random.choice(range(1,5))}")
        else:
            # this would be the child of a lost cat, who inherited the lost status from the parent and was never a clancat
            text = i18n.t(
                "hardcoded.event_returning_child_of_lost",
                parent_name=Cat.fetch_cat(lost_cat.parent1).name,
            )

        additional_cats = lost_cat.add_to_clan(clan.group_ID)
        cat_IDs.extend(additional_cats)

        if additional_cats:
            text += i18n.t("hardcoded.event_lost_kits", count=len(additional_cats))

        text = event_text_adjust(Cat, text, main_cat=lost_cat, clan=clan)

        game.cur_events_list.append(Single_Event(text, "misc", cat_IDs, clan=clan.group_ID))

    # Perform a ceremony if needed
    for cat_ID in cat_IDs:
        x = Cat.fetch_cat(cat_ID)
        if x.status.rank in [
            CatRank.APPRENTICE,
            CatRank.MEDICINE_APPRENTICE,
            CatRank.MEDIATOR_APPRENTICE,
            CatRank.KITTEN,
            CatRank.NEWBORN,
        ]:
            if x.moons >= 15:
                if x.status.rank == CatRank.MEDICINE_APPRENTICE:
                    ceremony(x, CatRank.MEDICINE_CAT)
                elif x.status.rank == CatRank.MEDIATOR_APPRENTICE:
                    ceremony(x, CatRank.MEDIATOR)
                else:
                    ceremony(x, CatRank.WARRIOR)
            elif not x.status.rank.is_any_apprentice_rank() and x.moons >= 6:
                ceremony(x, CatRank.APPRENTICE)

def handle_fading(cat, clan, forced=False):
    """
    TODO: DOCS
    """
    if (
        get_clan_setting("fading")
        and not cat.prevent_fading
        and cat.ID not in [clan.instructor.ID for clan in game.clan.all_other_clans if clan.instructor] + [game.clan.instructor.ID]
        and not cat.faded
    ) or forced:
        age_to_fade = constants.CONFIG["fading"]["age_to_fade"]
        kitten_fade = constants.CONFIG["fading"]["kit_fade"]
        opacity_at_fade = constants.CONFIG["fading"]["opacity_at_fade"]
        fading_speed = constants.CONFIG["fading"]["visual_fading_speed"]
        # Handle opacity
        cat.pelt.opacity = int(
            (100 - opacity_at_fade)
            * (1 - (cat.dead_for / age_to_fade) ** fading_speed)
            + opacity_at_fade
        )
        cat.pelt.rebuild_sprite = True

        # Deal with fading the cat if they are old enough.
        if forced or cat.dead_for > age_to_fade or (get_clan_setting('modded_kits') and cat.moons < 6 and cat.dead_for > kitten_fade):
            # If order not to add a cat to the faded list
            # twice, we can't remove them or add them to
            # faded cat list here. Rather, they are added to
            # a list of cats that will be "faded" at the next save.

            # Remove from med cat list, just in case.
            # This should never be triggered, but I've has an issue or
            # two with this, so here it is.
            if cat.ID in clan.med_cat_list:
                clan.med_cat_list.remove(cat.ID)

            # Unset their mate, if they have one
            if len(cat.mate) > 0:
                for mate_id in cat.mate:
                    if Cat.all_cats.get(mate_id):
                        cat.unset_mate(Cat.all_cats.get(mate_id))

            # If the cat is the current med, leader, or deputy, remove them
            if clan.leader:
                if clan.leader.ID == cat.ID:
                    clan.leader = None
            if clan.deputy:
                if clan.deputy.ID == cat.ID:
                    clan.deputy = None
            if clan.medicine_cat:
                if clan.medicine_cat.ID == cat.ID:
                    if clan.med_cat_list:  # If there are other med cats
                        clan.medicine_cat = Cat.fetch_cat(
                            clan.med_cat_list[0]
                        )
                    else:
                        clan.medicine_cat = None

            add_cat_to_fade_id(cat.ID)
            cat.set_faded()

def one_moon_outside_cat(cat, other_clan_cats: list = None):
    """
    exiled cat events
    """
    # aging the cat
    clan = next(filter(lambda c: cat.status.is_lost(c.group_ID) or cat.status.is_exiled(c.group_ID), game.clan.all_other_clans), game.clan)
    # this will also handle increasing dead_for!
    cat.status.increase_current_moons_as()

    cat.one_moon(other_clan_cats)
    if cat.dead:
        return

    cat.manage_outside_trait()

    handle_outside_EX(cat)

    # LG
    if (
        cat.status.is_exiled(CatGroup.PLAYER_CLAN_ID) and
        cat.ID != game.clan.your_cat.ID and
        not int(random.random() * 30)
        ):
        if cat.return_home():
            return
    # ---

    # handling the rank changes for Other Clan cats
    # this is SUPER rudimentary rn, really just a temp patch to handle our current little edge-cases
    if cat.status.is_other_clancat:
        # kitten to apprentice - for now it's going to be limited to warrior apprentices
        # use >= (with a kitten guard) so kittens past 6 moons still get promoted
        if cat.moons >= cat_class.age_moons[CatAge.ADOLESCENT][0] and cat.status.rank == CatRank.KITTEN:
            cat.status._change_rank(CatRank.APPRENTICE)
            # we aren't going to worry about sourcing a mentor, we're gonna pretend it's "hidden" from the player
        # apprentice to full
        if cat.moons >= cat_class.age_moons[CatAge.YOUNG_ADULT][0]:
            # warrior
            if cat.status.rank == CatRank.APPRENTICE:
                cat.status._change_rank(CatRank.WARRIOR)
            # med cat
            if cat.status.rank == CatRank.MEDICINE_APPRENTICE:
                cat.status._change_rank(CatRank.MEDICINE_CAT)
            # mediator (just in case)
            if cat.status.rank == CatRank.MEDIATOR_APPRENTICE:
                cat.status._change_rank(CatRank.MEDIATOR)
        # cat to elder
        if cat.moons >= cat_class.age_moons[CatAge.SENIOR][0]:
            # exclude the roles that don't really retire
            if cat.status.rank not in (CatRank.LEADER, CatRank.MEDICINE_CAT):
                cat.status._change_rank(CatRank.ELDER)

        if cat.mentor and not cat.status.rank.is_any_apprentice_rank():
            cat.update_mentor()

    # skill progression needs to be after rank progression
    cat.skills.progress_skill(cat)
    Pregnancy_Events.handle_having_kits(cat, clan=clan)

    if cat.is_ill() or cat.is_injured():
        if cat.is_ill() and cat.is_injured():
            if random.getrandbits(1):
                triggered_death = Condition_Events.handle_injuries(cat, clan=clan)
                if not triggered_death:
                    Condition_Events.handle_illnesses(cat, clan=clan)
            else:
                triggered_death = Condition_Events.handle_illnesses(cat, clan=clan)
                if not triggered_death:
                    Condition_Events.handle_injuries(cat, clan=clan)
        elif cat.is_ill():
            Condition_Events.handle_illnesses(cat, clan=clan)
        else:
            Condition_Events.handle_injuries(cat, clan=clan)
        switch_get_value(Switch.skip_conditions).clear()
        if cat.dead:
            return

    if not cat.dead:
        OutsiderEvents.killing_outsiders(cat, clan)
        OutsiderEvents.outsider_wander(cat, clan)
    
def kit_deaths(cats, clan=None):
    fading_kits = []
    fading_kit_names = []

    if len(find_alive_cats_with_rank(Cat, [CatRank.KITTEN], clan=clan.group_ID)):
        clan_queens = len(find_alive_cats_with_rank(Cat, [CatRank.QUEEN], working=True, clan=clan.group_ID))*3 + len(find_alive_cats_with_rank(Cat, [CatRank.QUEEN_APPRENTICE], working=True, clan=clan.group_ID))
        clan_queens = min(clan_queens/len(find_alive_cats_with_rank(Cat, [CatRank.KITTEN], clan=clan.group_ID)), 1)
        clan_queens *= constants.CONFIG['death_related']['max_queen_influence']

    death_chances = constants.CONFIG['death_related']['kit_death_chances']
    
    for kit in cats:
        # unborn cats (like your cat before it's born) sit at -1 moons
        if kit.dead or kit.moons < 0 or kit.status.social == CatSocial.KITTYPET:
            continue
        
        multiplier = 1-(clan_queens) if kit.status.group_ID == clan.group_ID and kit.status.rank == CatRank.KITTEN else 1
        multiplier *= 1.25 if kit.phenotype.growth_pattern == "runt" else 1
        if kit.moons < 2 and ((kit.status.is_outsider and clan.group_ID == game.clan.group_ID) or kit.status.group_ID == clan.group_ID):
            if random.random() < death_chances[str(kit.moons)] * multiplier:
                if not kit.status.is_outsider:
                    fading_kits.append(kit.ID)
                    fading_kit_names.append(str(kit.name))
                    kit.die(True)
                else:
                    kit.die(False)
                kit.history.add_death(str(kit.name) + " failed to thrive.")
                kit.moons -= 1
        elif kit.moons < 6 and kit.status.group_ID == clan.group_ID:
            if random.random() < death_chances[str(kit.moons)] * multiplier:
                create_short_event(
                            event_type="birth_death",
                            main_cat=kit,
                            clan=clan)
                if kit.dead:
                    kit.moons -= 1

    if len(fading_kits) > 0:
        event_text = ""
        event_text += ", ".join(fading_kit_names)
        if len(fading_kits) > 1:
            event_text += " were"
        else:
            event_text += " was"
        event_text += " lost this moon."
        game.cur_events_list.append(Single_Event(event_text, ['birth_death'], fading_kits, clan=clan.group_ID))
    
    return fading_kits



def queen_influence(cat):
    """Queens and queen apprentices can influence kits every moon"""

    personality = cat.personality.trait
    queens = find_alive_cats_with_rank(Cat, [CatRank.QUEEN, CatRank.QUEEN_APPRENTICE], clan=cat.status.group_ID)
    has_rel = []
    values = {}
    for c in queens:
        if c.ID in cat.relationships:
            has_rel.append(c)
            values[c.ID] = cat.relationships[c.ID].respect + cat.relationships[c.ID].trust + cat.relationships[c.ID].like + cat.relationships[c.ID].comfort
    if not has_rel:
        return

    negative_influence = False
    has_rel.sort(reverse=True,
        key=lambda c: abs(cat.relationships[c.ID].respect) + abs(cat.relationships[c.ID].trust) + abs(cat.relationships[c.ID].like) + abs(cat.relationships[c.ID].comfort))
    if values[has_rel[0].ID] < 0:
        negative_influence = True
    
    max_influence = random.randint(0, 1)
    i = 0
    while max_influence > i:
        i += 1
        affect_personality = cat.personality.mentor_influence(
            has_rel[0].personality, negative=negative_influence
        )
        affect_skills = None
        if not negative_influence:
            affect_skills = cat.skills.mentor_influence(has_rel[0])
        if affect_personality:
            cat.history.add_facet_queen_influence(
                has_rel[0].ID,
                affect_personality[0],
                affect_personality[1],
            )
            if cat.personality.trait != personality:
                cat.history.prev_pers.append(personality)
        if affect_skills:
            cat.history.add_skill_queen_influence(
                affect_skills[0], affect_skills[1], affect_skills[2]
            )

def one_moon_cat(cat, clan):
    """
    Triggers various moon events for a cat.
    -If dead, cat is given thought, dead_for count increased, and fading handled (then function is returned)
    -Outbreak chance is handled, death event is attempted, and conditions are handled (if death happens, return)
    -cat.one_moon() is triggered
    -mediator events are triggered (this includes the cat choosing to become a mediator)
    -freshkill pile events are triggered
    -if the cat is injured or ill, they're given their own set of possible events to avoid unrealistic behavior.
    They will handle disability events, coming out, pregnancy, apprentice EXP, ceremonies, relationship events, and
    will generate a new thought. Then the function is returned.
    -if the cat was not injured or ill, then they will do all of the above *and* trigger misc events, acc events,
    and new cat events
    """
    if cat.faded:
        return

    if cat.dead:
        if cat.ID in game.just_died:
            cat.moons += 1
        else:
            cat.status.increase_current_moons_as()
        if cat.moons > 0 and cat.status.rank == CatRank.NEWBORN:
            cat.status._change_rank(CatRank.KITTEN)
        cat.get_new_thought()
        handle_fading(cat, clan)  # Deal with fading.
        cat.talked_to = False
        return

    if cat.status.is_shunned() and cat.status.alive_in_player_clan:
        # Chance for a cat to be exiled, forgiven, or leave before the limit
        standing = cat.status.get_standing_with_group(CatGroup.PLAYER_CLAN_ID)
        shunned_moons = 0
        if standing and isinstance(standing[-1], list):
            if standing[-1][0] == CatStanding.SHUNNED:
                shunned_moons = game.clan.age - standing[-1][1]

        chance = constants.CONFIG["lifegen"]["shunned_cat"]["max_shunned_moons"] - shunned_moons
        # the chance scales as the cat gets closer to the limit
        # once theyre at the limit, itll be a 100% chance
        if chance < 1:
            chance = 1

        if not int(random.random() * chance):
            exile_or_forgive(cat)
    
    if cat.status.rank == CatRank.LEADER and cat.status.is_shunned() and cat.name.specsuffix_hidden is False:
        cat.name.specsuffix_hidden = True

    # corrects the name if the leader is shunned but their special suffix isnt hidden
    

    if cat.status.rank == CatRank.KITTEN:
        queen_influence(cat)

    cat.status.increase_current_moons_as()

    # all actions, which do not trigger an event display and
    # are connected to cats are located in there
    cat.one_moon()

    if constants.CONFIG["event_generation"]["debug_type_override"]:
        debug_type_override = constants.CONFIG["event_generation"][
            "debug_type_override"
        ]
        if debug_type_override in ["death", "injury"]:
            handle_injuries_or_general_death(cat, clan)
        elif debug_type_override == "misc":
            other_interactions(cat, clan)
        elif debug_type_override == "new_cat":
            invite_new_cats(cat, clan)

    # Handle Mediator Events
    mediator_events(cat, clan)
    become_healer_events(cat, clan)
    become_queen_events(cat, clan)

    
    # LIFEGEN: handle faith events
    # they only get a faith event if they hit the chance. that chance being 8 rn
    if not int(random.random() * 8):
        generate_faith_events(cat)
    # ---

    # handle nutrition amount
    # (CARE: the cats have to be fed before this happens - should be handled in "one_moon" function)
    if (
        game.clan.game_mode in ("expanded", "cruel season")
        and game.clan.freshkill_pile
        and (cat.status.alive_in_player_clan or cat.status.alive_in_your_cat_group)
    ):
        Condition_Events.handle_nutrient(
            cat, game.clan.freshkill_pile.nutrition_info
        )

        if cat.dead:
            return

    cat.talked_to = False
    cat.insulted = False
    cat.flirted = False
    cat.did_activity = False
    
    # prevent injured or sick cats from unrealistic Clan events
    if cat.is_ill() or cat.is_injured():
        if cat.is_ill() and cat.is_injured():
            if random.getrandbits(1):
                triggered_death = Condition_Events.handle_injuries(cat, clan=clan)
                if not triggered_death:
                    Condition_Events.handle_illnesses(cat, clan=clan)
            else:
                triggered_death = Condition_Events.handle_illnesses(cat, clan=clan)
                if not triggered_death:
                    Condition_Events.handle_injuries(cat, clan=clan)
        elif cat.is_ill():
            Condition_Events.handle_illnesses(cat, clan=clan)
        else:
            Condition_Events.handle_injuries(cat, clan=clan)
        switch_set_value(Switch.skip_conditions, [])
        if cat.dead:
            return
        handle_outbreaks(cat, clan)
    elif cat.ID != game.clan.your_cat.ID and cat.status.rank not in (CatRank.KITTEN, CatRank.ELDER, CatRank.NEWBORN) and not cat.status.is_outsider and not cat.dead:
        cat.experience += random.randint(0,5)

    # newborns don't do much
    if cat.status.rank == CatRank.NEWBORN:
        return
    
    if (
        cat.status.alive_in_your_cat_group
        or (not cat.dead and cat.status.group.is_any_clan_group())
    ) and not cat.status.is_outsider:
        if not cat.status.is_shunned():
            handle_apprentice_EX(cat)  # This must be before perform_ceremonies!
        handle_adult_EX(cat)
        # this HAS TO be before the cat.is_disabled() so that disabled kits can choose a med cat or mediator position
        perform_ceremonies(cat, clan)
    cat.skills.progress_skill(cat) # This must be done after ceremonies. 

    # check for death/reveal/risks/retire caused by permanent conditions
    if cat.is_disabled():
        Condition_Events.handle_already_disabled(cat, clan)
        if cat.dead:
            return

    coming_out(cat, clan)
    Pregnancy_Events.handle_having_kits(cat, clan=clan)
    # Stop the timeskip if the cat died in childbirth
    if cat.dead:
        return

    handle_colour_changes(cat, clan)

    # relationships have to be handled separately, because of the ceremony name change
    if cat.status.group.is_any_clan_group():
        cat.relationship_interaction()
        Relation_Events.handle_relationships(cat)

    # now we make sure ill and injured cats don't get interactions they shouldn't
    if cat.is_ill() or cat.is_injured():
        return

    invite_new_cats(cat, clan)
    other_interactions(cat, clan)
    gain_accessories(cat, clan)

    if random.getrandbits(1):
        triggered_death = handle_injuries_or_general_death(cat, clan)
        if not triggered_death:
            triggered_death = handle_illnesses_or_illness_deaths(cat, clan)
    else:
        triggered_death = handle_illnesses_or_illness_deaths(cat, clan)
        if not triggered_death:
            triggered_death = handle_injuries_or_general_death(cat, clan)

    if triggered_death:
        switch_set_value(Switch.skip_conditions, [])
        return

    handle_murder(cat, clan)
    cat.faith += round(random.uniform(-0.2, 0.2), 2)

    switch_set_value(Switch.skip_conditions, [])

def handle_colour_changes(cat, clan):
    involved_cats = [cat.ID]
    event_text = ""

    if cat.phenotype.white[0] == 'W' or (cat.phenotype.white[1] in ['ws', 'wt'] and cat.phenotype.whitegrade > 2) or cat.phenotype.pointgene[0] == 'c' or 'o' not in cat.phenotype.sexgene:
        return
    
    if cat.phenotype.brindledbi:
        red_colour = "white"
    elif cat.phenotype.dilute[0] == 'D' and cat.phenotype.pinkdilute[0] == 'Dp':
        red_colour = "orange"
    elif cat.phenotype.dilute[0] == 'd' and cat.phenotype.pinkdilute[0] == 'Dp':
        red_colour = "cream"
    elif cat.phenotype.dilute[0] == 'D' and cat.phenotype.pinkdilute[0] == 'dp':
        red_colour = "yellow"
    else:
        red_colour = 'creamy white'

    if cat.phenotype.ext[0] == 'ec' and cat.phenotype.agouti[0] == 'a' and cat.moons == 6:
        event_text = "Throughout kittenhood m_c has gotten many comments about their unique coat. Well, it looks by now to have turned completely " + red_colour + "."
    if cat.phenotype.ext[0] == 'ea' and ((cat.moons == 12 and cat.phenotype.agouti[0] != 'a') or (cat.moons == 36 and cat.phenotype.agouti[0] == 'a')):
        event_text = "m_c has gotten used to the odd comment of 'is your fur more "+ red_colour + " today?', having heard it practically since kithood. But by now, nobody can deny it, there's barely a trace of any other coat colour left."
    if cat.phenotype.ext[0] == 'er' and cat.moons == 24:
        event_text = "m_c has gotten used to the odd comment of 'is your fur more "+ red_colour + " today?', having heard it practically since kithood. But by now, nobody can deny it, there's barely a trace of any other coat colour left."

    if event_text:
        event_text = event_text_adjust(Cat, event_text, main_cat=cat)
        types = ["misc"]
        game.cur_events_list.append(Single_Event(event_text, types, involved_cats, clan=clan.group_ID))

def load_war_resources():
    global WAR_TXT, war_lang
    if war_lang == i18n.config.get("locale"):
        return
    WAR_TXT = load_lang_resource("events/war.json")
    war_lang = i18n.config.get("locale")

def check_war():
    """
    interactions with other clans
    """
    global WAR_TXT
    # if there are somehow no other clans, don't proceed
    if not game.clan.all_other_clans:
        return

    # Prevent wars from starting super early in the game.
    if game.clan.age <= 4:
        return
        
    switch_set_value(Switch.war_rel_change_type, {})
    
    for clan in game.clan.war:
        # check if war in progress
        started_war = False
        main_clan = game.clan if clan == game.clan.group_ID else [c for c in game.clan.all_other_clans if c.group_ID == clan][0]
        enemy_clan = None
        victor = None
        for enemy in game.clan.war[clan]:
            war_events: list = []
            enemy_clan = [c for c in game.clan.all_other_clans if c.group_ID == enemy][0]
            enemy_can_fight = game.clan.clancount == "singleclan" or event_for_other_clan(Cat, ["any_warrior_mult"], enemy)
            if game.clan.war[clan][enemy]["at_war"]:
                if not event_for_other_clan(Cat, ["any_warrior_mult"], clan) or not enemy_can_fight:
                    game.clan.war[clan][enemy]["at_war"] = False
                    game.clan.war[clan][enemy]["duration"] = 0
                    war_events = WAR_TXT["loss_events"]
                    victor = clan if not enemy_can_fight else enemy
                else:
                    threshold = 10
                    if enemy_clan.temperament[0] == "bloodthirsty":
                        threshold = 12
                    if enemy_clan.temperament[0] in ["mellow", "amiable", "gracious"]:
                        threshold = 7

                    threshold -= int(game.clan.war[clan][enemy]["duration"])
                    rel_value = game.clan.get_relations(main_clan, enemy_clan)
                    if rel_value < 0:
                        rel_value = 0

                    # check if war should conclude, if not, continue
                    if rel_value >= threshold and game.clan.war[clan][enemy]["duration"] > 1:
                        game.clan.war[clan][enemy]["at_war"] = False
                        game.clan.war[clan][enemy]["duration"] = 0
                        rel_value += 2
                        war_events = WAR_TXT["conclusion_events"]
                    else:  # try to influence the relation with warring clan
                        game.clan.war[clan][enemy]["duration"] += 1
                        choice = random.choice(
                            ["rel_up", "neutral", "rel_down", "rel_down", "rel_down"])
                        current_rels = switch_get_value(Switch.war_rel_change_type)
                        if not current_rels.get(clan):
                            current_rels[clan] = {}
                        current_rels[clan][enemy] = choice
                        switch_set_value(Switch.war_rel_change_type, current_rels)
                        war_events = WAR_TXT["progress_events"][choice]
                        if rel_value < 0:
                            rel_value = 0
                        if choice == "rel_up":
                            rel_value += 2
                        elif choice == "rel_down" and rel_value > 1:
                            rel_value -= 1

                    game.clan.set_relations(main_clan, enemy_clan, rel_value)

            else:  # try to start a war if no war in progress
                if started_war:
                    continue
                if not event_for_other_clan(Cat, ["any_warrior_mult"], clan) or not enemy_can_fight:
                    continue
                active_wars = max(len(game.clan.get_wars(clan)), len(game.clan.get_wars(enemy)))
                if active_wars and random.random() > 0.125:
                    continue
                threshold = 5
                if enemy_clan.temperament[0] == "bloodthirsty":
                    threshold = 10
                if enemy_clan.temperament[0] in ["mellow", "amiable", "gracious"]:
                    threshold = 3

                rel_value = game.clan.get_relations(main_clan, enemy_clan)

                if int(rel_value) <= threshold and not int(
                    random.random() * int(rel_value)
                ):
                    game.clan.war[clan][enemy]["at_war"] = True
                    war_events = WAR_TXT["trigger_events"]
                    current_rels = switch_get_value(Switch.war_rel_change_type)
                    if not current_rels.get(clan):
                        current_rels[clan] = {}
                    current_rels[clan][enemy] = "rel_down"
                    switch_set_value(Switch.war_rel_change_type, current_rels)
                    started_war = True

            # if nothing happened, return
            if not war_events or not enemy_clan or main_clan == enemy_clan:
                continue

            available_med = find_alive_cats_with_rank(Cat, [CatRank.MEDICINE_CAT], working=True, clan=main_clan.group_ID)

            war_events_copy = war_events.copy()
            if not main_clan.leader or not main_clan.deputy or not available_med:
                for event in war_events_copy:
                    if not main_clan.leader and "lead_name" in event:
                        war_events.remove(event)
                        continue
                    if not main_clan.deputy and "dep_name" in event:
                        war_events.remove(event)
                        continue
                    if not available_med and "med_name" in event:
                        war_events.remove(event)


            # grab our war "notice" for this moon
            event = random.choice(war_events)
            if not victor or victor == clan:
                event = ongoing_event_text_adjust(
                    Cat, event, other_clan_name=f"{enemy_clan.displayname}Clan", clan=main_clan
                )
            else:
                event = ongoing_event_text_adjust(
                    Cat, event, other_clan_name=f"{main_clan.displayname}Clan", clan=enemy_clan
                )
            game.cur_events_list.append(Single_Event(event, "other_clans", clan=clan))
            if game.clan.clancount == "multiclan":
                game.cur_events_list.append(Single_Event(event, "other_clans", clan=enemy))

def perform_ceremonies(cat, clan):
    """
    ceremonies
    """    
    global ceremony_accessory
    # TODO: hardcoded events, not good, consider how to convert to ShortEvent
    #  we *do* have a ceremony dict and format, not sure why it isn't being used here
    # PROMOTE DEPUTY TO LEADER, IF NEEDED -----------------------
    if clan.leader:
        leader_dead = clan.leader.dead
        leader_outside = clan.leader.status.group_ID != clan.group_ID
    else:
        leader_dead = True
        # If leader is None, treat them as dead (since they are dead - and faded away.)
        leader_outside = True

    # If a Clan deputy exists, and the leader is dead,
    #  outside, or doesn't exist, make the deputy leader.
    if clan.deputy:
        if (
            clan.deputy is not None
            and not clan.deputy.dead
            and not clan.deputy.status.group_ID != clan.group_ID
            and (leader_dead or leader_outside)
        ):
            old_name = clan.deputy.name
            clan.new_leader(clan.deputy)
            cat = clan.leader
            text = ""
            if cat.personality.trait == "bloodthirsty":
                text = i18n.t(
                    "hardcoded.ceremony_leader_bloodthirsty",
                    oldname=old_name,
                    newname=cat.name,
                )
            else:
                c = random.randint(1, 3)
                text = i18n.t(
                    f"hardcoded.ceremony_leader_{c}",
                    oldname=old_name,
                    newname=cat.name,
                )

            # LG
            moonplace_dict = {
                "Beach": "Mooncove",
                "Forest": "Moonhollow",
                "Plains": "Moongrove",
                "Mountainous": "Moonfalls"
            }

            text += " " +  i18n.t(
                "hardcoded.lifegen_ceremony_moonplace",
                oldname=old_name,
                newname=cat.name,
                moonplace=moonplace_dict.get(getattr(clan, "biome", None) or game.clan.biome, "Moonhollow")
            )
            # ---

            # game.ceremony_events_list.append(text)
            text += " " + i18n.t("hardcoded.ceremony_closer")

            text = event_text_adjust(Cat, text, main_cat=cat, clan=clan)

            game.cur_events_list.append(
                Single_Event(text, "ceremony", cat.ID, clan=clan.group_ID)
            )
            ceremony_accessory = True
            gain_accessories(cat, clan)
            clan.deputy = None

    # OTHER CEREMONIES ---------------------------------------
    # Protection check, to ensure "None" cats won't cause a crash.
    if cat:
        cat_dead = cat.dead
    else:
        cat_dead = True

    if not cat_dead:
        if cat.status.rank == CatRank.DEPUTY and clan.deputy is None:
            clan.deputy = cat
        if (
            cat.status.rank == CatRank.MEDICINE_CAT
            and clan.medicine_cat is None
        ):
            clan.medicine_cat = cat

        special_can_retire = False
        if cat.status.rank == CatRank.LEADER:
            special_can_retire = get_clan_setting("leader_retirement") and random.random() < (1/constants.CONFIG["roles"]["max_leader_retire_chance"])
        if cat.status.rank == CatRank.MEDICINE_CAT:
            special_can_retire = get_clan_setting("healer_retirement") and medicine_cats_can_cover_clan(
                Cat.all_cats.values(), get_amount_cat_for_one_medic(), clan=clan.group_ID, exclude=cat
            ) and random.random() < (1/constants.CONFIG["roles"]["max_healer_retire_chance"])
        if cat.status.rank == CatRank.MEDIATOR:
            special_can_retire = get_clan_setting("mediator_retirement") and random.random() < (1/constants.CONFIG["roles"]["max_mediator_retire_chance"])
        if cat.status.rank == CatRank.QUEEN:
            special_can_retire = random.random() < (1/constants.CONFIG["roles"]["max_queen_retire_chance"])
        
        # retiring to elder den
        if (
            not cat.no_retire
            and (cat.status.rank in (CatRank.WARRIOR, CatRank.DEPUTY) or cat.status.rank in (CatRank.MEDICINE_CAT, CatRank.MEDIATOR, CatRank.LEADER, CatRank.QUEEN) and special_can_retire)
            and len(cat.apprentice) < 1
            and cat.moons > 114
        ):
            # There is some variation in the age.
            if cat.moons > 140 or not int(
                random.random() * (-0.7 * cat.moons + 100)
            ):
                if cat.status.rank == CatRank.DEPUTY:
                    clan.deputy = None
                if cat.status.rank == CatRank.LEADER:
                    clan.leader = None
                if cat.status.rank == CatRank.MEDICINE_CAT:
                    clan.remove_med_cat(cat)
                ceremony(cat, CatRank.ELDER)

        # apprentice a kitten to either med or warrior
        if cat.moons >= cat_class.age_moons[CatAge.ADOLESCENT][0]:
            if cat.status.rank == CatRank.KITTEN:
                ceremony_accessory = True
                if clan is not game.clan:
                    becomes_med_app = _is_suitable_medcat_app(cat, clan)
                else:
                    med_cat_list = [
                        i
                        for i in Cat.all_cats_list
                        if i.status.rank.is_any_medicine_rank()
                        and i.status.alive_in_player_clan
                    ]

                    # check if the medicine cat is an elder
                    has_elder_med = [
                        c
                        for c in med_cat_list
                        if c.age == "senior" and c.status.rank == CatRank.MEDICINE_CAT
                    ]

                    very_old_med = [
                        c
                        for c in med_cat_list
                        if c.moons >= 150 and c.status.rank == CatRank.MEDICINE_CAT
                    ]

                    # check if the Clan has sufficient med cats
                    has_med = medicine_cats_can_cover_clan(
                        Cat.all_cats.values(),
                        amount_per_med=get_amount_cat_for_one_medic(),
                    )

                    # check if a med cat app already exists
                    has_med_app = any(
                        cat.status.rank == CatRank.MEDICINE_APPRENTICE
                        for cat in med_cat_list
                    )

                    # assign chance to become med app depending on current med cat and traits
                    chance = constants.CONFIG["roles"]["base_medicine_app_chance"]
                    if has_elder_med == med_cat_list:
                        # These chances apply if all the current medicine cats are elders.
                        if has_med:
                            chance = int(chance / 2.22)
                        else:
                            chance = int(chance / 13.67)
                    elif very_old_med == med_cat_list:
                        # These chances apply is all the current medicine cats are very old.
                        if has_med:
                            chance = int(chance / 3)
                        else:
                            chance = int(chance / 14)
                    # These chances will only be reached if the
                    # Clan has at least one non-elder medicine cat.
                    elif not has_med:
                        chance = int(chance / 7.125)
                    elif has_med:
                        chance = int(chance * 2.22)

                    if cat.personality.trait in [
                        "careful",
                        "compassionate",
                        "loving",
                        "wise",
                        "faithful",
                    ]:
                        chance = int(chance / 1.3)
                    if cat.is_disabled():
                        chance = int(chance / 2)

                    chance += (cat.intelligence * -1)

                    if chance <= 0:
                        chance = 1

                    if (
                        switch_get_value(Switch.request_apprentice) and
                        cat.status.group_ID == game.clan.your_cat.status.group_ID and
                        game.clan.your_cat.status.rank == CatRank.MEDICINE_CAT
                        ):
                        chance = 1

                    becomes_med_app = not has_med_app and not int(random.random() * chance)

                # edited below here for LG shunned ceremonies
                if becomes_med_app:
                    ceremony(cat, CatRank.MEDICINE_APPRENTICE)
                    ceremony_accessory = True
                    gain_accessories(cat, clan)
                    # CHECKMERGE
                    # queen chances were determined based on compassion here
                else:
                    # Chance for mediator apprentice
                    mediator_list = list(
                        filter(
                            lambda x: x.status.rank == CatRank.MEDIATOR
                            and x.status.group_ID == clan.group_ID,
                            Cat.all_cats_list,
                        )
                    )

                    # This checks if at least one mediator already has an apprentice.
                    has_mediator_apprentice = False
                    for c in mediator_list:
                        if c.apprentice:
                            has_mediator_apprentice = True
                            break

                    chance = constants.CONFIG["roles"]["mediator_app_chance"]
                    if cat.personality.trait in [
                        "charismatic",
                        "loving",
                        "responsible",
                        "wise",
                        "thoughtful",
                    ]:
                        chance = int(chance / 1.5)
                    if cat.skills.primary.path == SkillPath.MEDIATOR or cat.skills.secondary and cat.skills.secondary.path == SkillPath.MEDIATOR:
                        chance = int(chance / 2)
                    if cat.is_disabled():
                        chance = int(chance / 2)

                    chance += (cat.empathy * -1)
                    if chance <= 0:
                        chance = 1

                    if (
                        switch_get_value(Switch.request_apprentice) and
                        cat.status.group_ID == game.clan.your_cat.status.group_ID and
                        game.clan.your_cat.status.rank == CatRank.MEDIATOR
                    ):
                        chance = 1

                    # Chance for queen apprentice
                    queen_list = list(
                        filter(
                            lambda x: x.status.rank == CatRank.QUEEN
                            and x.status.group_ID == clan.group_ID,
                            Cat.all_cats_list,
                        )
                    )

                    # This checks if at least one mediator already has an apprentice.
                    has_queen_apprentice = False
                    for c in queen_list:
                        if c.apprentice:
                            has_queen_apprentice = True
                            break

                    q_chance = constants.CONFIG["roles"]["queen_app_chance"]
                    if cat.personality.trait in [
                        "childish",
                        "playful",
                        "compassionate",
                        "thoughtful",
                        "calm",
                        "responsible",
                    ]:
                        q_chance = int(chance / 1.5)
                    if cat.skills.primary.path == SkillPath.KIT or cat.skills.secondary and cat.skills.secondary.path == SkillPath.KIT:
                        q_chance = int(chance / 2)
                    if cat.is_disabled():
                        q_chance = int(chance / 2)

                    if q_chance == 0:
                        q_chance = 1

                    # Only become a mediator if there is already one in the clan.
                    if (
                        mediator_list
                        and not has_mediator_apprentice
                        and not int(random.random() * chance)
                    ):
                        ceremony(cat, CatRank.MEDIATOR_APPRENTICE)
                        ceremony_accessory = True
                        gain_accessories(cat, clan)
                    elif (
                        not mediator_list
                        and not int(random.random() * chance * 3)
                    ):
                        ceremony(cat, CatRank.MEDIATOR_APPRENTICE)
                        ceremony_accessory = True
                        gain_accessories(cat, clan)
                    elif (
                        queen_list
                        and not has_queen_apprentice
                        and not int(random.random() * q_chance)
                    ):
                        ceremony(cat, CatRank.QUEEN_APPRENTICE)
                        ceremony_accessory = True
                        gain_accessories(cat, clan)
                    elif (
                        not queen_list
                        and not int(random.random() * q_chance * 3)
                    ):
                        ceremony(cat, CatRank.QUEEN_APPRENTICE)
                        ceremony_accessory = True
                        gain_accessories(cat, clan)
                    else:
                        ceremony(cat, CatRank.APPRENTICE)
                        ceremony_accessory = True
                        gain_accessories(cat, clan)

        # graduate
        if cat.status.rank.is_any_apprentice_rank():
            if get_clan_setting("12_moon_graduation"):
                _ready = cat.moons >= 12
            else:
                _ready = (
                    cat.experience_level not in ["untrained", "trainee"]
                    and cat.moons
                    >= constants.CONFIG["graduation"]["min_graduating_age"]
                ) or cat.moons >= constants.CONFIG["graduation"][
                    "max_apprentice_age"
                ][
                    cat.status.rank
                ]

            if _ready:
                if get_clan_setting("12_moon_graduation"):
                    preparedness = "prepared"
                else:
                    if (
                        cat.moons
                        == constants.CONFIG["graduation"]["min_graduating_age"]
                    ):
                        preparedness = "early"
                    elif cat.experience_level in ["untrained", "trainee"]:
                        preparedness = "unprepared"
                    else:
                        preparedness = "prepared"

                if cat.status.rank == CatRank.APPRENTICE:
                    ceremony(cat, CatRank.WARRIOR, preparedness)
                    ceremony_accessory = True
                    gain_accessories(cat, clan)

                # promote to med cat
                elif cat.status.rank == CatRank.MEDICINE_APPRENTICE:
                    ceremony(cat, CatRank.MEDICINE_CAT, preparedness)
                    ceremony_accessory = True
                    gain_accessories(cat, clan)

                elif cat.status.rank == CatRank.MEDIATOR_APPRENTICE:
                    ceremony(cat, CatRank.MEDIATOR, preparedness)
                    ceremony_accessory = True
                    gain_accessories(cat, clan)

                elif cat.status.rank == CatRank.QUEEN_APPRENTICE:
                    ceremony(cat, CatRank.QUEEN, preparedness)
                    ceremony_accessory = True
                    gain_accessories(cat, clan)

def _is_suitable_medcat_app(cat, clan) -> bool:
    """
    Determines whether this cat will become a medicine cat
    :param cat: A kitten preparing for apprenticeship ceremony
    :return: True if the kitten should be a medcat, False otherwise
    """
    # assign chance to become med app depending on current med cat and traits
    chance = constants.CONFIG["roles"]["base_medicine_app_chance"]  # 41
    logger.info("Medcat app %s starting chance: %d", str(cat.name), chance)

    med_cat_list = [
        i
        for i in Cat.all_cats_list
        if i.status.rank.is_any_medicine_rank() and i.status.group_ID == clan.group_ID
    ]

    num_medcats = len(med_cat_list)

    # get number of medcat apps
    num_med_apps = len(
        [cat.status.rank == CatRank.MEDICINE_APPRENTICE for cat in med_cat_list]
    )
    logger.debug("Current number of medcats: %d", num_medcats - num_med_apps)
    logger.debug("Current number of medcat apps: %d", num_med_apps)

    # check if the Clan has sufficient med cats
    enough_working_meds = medicine_cats_can_cover_clan(
        Cat.all_cats.values(),
        amount_per_med=get_amount_cat_for_one_medic(), 
        clan=clan.group_ID
    )

    if (
        floor(num_med_apps / max(1, (len(med_cat_list) - num_med_apps)))
        > constants.CONFIG["roles"]["medicine cat apprentice"]["max_medcats_to_apps"]
    ):
        if enough_working_meds:
            # early return if the ratio of apps would be too high
            logger.info("Too many apprentices for medcat population. Aborting.")
            return False
        logger.debug(
            "Too many apprentices for medcat population, but not enough medicine cats for Clan! Continuing."
        )

    # check if the medicine cats are old
    senior_meds = [
        c
        for c in med_cat_list
        if c.age == "senior" and c.status.rank == CatRank.MEDICINE_CAT
    ]

    ancient_meds = [
        c
        for c in senior_meds
        if c.moons
        >= constants.CONFIG["roles"]["medicine cat apprentice"][
            "threshold_moons_ancient"
        ]
    ]

    senior_med_ratio = (len(senior_meds) / num_medcats) if num_medcats != 0 else 0

    ancient_med_ratio = (len(ancient_meds) / num_medcats) if num_medcats != 0 else 0

    if (
        ancient_med_ratio
        > constants.CONFIG["roles"]["medicine cat apprentice"][
            "threshold_percentage_ancient"
        ]
        / 100
    ):
        # These chances apply if enough medicine cats are very old.
        if enough_working_meds:
            chance = chance / 3
        else:
            logger.info("Not enough healthy medicine cats")
            chance = chance / 14

        logger.info("Ancient medicine cats, chance updated to %d", round(chance))
    elif (
        senior_med_ratio
        > constants.CONFIG["roles"]["medicine cat apprentice"][
            "threshold_percentage_seniors"
        ]
        / 100
    ):
        # These chances apply if enough medicine cats are elders.
        if enough_working_meds:
            chance = chance / 2.22
        else:
            logger.info("Not enough healthy medicine cats")
            chance = chance / 14

        logger.info("Senior medicine cats, chance updated to %d", round(chance))
    else:
        # These chances will only be reached if the
        # Clan has at least one non-elder medicine cat.
        if not enough_working_meds:
            chance = chance / 7.125
            logger.info(
                "Not enough healthy medicine cats, chance updated to %d", chance
            )
        else:
            chance = chance * 2.22
            logger.info(
                "Enough healthy young medicine cats, chance updated to %d", chance
            )

    if cat.personality.trait in [
        "careful",
        "compassionate",
        "loving",
        "wise",
        "faithful",
    ]:
        chance = chance / 1.3
        logger.info("Suitable trait, chance updated to %d", round(chance))

    elif cat.personality.trait in [
        "adventurous",
        "arrogant",
        "bold",
        "bloodthirsty",
        "cold",
        "fierce",
        "rebellious",
        "troublesome",
        "sneaky",
        "vengeful",
    ]:
        chance = chance * 2
        logger.info("Unsuitable trait, chance updated to %d", round(chance))

    beneficial_skills = [
        SkillPath.OMEN,
        SkillPath.PROPHET,
        SkillPath.HEALER,
        SkillPath.STAR,
        SkillPath.DREAM,
        SkillPath.CLAIRVOYANT,
        SkillPath.GHOST,
        SkillPath.CAMP,
    ]

    if cat.skills.primary.path in beneficial_skills:
        chance = chance / 2
        logger.info("beneficial primary skill, chance updated to %d", round(chance))

    if cat.skills.secondary and cat.skills.secondary.path in beneficial_skills:
        chance = chance / 4
        logger.info("beneficial secondary skill, chance updated to %d", round(chance))

    if cat.is_disabled():
        chance = chance / 2

    if num_med_apps == 0:
        # if there are no apprentices at all, make it slightly easier to get one
        logger.info("No apprentices at all")
        chance = chance / 1.8
        logger.info("No medcat apprentices at all, chance updated to %d", chance)
    if num_med_apps > 1:
        # if there's already at least one medcat app, make it harder to get another
        chance = chance * (1 + (0.2 * (num_med_apps - 1)))
        logger.info("%d medcat apps, chance updated to %d", num_med_apps, chance)

    chance = max(1, int(chance))

    success = not int(random.random() * chance)
    logger.info("%s final chance: %d | SUCCESS: %s", cat.name, chance, success)
    return success


def load_ceremonies():
    """
    TODO: DOCS
    """
    global CEREMONY_TXT, ceremony_id_by_tag, ceremony_lang
    if ceremony_lang == i18n.config.get("locale"):
        return

    CEREMONY_TXT = load_lang_resource("events/ceremonies/ceremony-master.json")

    ceremony_id_by_tag = {}
    # Sorting.
    # lifegen ceremonies are tagged with the old rank names, genemod renamed a few
    old_rank_tags = {
        "medicine cat": "healer",
        "medicine cat apprentice": "healer apprentice",
        "queen's apprentice": "queen apprentice",
    }
    for ID in CEREMONY_TXT:
        for tag in CEREMONY_TXT[ID][0]:
            tag = old_rank_tags.get(tag, tag)
            if tag in ceremony_id_by_tag:
                ceremony_id_by_tag[tag].add(ID)
            else:
                ceremony_id_by_tag[tag] = {ID}

    ceremony_lang = i18n.config.get("locale")

def ceremony(cat, promoted_to, preparedness="prepared"):
    """
    promote cats and add to events list
    """
    # ceremony = []
    clan = cat.status.fetch_clan_object(game.clan)
    was_leader = cat.status.rank == CatRank.LEADER

    _ment = (
        Cat.fetch_cat(cat.mentor) if cat.mentor else None
    )  # Grab current mentor, if they have one, before it's removed.
    old_name = str(cat.name)
    cat.rank_change(promoted_to)
    cat.rank_change_traits_skill(_ment)

    # LG Request Apprentice switch
    mentor_dict = {
        CatRank.MEDICINE_APPRENTICE: [CatRank.MEDICINE_CAT],
        CatRank.APPRENTICE: [
            CatRank.WARRIOR,
            CatRank.DEPUTY,
            CatRank.LEADER,
            CatRank.ELDER,
        ],
        CatRank.MEDIATOR_APPRENTICE: [CatRank.MEDIATOR],
        CatRank.QUEENS_APPRENTICE: [CatRank.QUEEN]
    }
    if switch_get_value(Switch.request_apprentice) and cat.status.group_ID == game.clan.your_cat.status.group_ID:
        if game.clan.your_cat.status.rank in mentor_dict.get(promoted_to, []):
            switch_set_value(Switch.request_apprentice, False)
    # ---

    involved_cats = [cat.ID]  # Clearly, the cat the ceremony is about is involved.

    # Changing prefix if needed
    if get_clan_setting('modded names') and get_clan_setting('dynamic prefixes'):
        cer_type = 'apprentice-warrior'
        if 'apprentice' in promoted_to:
            cer_type = 'kit-apprentice'
        elif promoted_to == 'elder':
            cer_type = 'warrior-elder'
        
        cat.name.change_prefix(cat.moons, clan.biome, cer_type)
        

    # Time to gather ceremonies. First, lets gather all the ceremony ID's.

    # ensure the right ceremonies are loaded for the given language
    load_ceremonies()

    possible_ceremonies = set()
    dead_mentor = None
    mentor = None
    previous_alive_mentor = None
    dead_parents = []
    living_parents = []
    mentor_type = {
        CatRank.MEDICINE_CAT: [CatRank.MEDICINE_CAT],
        CatRank.WARRIOR: [
            CatRank.WARRIOR,
            CatRank.DEPUTY,
            CatRank.LEADER,
            CatRank.ELDER,
        ],
        CatRank.MEDIATOR: [CatRank.MEDIATOR],
        CatRank.QUEEN: [CatRank.QUEEN]
    }

    try:
        # Get all the ceremonies for the role ----------------------------------------
        possible_ceremonies.update(ceremony_id_by_tag["leader_retire"] if was_leader else ceremony_id_by_tag[promoted_to])

        # Get ones for prepared status ----------------------------------------------
        if promoted_to in (CatRank.WARRIOR, CatRank.MEDICINE_CAT, CatRank.MEDIATOR, CatRank.QUEEN):
            possible_ceremonies = possible_ceremonies.intersection(
                ceremony_id_by_tag[preparedness]
            )

        # Gather ones for mentor. -----------------------------------------------------
        tags = []

        # CURRENT MENTOR TAG CHECK
        mentor = Cat.fetch_cat(cat.mentor) if cat.mentor else None
        if mentor:
            if mentor.status.is_leader:
                tags.append("yes_leader_mentor")
            else:
                tags.append("yes_mentor")
        else:
            tags.append("no_mentor")

        for c in reversed(cat.former_mentor):
            if Cat.fetch_cat(c) and Cat.fetch_cat(c).dead:
                tags.append("dead_mentor")
                dead_mentor = Cat.fetch_cat(c)
                break

        # Unlike dead mentors, living mentors must be VALID
        # they must have the correct status for the role the cat
        # is being promoted too.
        valid_living_former_mentors = []
        for c in cat.former_mentor:
            if Cat.fetch_cat(c).status.group_ID == clan.group_ID and Cat.fetch_cat(c) == 0:
                if promoted_to in mentor_type:
                    if Cat.fetch_cat(c).status.rank in mentor_type[promoted_to]:
                        valid_living_former_mentors.append(c)
                else:
                    valid_living_former_mentors.append(c)

        # ALL FORMER MENTOR TAG CHECKS
        if valid_living_former_mentors:
            #  Living Former mentors. Grab the latest living valid mentor.
            previous_alive_mentor = Cat.fetch_cat(valid_living_former_mentors[-1])
            if previous_alive_mentor.status.is_leader:
                tags.append("alive_leader_mentor")
            else:
                tags.append("alive_mentor")
        else:
            # This tag means the cat has no living, valid mentors.
            tags.append("no_valid_previous_mentor")

        # Now we add the mentor stuff:
        temp = possible_ceremonies.intersection(
            ceremony_id_by_tag["general_mentor"]
        )

        for t in tags:
            temp.update(
                possible_ceremonies.intersection(ceremony_id_by_tag[t])
            )

        possible_ceremonies = temp

        # Gather for parents ---------------------------------------------------------
        for p in [cat.parent1, cat.parent2, cat.parent3]:
            if Cat.fetch_cat(p):
                if Cat.fetch_cat(p).dead:
                    dead_parents.append(Cat.fetch_cat(p))
                # For the purposes of ceremonies, living parents
                # who are also the leader are not counted.
                elif (
                    Cat.fetch_cat(p).status.group_ID == clan.group_ID
                    and Cat.fetch_cat(p).status.rank != CatRank.LEADER
                ):
                    living_parents.append(Cat.fetch_cat(p))

        tags = []
        if len(dead_parents) >= 1 and "orphaned" not in cat.backstory:
            tags.append("dead1_parents")
        if len(dead_parents) >= 2 and "orphaned" not in cat.backstory:
            tags.append("dead1_parents")
            tags.append("dead2_parents")

        if len(living_parents) >= 1:
            tags.append("alive1_parents")
        if len(living_parents) >= 2:
            tags.append("alive2_parents")

        temp = possible_ceremonies.intersection(
            ceremony_id_by_tag["general_parents"]
        )

        for t in tags:
            temp.update(
                possible_ceremonies.intersection(ceremony_id_by_tag[t])
            )

        possible_ceremonies = temp

        # Gather for leader ---------------------------------------------------------

        tags = []
        if clan.leader and clan.leader.status.group_ID == clan.group_ID and not clan.leader.status.is_shunned():
            tags.append("yes_leader")
        else:
            tags.append("no_leader")

        temp = possible_ceremonies.intersection(
            ceremony_id_by_tag["general_leader"]
        )

        for t in tags:
            temp.update(
                possible_ceremonies.intersection(ceremony_id_by_tag[t])
            )

        possible_ceremonies = temp

        # Gather for backstories.json ----------------------------------------------------
        tags = []
        if (
            cat.backstory
            in BACKSTORIES["backstory_categories"]["abandoned_backstories"]
        ):
            tags.append("abandoned")
        elif cat.backstory == "clanborn":
            tags.append("clanborn")

        temp = possible_ceremonies.intersection(
            ceremony_id_by_tag["general_backstory"]
        )

        for t in tags:
            temp.update(
                possible_ceremonies.intersection(ceremony_id_by_tag[t])
            )

        possible_ceremonies = temp
        # Gather for traits --------------------------------------------------------------

        temp = possible_ceremonies.intersection(
            ceremony_id_by_tag["all_traits"]
        )

        if cat.personality.trait in ceremony_id_by_tag:
            temp.update(
                possible_ceremonies.intersection(
                    ceremony_id_by_tag[cat.personality.trait]
                )
            )

        possible_ceremonies = temp
    except Exception as ex:
        traceback.print_exception(type(ex), ex, ex.__traceback__)
        print("Issue gathering ceremony text.", str(cat.name), promoted_to)

    # getting the random honor if it's needed
    random_honor = None
    if promoted_to in (CatRank.WARRIOR, CatRank.MEDIATOR, CatRank.MEDICINE_CAT, CatRank.QUEEN):
        traits = load_lang_resource("events/ceremonies/ceremony_traits.json")

        try:
            random_honor = random.choice(traits[cat.personality.trait])
        except KeyError:
            random_honor = i18n.t("defaults.ceremony_honor")

        if get_clan_setting('modded names') and get_clan_setting('new suffixes') and not cat.name.specsuffix_hidden:
            cat.name.give_suffix(cat.skills, cat.personality, clan.biome, random_honor)

    if cat.status.rank in (CatRank.WARRIOR, CatRank.MEDICINE_CAT, CatRank.MEDIATOR, CatRank.QUEEN):
        cat.history.add_app_ceremony(random_honor)

    # lifegen filtering for shunned/forgiven
    # it's easier to do here lol
    new_ceremonies = []
    for ceremony in possible_ceremonies:
        
        new_ceremonies.append(ceremony)

    if promoted_to in [
        CatRank.APPRENTICE,
        CatRank.MEDICINE_APPRENTICE,
        CatRank.MEDIATOR_APPRENTICE,
        CatRank.QUEENS_APPRENTICE
    ]:
        try:
            ceremony_tags, ceremony_text = CEREMONY_TXT[
                random.choice(list(new_ceremonies))
            ]
        except IndexError:
            print("WARNING: A ceremony could not be chosen for", cat.name)
            return
    else:
    # -------------------
        ceremony_tags, ceremony_text = CEREMONY_TXT[
            random.choice(list(possible_ceremonies))
        ]

    # This is a bit strange, but it works. If there is
    # only one parent involved, but more than one living
    # or dead parent, the adjust text function will pick
    # a random parent. However, we need to know the
    # parent to include in the involved cats. Therefore,
    # text adjust also returns the random parents it picked,
    # which will be added to the involved cats if needed.
    (
        ceremony_text,
        involved_living_parent,
        involved_dead_parent,
    ) = ceremony_text_adjust(
        Cat,
        ceremony_text,
        cat,
        dead_mentor=dead_mentor,
        random_honor=random_honor,
        old_name=old_name,
        mentor=mentor,
        previous_alive_mentor=previous_alive_mentor,
        living_parents=living_parents,
        dead_parents=dead_parents,
        clan=clan
    )

    # Gather additional involved cats
    for tag in ceremony_tags:
        if tag == "yes_leader":
            involved_cats.append(clan.leader.ID)
        elif tag in ["yes_mentor", "yes_leader_mentor"]:
            involved_cats.append(cat.mentor)
        elif tag == "dead_mentor":
            involved_cats.append(dead_mentor.ID)
        elif tag in ["alive_mentor", "alive_leader_mentor"]:
            involved_cats.append(previous_alive_mentor.ID)
        elif tag == "alive2_parents" and len(living_parents) >= 2:
            for c in living_parents[:2]:
                involved_cats.append(c.ID)
        elif tag == "alive1_parents" and involved_living_parent:
            involved_cats.append(involved_living_parent.ID)
        elif tag == "dead2_parents" and len(dead_parents) >= 2:
            for c in dead_parents[:2]:
                involved_cats.append(c.ID)
        elif tag == "dead1_parent" and involved_dead_parent:
            involved_cats.append(involved_dead_parent.ID)

    # remove duplicates
    involved_cats = list(set(involved_cats))

    if str(cat.name) != old_name:
        cat.history.prev_names.append(old_name)

    if cat.ID != game.clan.your_cat.ID and game.clan.your_cat.ID != cat.mentor:
        game.cur_events_list.append(
            Single_Event(ceremony_text, "ceremony", involved_cats, clan=clan.group_ID)
        )
        # game.ceremony_events_list.append(f'{cat.name}{ceremony_text}')

def gain_accessories(cat, clan):
    """
    accessories
    """    
    global ceremony_accessory

    if not cat:
        return

    if cat.status.group_ID != clan.group_ID:
        return
    
    if get_clan_setting('all accessories'):
        return

    # check if cat already has acc
    # if cat.pelt.accessory:
    #     ceremony_accessory = False
    #     return
    # old ^^
    # check if cat already has max acc
    if cat.pelt.accessory and len(cat.pelt.accessory) == 3:
        ceremony_accessory = False
        return

    # chance to gain acc
    acc_chances = constants.CONFIG["accessory_generation"]
    chance = acc_chances["base_acc_chance"]
    if cat.status.rank.is_any_medicine_rank():
        chance += acc_chances["med_modifier"]
    if cat.age in [CatAge.KITTEN, CatAge.ADOLESCENT]:
        chance += acc_chances["baby_modifier"]
    elif cat.age in [CatAge.SENIOR_ADULT, CatAge.SENIOR]:
        chance += acc_chances["elder_modifier"]
    if cat.personality.trait in [
        "adventurous",
        "childish",
        "confident",
        "daring",
        "playful",
        "attention-seeker",
        "sweet",
        "troublesome",
        "impulsive",
        "inquisitive",
        "strange",
        "shameless",
    ]:
        chance += acc_chances["happy_trait_modifier"]
    elif cat.personality.trait in [
        "cold",
        "strict",
        "bossy",
        "bullying",
        "insecure",
        "nervous",
    ]:
        chance += acc_chances["grumpy_trait_modifier"]
    if cat.pelt.accessory and len(cat.pelt.accessory) >= 1:
        chance += acc_chances["multiple_acc_modifier"]
    if ceremony_accessory:
        chance += acc_chances["ceremony_modifier"]

    # increase chance of acc if the cat had a ceremony
    if chance <= 0:
        chance = 1
    if not int(random.random() * chance):
        sub_type = ["accessory"]
        if ceremony_accessory:
            sub_type.append("ceremony")

        create_short_event(
            event_type="misc",
            main_cat=cat,
            sub_type=sub_type,
            clan=clan
        )

    ceremony_accessory = False

    return

# This gives outsiders exp. There may be a better spot for it to go,
# but I put it here to keep the exp functions together
def handle_outside_EX(cat):
    if cat.status.is_outsider or cat.status.is_other_clancat:
        if cat.not_working() and int(random.random() * 3):
            return

        if cat.age == CatAge.KITTEN:
            return

        if cat.age == CatAge.ADOLESCENT:
            ran = constants.CONFIG["outside_ex"]["base_adolescent_timeskip_ex"]
        elif cat.age == CatAge.SENIOR:
            ran = constants.CONFIG["outside_ex"]["base_senior_timeskip_ex"]
        else:
            ran = constants.CONFIG["outside_ex"]["base_adult_timeskip_ex"]

        role_modifier = 1
        if cat.status.social == CatSocial.KITTYPET:
            # Kittypets will gain exp at 2/3 the rate of loners or exiled cats, as this assumes they are
            # kept indoors at least part of the time and can't hunt/fight as much
            role_modifier = 0.6

        exp = random.choice(
            list(range(ran[0][0], ran[0][1] + 1))
            + list(range(ran[1][0], ran[1][1] + 1))
        )

        cat.experience += max(exp * role_modifier, 1)

def handle_adult_EX(cat):
    if cat.not_working() and int(random.random() * 3):
        return

    if cat.ID in game.patrolled:
        return

    if cat.age in [CatAge.NEWBORN, CatAge.KITTEN] or cat.status.rank.is_any_apprentice_rank():
        return

    if cat.age == CatAge.SENIOR:
        ran = constants.CONFIG["outside_ex"]["base_senior_timeskip_ex"]
    else:
        ran = constants.CONFIG["outside_ex"]["base_adult_timeskip_ex"]

    role_modifier = 1
    if cat.status.rank.is_any_medicine_rank():
        # Healers just gain exp slower because reasons idk
        role_modifier = 0.6

    exp = random.choice(
        list(range(ran[0][0], ran[0][1] + 1))
        + list(range(ran[1][0], ran[1][1] + 1))
    )

    cat.experience += max(exp * role_modifier, 1)

def handle_apprentice_EX(cat):
    """
    TODO: DOCS
    """
    if cat.status.rank.is_any_apprentice_rank() and not cat.status.is_shunned():
        if cat.not_working() and int(random.random() * 3):
            return

        if cat.experience > cat.experience_levels_range["trainee"][1]:
            return

        if cat.status.rank == CatRank.MEDICINE_APPRENTICE:
            ran = constants.CONFIG["clancat_ex"]["base_med_app_timeskip_ex"]
        else:
            ran = constants.CONFIG["clancat_ex"]["base_app_timeskip_ex"]

        mentor_modifier = 1
        mentor = Cat.fetch_cat(cat.mentor) if cat.mentor else None
        if not mentor or mentor.not_working():
            # Sick mentor debuff
            mentor_modifier = 0.7

        exp = random.choice(
            list(range(ran[0][0], ran[0][1] + 1))
            + list(range(ran[1][0], ran[1][1] + 1))
        )

        if cat.status.group_ID != CatGroup.PLAYER_CLAN_ID:
            exp += random.randint(0, 3)

        cat.experience += max(exp * mentor_modifier, 1)

def invite_new_cats(cat, clan=None):
    """
    new cats
    """
    if clan is None:
        clan = game.clan
    global new_cat_invited

    if game.clan is None:
        return

    if constants.CONFIG["event_generation"]["debug_type_override"] == "new_cat":
        create_short_event(
            event_type="new_cat",
            main_cat=cat,
            clan=clan
        )
        return

    chance = 200

    clan_size = get_living_clan_cat_count(Cat, clan.group_ID)

    base_chance = 700
    if clan_size < 10:
        base_chance = 200
    elif clan_size < 30:
        base_chance = 300


    if clan != game.clan:
        # Increase chance if secondary Clan is smaller than main clan

        main_clan_alive_cats = get_living_clan_cat_count(Cat)
        ratio = clan_size / (main_clan_alive_cats or 1)

        if ratio < 0.33:
            base_chance = int(base_chance * ratio / 2)

        if ratio < 0.5:
            base_chance = int(base_chance * ratio)

        if ratio < 0.75:
            base_chance = int(base_chance * ratio * 1.25)

    reputation = 50
    reputation = clan.reputation

    # hostile
    if 1 <= reputation <= 30:
        if clan_size < 10:
            chance = base_chance
        else:
            rep_adjust = int(reputation / 2)
            if rep_adjust == 0:
                rep_adjust = 1
            chance = base_chance + int(300 / rep_adjust)
    # neutral
    elif 31 <= reputation <= 70:
        if clan_size < 10:
            chance = base_chance - reputation
        else:
            chance = base_chance
    # welcoming
    elif 71 <= reputation <= 100:
        chance = base_chance - reputation

    chance = max(chance, 1)

    if (
        not int(random.random() * chance)
        and not cat.age.is_baby()
        and not new_cat_invited
    ):
        new_cat_invited = True

        create_short_event(
            event_type="new_cat",
            main_cat=cat,
            clan=clan
        )

def other_interactions(cat, clan):
    """
    TODO: DOCS
    """
    if constants.CONFIG["event_generation"]["debug_type_override"] == "misc":
        create_short_event(
            event_type="misc",
            main_cat=cat,
            clan=clan
        )
        return

    hit = int(random.random() * 30)
    if hit:
        return

    create_short_event(
        event_type="misc",
        main_cat=cat,
        clan=clan
    )

def handle_injuries_or_general_death(cat, clan):
    """
    decide if cat dies
    """

    if constants.CONFIG["event_generation"]["debug_type_override"] == "death":
        create_short_event(
            event_type="birth_death",
            main_cat=cat,
            clan=clan
        )
        return
    elif constants.CONFIG["event_generation"]["debug_type_override"] == "injury":
        Condition_Events.handle_injuries(cat, clan)
        return

    # chance to kill leader: 1/50 by default
    if (
        not int(
            random.random()
            * game.get_config_value(clan.group_ID, "death_related", "leader_death_chance")
        )
        and cat.status.is_leader
        and not cat.not_working()
    ):
        create_short_event(
            event_type="birth_death",
            main_cat=cat,
            clan=clan
        )

        return True

    # chance to die of old age
    age_start = constants.CONFIG["death_related"]["old_age_death_start"]
    death_curve_setting = constants.CONFIG["death_related"]["old_age_death_curve"]
    death_curve_value = 0.001 * death_curve_setting
    # made old_age_death_chance into a separate value to make testing with print statements easier
    old_age_death_chance = ((1 + death_curve_value) ** (cat.moons - age_start)) - 1
    if random.random() <= old_age_death_chance:
        create_short_event(
            event_type="birth_death",
            main_cat=cat,
            sub_type=["old_age"],
            clan=clan
        )
        return True
    # max age has been indicated to be 300, so if a cat reaches that age, they die of old age
    elif cat.moons >= 300:
        create_short_event(
            event_type="birth_death",
            main_cat=cat,
            sub_type=["old_age"],
            clan=clan
        )
        return True
    
    # disaster death chance
    if get_clan_setting("disasters"):
        if not random.getrandbits(constants.CONFIG["death_related"]["mass_death_chance"]):  # 1/512
            create_short_event(
                event_type="birth_death",
                main_cat=cat,
                sub_type=["mass_death"],
                clan=clan,
            )
            return True
    chance_death = game.get_config_value(clan.group_ID, "death_related", f"{game.clan.game_mode}_death_chance")
    if cat.status.rank.is_baby():
        num_queens = 0
        for c_ob in Cat.all_cats_list:
            if not c_ob.dead and c_ob.status.group_ID == clan.group_ID:
                if c_ob.status.rank.is_any_queen_rank():
                    num_queens += 1
        chance_death += (num_queens * 5)

    # final death chance and then, if not triggered, head to injuries
    if (
        not int(
            random.random()
            * chance_death
        )
        and not cat.not_working()
    ):  # 1/400
        create_short_event(
            event_type="birth_death",
            main_cat=cat,
            clan=clan
        )
        return True
    else:
        triggered_death = Condition_Events.handle_injuries(cat, clan)

        return triggered_death

def handle_murder(cat, clan):
    """Handles murder"""

    if cat.age.is_baby():
        return
    if cat.ID == game.clan.your_cat.ID:
        return
        
    relationships = cat.relationships.values()
    targets = []

    # if this cat is unstable and aggressive, we lower the random murder chance
    random_murder_chance = int(constants.CONFIG["death_related"]["base_random_murder_chance"])
    # random_murder_chance -= 0.5 * (
    #     (cat.personality.aggression) + (16 - cat.personality.stability)
    # )

    # Check to see if random murder is triggered.
    # If so, we allow targets to be anyone they have even the smallest amount of negativity for
    if random.getrandbits(max(1, random_murder_chance)) == 1:
        targets = [
            Cat.fetch_cat(i)
            for i in Cat.all_cats
            if Cat.fetch_cat(i).status.group.is_any_clan_group()
            and i != cat.ID
        ]
        if not targets:
            return

        chosen_cat = random.choice(targets)

        create_short_event(
            event_type="birth_death",
            main_cat=chosen_cat,
            random_cat=cat,
            sub_type=["murder"],
            clan=clan,
            second_clan=chosen_cat.status.fetch_clan_object(game.clan) if chosen_cat.status.group_ID != cat.status.group_ID else None
        )

        return

    # will this cat actually murder? this takes into account stability and lawfulness
    murder_capable = 8
    if cat.personality.stability < 6:
        murder_capable -= 3
    if cat.personality.lawfulness < 6:
        murder_capable -= 2
    if cat.personality.aggression > 12:
        murder_capable -= 3
    elif cat.personality.aggression > 10:
        murder_capable -= 1

    murder_capable = max(1, murder_capable)

    if random.getrandbits(murder_capable) != 1:
        return

    # If random murder is not triggered, targets can only be those they have some mid/extreme neg for
    targets = [
        i
        for i in relationships
        if (i.has_mid_negative or i.has_extreme_negative)
        and Cat.fetch_cat(i.cat_to).status.group.is_any_clan_group()
    ]
    # sort by total relationship, this way we know who has the worst relationship
    targets.sort(key=lambda x: x.total_relationship_value)
    if len(targets) > 5:
        targets = targets[:5]

    # if we have some, then we need to decide if this cat will kill
    if targets:
        chosen_target = random.choice(targets)
        chosen_cat = Cat.fetch_cat(chosen_target.cat_to)

        kill_chance = constants.CONFIG["death_related"]["base_murder_kill_chance"]

        if chosen_cat.status.group_ID != cat.status.group_ID:
            kill_chance = constants.CONFIG["death_related"]["base_crossclan_murder_kill_chance"]

        extreme_neg = len(
            [l for l in chosen_target.get_reltype_tiers() if l.is_extreme_neg]
        )
        mid_neg = len([t for t in chosen_target.get_reltype_tiers() if t.is_mid_neg])

        relation_modifier = (extreme_neg * 8) + (mid_neg * 6)

        kill_chance -= relation_modifier

        if (
            len(chosen_target.log) > 0
            and "(high negative effect)" in chosen_target.log[-1]
        ):
            kill_chance -= 10

        if (
            len(chosen_target.log) > 0
            and "(medium negative effect)" in chosen_target.log[-1]
        ):
            kill_chance -= 5

        # little easter egg just for fun
        if cat.personality.trait in ("ambitious", "arrogant", "rebellious") and (
            Cat.fetch_cat(chosen_target.cat_to).status.is_leader
            or Cat.fetch_cat(chosen_target.cat_to).status.rank == CatRank.DEPUTY
        ):
            kill_chance -= 10
            if cat.status.rank == CatRank.DEPUTY:
                kill_chance -= 15

        kill_chance -= cat.personality.aggression
        kill_chance -= 16 - cat.personality.stability
        kill_chance -= 16 - cat.personality.lawfulness
        kill_chance = max(1, int(kill_chance))

        if not int(random.random() * kill_chance):
            # print(
            #     cat.name, "TARGET CHOSEN", Cat.fetch_cat(chosen_target.cat_to).name
            # )
            # print("KILL KILL KILL")

            create_short_event(
                event_type="birth_death",
                main_cat=chosen_cat,
                random_cat=cat,
                sub_type=["murder"],
                clan=clan,
                second_clan=chosen_cat.status.fetch_clan_object(game.clan) if chosen_cat.status.group_ID != cat.status.group_ID else None
            )

        elif kill_chance <= 15:
            create_short_event(
                event_type="misc",
                main_cat=cat,
                random_cat=chosen_cat,
                sub_type=["failed_murder"],
                clan=clan,
                second_clan=chosen_cat.status.fetch_clan_object(game.clan) if chosen_cat.status.group_ID != cat.status.group_ID else None
            )


        # will this cat actually murder? this takes into account stability and lawfulness
        murder_capable = 7
        if cat.personality.stability < 6:
            murder_capable -= 3
        if cat.personality.lawfulness < 6:
            murder_capable -= 2
        if cat.personality.aggression > 10:
            murder_capable -= 1
        elif cat.personality.aggression > 12:
            murder_capable -= 3

        murder_capable = max(1, murder_capable)

        if random.getrandbits(murder_capable) != 1:
            return

        # If random murder is not triggered, targets can only be those they have some dislike for
        # If random murder is not triggered, targets can only be those they have extreme negativity for
        negative_relation = [
            i
            for i in relationships
            if i.has_extreme_negative
            and Cat.fetch_cat(i.cat_to).status.alive_in_player_clan
        ]
        targets.extend(negative_relation)

        # if we have some, then we need to decide if this cat will kill
        if targets:
            chosen_target = random.choice(targets)

            kill_chance = constants.CONFIG["death_related"]["base_murder_kill_chance"]

            extreme_neg = len(
                [l for l in chosen_target.get_reltype_tiers() if l.is_extreme_neg]
            )
            neg = len(
                [
                    l
                    for l in chosen_target.get_reltype_tiers()
                    if (l.is_low_neg or l.is_mid_neg)
                ]
            )

            relation_modifier = (extreme_neg * 10) + (neg * 5)

            kill_chance -= relation_modifier

            if (
                len(chosen_target.log) > 0
                and "(high negative effect)" in chosen_target.log[-1]
            ):
                kill_chance -= 50

            if (
                len(chosen_target.log) > 0
                and "(medium negative effect)" in chosen_target.log[-1]
            ):
                kill_chance -= 20

            # little easter egg just for fun
            if (
                cat.personality.trait == "ambitious"
                and Cat.fetch_cat(chosen_target.cat_to).status.is_leader
            ):
                kill_chance -= 10

            kill_chance = max(1, int(kill_chance))

            if not int(random.random() * kill_chance):
                print(
                    cat.name, "TARGET CHOSEN", Cat.fetch_cat(chosen_target.cat_to).name
                )
                print("KILL KILL KILL")

                create_short_event(
                    event_type="birth_death",
                    main_cat=Cat.fetch_cat(chosen_target.cat_to),
                    random_cat=cat,
                    sub_type=["murder"],
                )

def handle_disaster(current_disaster, resource=[]):
    if not current_disaster:
        return

    current_moon = game.clan.disaster_moon
    if current_moon == 0:
        event_string = random.choice(current_disaster["trigger_events"])
        game.clan.disaster_moon += 1
    elif current_moon < current_disaster["duration"]:
        
        possible_events = current_disaster["progress_events"]["moon" + str(current_moon)]

        possible_events = [
            event
            for event in possible_events
            if not (not game.clan.leader and "lead_name" in event)
            and not (not game.clan.deputy and "dep_name" in event)
            and not (not game.clan.medicine_cat and "med_name" in event)
        ]

        event_string = random.choice(possible_events)

        game.clan.disaster_moon += 1
        handle_disaster_impacts(current_disaster)
        if (
            random.randint(1,30) == 1 and
            not game.clan.second_disaster and
            current_disaster["secondary_disasters"]
            ):
            game.clan.second_disaster = random.choice(list(current_disaster["secondary_disasters"].keys()))
            secondary_event_string = random.choice(
                current_disaster["secondary_disasters"][game.clan.second_disaster]["trigger_events"]
                )
            secondary_event_string = ongoing_event_text_adjust(Cat, secondary_event_string)
            game.cur_events_list.append(
                    Single_Event(secondary_event_string, "alert"))
    else:
        event_string = random.choice(current_disaster["conclusion_events"])
        game.clan.disaster_moon = 0
        game.clan.disaster = ""
    
    event_string = ongoing_event_text_adjust(Cat, event_string)
    game.cur_events_list.insert(0, 
                    Single_Event(event_string, "alert"))
    if game.clan.second_disaster:
        handle_second_disaster(resource=resource)

def handle_disaster_impacts(current_disaster):      
    for i in range(random.randint(0,2)):
        cat = Cat.all_cats.get(random.choice(game.clan.clan_cats))
        for j in range(20):
            if cat.status.is_outsider or cat.dead or cat.moons < 6:
                cat = Cat.all_cats.get(random.choice(game.clan.clan_cats))
            else:
                break
        if cat.status.is_outsider or cat.dead or cat.moons < 6:
            return
        if current_disaster["collateral_damage"]:
            if random.randint(1,10) == 1:
                if random.randint(1,5) == 1:
                    herbs = game.clan.herb_supply.entire_supply.copy()
                    for herb in herbs:
                        adjust_by = random.choices([-3, -2, -1], [1, 2, 3],
                                                k=1)
                        game.clan.herb_supply.entire_supply[herb] += adjust_by[0]
                        if game.clan.herb_supply.entire_supply[herb] <= 0:
                            game.clan.herb_supply.entire_supply.pop(herb)
                if random.randint(1,5) == 1 and game.clan.freshkill_pile:
                    game.clan.freshkill_pile.total_amount = game.clan.freshkill_pile.total_amount * 0.7
            if random.randint(1,10) != 1:
                if "injuries" in current_disaster["collateral_damage"]:
                    cat.get_injured(random.choice(current_disaster["collateral_damage"]["injuries"]))
            else:
                if "deaths" in current_disaster["collateral_damage"]:
                    if cat.status.rank == CatRank.LEADER:
                        cat.history.add_death(death_text=current_disaster["collateral_damage"]["deaths"]["history_text"]["lead_death"])
                    else:
                        cat.history.add_death(death_text=current_disaster["collateral_damage"]["deaths"]["history_text"]["reg_death"])
                    cat.die()
                    death_text = random.choice(current_disaster["collateral_damage"]["deaths"]["death_text"]).replace("m_c", str(cat.name)).replace("c_n", str(game.clan.displayname) + "Clan")
                    game.cur_events_list.insert(0,
                        Single_Event(death_text, "birth_death", cat.ID))

def handle_second_disaster(resource=None):
    disaster_text = resource
    if not resource:
        return
    current_disaster = disaster_text.get(game.clan.second_disaster)
    current_moon = game.clan.second_disaster_moon
    if current_disaster and current_moon > 0 and current_moon < current_disaster["duration"]:

        possible_events = current_disaster["progress_events"]["moon" + str(current_moon)]

        possible_events = [
            event
            for event in possible_events
            if not (not game.clan.leader and "lead_name" in event)
            and not (not game.clan.deputy and "dep_name" in event)
            and not (not game.clan.medicine_cat and "med_name" in event)
        ]

        event_string = random.choice(possible_events)
        event_string = ongoing_event_text_adjust(Cat, event_string)
        game.clan.second_disaster_moon += 1
        game.cur_events_list.insert(0,
                    Single_Event(event_string, "alert"))
    elif current_disaster and current_moon == current_disaster["duration"]:

        possible_events = current_disaster["conclusion_events"]

        possible_events = [
            event
            for event in possible_events
            if not (not game.clan.leader and "lead_name" in event)
            and not (not game.clan.deputy and "dep_name" in event)
            and not (not game.clan.medicine_cat and "med_name" in event)
        ]

        event_string = random.choice(possible_events)

        game.clan.second_disaster_moon = 0
        game.clan.second_disaster = ""
        event_string = ongoing_event_text_adjust(Cat, event_string)
        game.cur_events_list.insert(0,
                    Single_Event(event_string, "alert"))

def handle_illnesses_or_illness_deaths(cat, clan):
    """
    This function will handle:
        - expanded mode: getting a new illness (extra function in own class)
    Returns:
        - boolean if a death event occurred or not
    """
    # ---------------------------------------------------------------------------- #
    #                           decide if cat dies                                 #
    # ---------------------------------------------------------------------------- #
    # if triggered_death is True then the cat will die
    triggered_death = False
    triggered_death = Condition_Events.handle_illnesses(
        cat, game.clan.current_season, clan=clan
    )
    return triggered_death

def handle_outbreaks(cat, clan):
    """Try to infect some cats."""
    # check if the cat is ill,
    # or if Clan has sufficient med cats
    if not cat.is_ill():
        return

    # check how many kitties are already ill
    already_sick = list(
        filter(
            lambda kitty: (kitty.status.group_ID == clan.group_ID and kitty.is_ill()),
            Cat.all_cats.values(),
        )
    )
    already_sick_count = len(already_sick)

    # round up the living kitties
    alive_cats = list(
        filter(
            lambda kitty: (
                kitty.status.group_ID == clan.group_ID and not kitty.is_ill()
            ),
            Cat.all_cats.values(),
        )
    )
    alive_count = len(alive_cats)

    # if large amount of the population is already sick, stop spreading
    if already_sick_count >= alive_count * 0.25:
        return

    meds = find_alive_cats_with_rank(
        Cat,
        [CatRank.MEDICINE_CAT, CatRank.MEDICINE_APPRENTICE],
        working=True,
        sort=True,
        clan=clan.group_ID
    )

    for illness in cat.illnesses:
        # check if illness can infect other cats
        if cat.illnesses[illness]["infectiousness"] == 0:
            continue
        chance = cat.illnesses[illness]["infectiousness"]
        chance += len(meds) * 7
        if not int(random.random() * chance):  # 1/chance to infect
            # fleas are the only condition allowed to spread outside of cold seasons
            if (
                game.clan.current_season not in ["Leaf-bare", "Leaf-fall"]
                and illness != "fleas"
            ):
                continue

            if get_clan_setting("rest_and_recover") and clan == game.clan:
                stopping_chance = constants.CONFIG["focus"]["rest_and_recover"][
                    "outbreak_prevention"
                ]
                if not int(random.random() * stopping_chance):
                    continue

            if illness == "kittencough":
                # adjust alive cats list to only include kittens
                alive_cats = list(
                    filter(
                        lambda kitty: (
                            kitty.status.rank.is_baby()
                            and kitty.status.group_ID == clan.group_ID
                        ),
                        Cat.all_cats.values(),
                    )
                )
                alive_count = len(alive_cats)

            max_infected = int(alive_count / 2)  # 1/2 of alive cats
            # If there are less than two cat to infect,
            # you are allowed to infect all the cats
            if max_infected < 2:
                max_infected = alive_count
            # If, event with all the cats, there is less
            # than two cats to infect, cancel outbreak.
            if max_infected < 2:
                return

            weights = []
            population = []
            for n in range(2, max_infected + 1):
                population.append(n)
                weight = 1 / (0.75 * n)  # Lower chance for more infected cats
                weights.append(weight)
            infected_count = random.choices(population, weights=weights)[
                0
            ]  # the infected..

            infected_names = []
            involved_cats = []
            infected_cats = random.sample(alive_cats, infected_count)
            for sick_meowmeow in infected_cats:
                infected_names.append(str(sick_meowmeow.name))
                involved_cats.append(sick_meowmeow.ID)
                sick_meowmeow.get_ill(
                    illness, event_triggered=True
                )  # SPREAD THE GERMS >:)

            # TODO: hardcoded text events, not good, need to consider how to convert
            #  should this be handled in condition_events.py?
            if illness == "kittencough":
                event = i18n.t(
                    "hardcoded.kittencough_spread",
                    kits=adjust_list_text(infected_names),
                    count=len(infected_names),
                )
            elif illness == "fleas":
                event = i18n.t(
                    "hardcoded.flea_spread",
                    cats=adjust_list_text(infected_names),
                    count=len(infected_names)-1,
                )
            else:
                event = i18n.t(
                    "hardcoded.illness_spread",
                    illness=str(illness).capitalize(),
                    cats=adjust_list_text(infected_names),
                    count=len(infected_names),
                )

            game.cur_events_list.append(
                Single_Event(event, "health", involved_cats, clan=clan.group_ID)
            )
            # game.health_events_list.append(event)
            break

def change_group_events(new_group_ID):
    """
    LG: Events for when the MC successfully switches groups.
    """
    event = "You have joined a new group: " + game.used_group_IDs[new_group_ID]
    game.cur_events_list.append(
        Single_Event(event, "alert", [game.clan.your_cat.ID])
    )

def exile_or_forgive(cat):
    """
    LG: a shunned cat becoming exiled or forgiven
    """
    involved_cats = []
    involved_cats.append(cat.ID)

    if game.clan.your_cat.ID == cat.ID:
        fate = int((constants.CONFIG["lifegen"]["shunned_cat"]["exile_chance"][cat.age.replace(' ', '_')]) * 1.75)
    else:
        fate = int(constants.CONFIG["lifegen"]["shunned_cat"]["exile_chance"][cat.age.replace(' ', '_')])

    if not int(random.random() * fate):
        cat.status.exile_from_group()
        text = event_text_adjust(
            Cat,
            text=(
                "m_c has been exiled from c_n."
                if cat.ID != game.clan.your_cat.ID
                else "You have been exiled from c_n."
                ),
            main_cat=cat,
            clan=game.clan
        )
    else:
        cat.status.unshun_from_group(cat.status.group_ID)
        text = event_text_adjust(
            Cat,
            text=(
                "m_c has been unshunned and welcomed back into c_n."
                if cat.ID != game.clan.your_cat.ID
                else "You have been unshunned and welcomed back into c_n."
                ),
            main_cat=cat,
            clan=game.clan
        )


    game.cur_events_list.insert(0, Single_Event(text, ["alert", "misc"], involved_cats))

def generate_faith_events(cat):
    """ yay """
    if (
        cat.status.is_outsider or
        cat.dead or
        cat.moons < 1
    ):
        return
    
    random_cat = random.choice(get_living_cats())

    create_short_event(event_type="faith",
                            main_cat=cat,
                            random_cat=random_cat,
                            sub_type=[])
    

def coming_out(cat, clan):
    """turnin' the kitties trans..."""

    if cat.moons < 3 or cat.gender != cat.genderalign:
        return

    transing_chance = constants.CONFIG["transition_related"]
    chance = transing_chance["base_trans_chance"]
    if cat.age in [CatAge.ADOLESCENT, CatAge.KITTEN]:
        chance += transing_chance["adolescent_modifier"]
    elif cat.age in [CatAge.ADULT, CatAge.SENIOR_ADULT, CatAge.SENIOR]:
        chance += transing_chance["older_modifier"]

    if not int(random.random() * chance):
        sub_type = ["transition"]
        create_short_event(
            event_type="misc",
            main_cat=cat,
            sub_type=sub_type,
            clan=clan
        )

    return

def check_and_promote_leader(clan):
    """Checks if a new leader need to be promoted, and promotes them, if needed."""
    # check for leader
    if clan.leader:
        leader_invalid = clan.leader.status.group_ID == clan.group_ID
    else:
        leader_invalid = True

    if leader_invalid:
        perform_ceremonies(
            None, clan
        )  # This is where the deputy will be make leader

        if clan.leader:
            leader_dead = clan.leader.dead
            leader_outside = clan.leader.status.group_ID != clan.group_ID
        else:
            leader_dead = True
            leader_outside = True


        if leader_dead or leader_outside:
            string = i18n.t("defaults.warn_no_leader")
            game.cur_events_list.insert(
                0,
                Single_Event(
                    event_text_adjust(
                        Cat, string, clan=clan
                    ),
                    clan=clan.group_ID
                ),
            )

def rel_deputy_filter(cat_list, leader):
    has_rel = []
    values = {}
    for c in cat_list:
        if c.ID in leader.relationships:
            has_rel.append(c)
            values[c.ID] = leader.relationships[c.ID].respect * 3 + leader.relationships[c.ID].trust * 2 + leader.relationships[c.ID].like + leader.relationships[c.ID].comfort
    if not has_rel:
        return cat_list

    has_rel.sort( reverse=True,
        key=lambda c: leader.relationships[c.ID].respect * 3 + leader.relationships[c.ID].trust * 2 + leader.relationships[c.ID].like + leader.relationships[c.ID].comfort)

    if leader.relationships[has_rel[0].ID].respect * 3 + leader.relationships[has_rel[0].ID].trust * 2 + leader.relationships[has_rel[0].ID].romance + leader.relationships[has_rel[0].ID].like + leader.relationships[has_rel[0].ID].comfort < 0:
        return cat_list
    for i, c in enumerate(has_rel):
        if i > 5:
            break
        if i <= 5 and values[c.ID] < 0:
            has_rel = has_rel[:i]
            break

    return has_rel[:min(5, len(has_rel))]

def check_and_promote_deputy(clan=None):
    # TODO: can these events be handled as ceremony events?

    """Checks if a new deputy needs to be appointed, and appointed them if needed."""
    if (
        not clan.deputy
        or clan.deputy.status.group_ID != clan.group_ID
        or clan.deputy.status.rank == CatRank.ELDER
    ):
        if not get_clan_setting("deputy") and clan == game.clan:
            game.cur_events_list.insert(0, Single_Event(
                event_text_adjust(Cat, "defaults.warn_no_deputy", clan=clan), clan=clan.group_ID))
            return
        # This determines all the cats who are eligible to be deputy.
        possible_deputies = list(
            filter(
                lambda x: x.status.group_ID == clan.group_ID
                and x.status.rank == CatRank.WARRIOR
                and ([i for i in x.former_apprentices if Cat.all_cats.get(i) and not Cat.all_cats.get(i).status.rank.is_any_apprentice_rank()]),
                Cat.all_cats_list,
            )
        )
        if not possible_deputies:
            possible_deputies = list(
                filter(
                    lambda x: x.status.group_ID == clan.group_ID
                    and x.status.rank == CatRank.WARRIOR
                    and (x.apprentice or x.former_apprentices),
                    Cat.all_cats_list))
        if get_clan_setting("rel_deputy") and clan.leader:
            possible_deputies = rel_deputy_filter(possible_deputies, clan.leader)

        # If there are possible deputies, choose from that list.
        if possible_deputies:
            random_cat = random.choice(possible_deputies)
            involved_cats = [random_cat.ID]

            # Gather deputy and leader status, for determination of the text.
            if clan.leader:
                if not clan.leader.status.group_ID == clan.group_ID:
                    leader_status = "not_here"
                else:
                    leader_status = "here"
            else:
                leader_status = "not_here"

            if clan.deputy:
                if not clan.deputy.status.group_ID == clan.group_ID:
                    deputy_status = "not_here"
                else:
                    deputy_status = "here"
            else:
                deputy_status = "not_here"

            if leader_status == "here" and deputy_status == "not_here":
                if random_cat.personality.trait == "bloodthirsty":
                    text = i18n.t("hardcoded.ceremony_deputy_bloodthirsty")
                    # No additional involved cats
                else:
                    if clan.deputy:
                        previous_deputy_mention = i18n.t(
                            f"hardcoded.ceremony_deputy_prev{random.choice(range(0, 3))}"
                        )
                        involved_cats.append(clan.deputy.ID)

                    else:
                        previous_deputy_mention = ""

                    text = i18n.t(
                        "hardcoded.ceremony_deputy",
                        previous=previous_deputy_mention,
                    )

                    involved_cats.append(clan.leader.ID)
            elif leader_status == "not_here" and deputy_status == "here":
                text = i18n.t("hardcoded.ceremony_deputy_nolead_retireddep")
            elif leader_status == "not_here" and deputy_status == "not_here":
                text = i18n.t("hardcoded.ceremony_deputy_nolead_nodep")
            elif leader_status == "here" and deputy_status == "here":
                # No additional involved cats
                text = i18n.t(
                    f"hardcoded.ceremony_deputy_lead_retireddep{random.choice(range(0, 5))}"
                )
            else:
                # This should never happen. Failsafe.
                text = i18n.t("defaults.deputy_event")
        else:
            # If there are no possible deputies, choose someone else, with special text.
            all_warriors = list(
                filter(
                    lambda x: x.status.group_ID == clan.group_ID
                    and x.status.rank == CatRank.WARRIOR,
                    Cat.all_cats_list,
                )
            )
            if all_warriors:
                if get_clan_setting("rel_deputy") and clan.leader:
                    all_warriors = rel_deputy_filter(all_warriors, clan.leader)
                random_cat = random.choice(all_warriors)
                involved_cats = [random_cat.ID]
                text = i18n.t("hardcoded.ceremony_deputy_unsuitable")

            else:
                # If there are no warriors at all, no one is named deputy.
                game.cur_events_list.append(
                    Single_Event(
                        i18n.t("hardcoded.ceremony_deputy_none"), "ceremony", 
                        clan=clan.group_ID
                    )
                )
                return

        text = event_text_adjust(Cat, text, main_cat=random_cat, clan=clan)
        random_cat.rank_change(CatRank.DEPUTY)
        clan.deputy = random_cat

        game.cur_events_list.append(Single_Event(text, "ceremony", involved_cats,
                                                    clan=clan.group_ID))


load_ceremonies()
load_war_resources()
