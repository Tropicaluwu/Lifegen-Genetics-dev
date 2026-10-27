# pylint: disable=line-too-long
"""

TODO: Docs


"""
# testt
# pylint: enable=line-too-long

import logging
import os
import statistics
from random import choice, randint, random

import ujson

from scripts.cat.cats import Cat, create_cat, cat_class, BACKSTORIES
from scripts.cat.enums import CatRank, CatGroup, CatSocial
from scripts.cat_relations.inheritance import Inheritance
from scripts.cat.names import names
from scripts.cat.save_load import (
    save_cats,
    get_faded_ids,
    load_faded_cat_ids,
)
from scripts.game_structure.game.settings import game_setting_get
from scripts.clan_package.settings import save_clan_settings, load_clan_settings, get_clan_setting
from scripts.clan_package.settings.clan_settings import reset_loaded_clan_settings
from scripts.clan_resources.freshkill import FreshkillPile, Nutrition
from scripts.clan_resources.herb.herb_supply import HerbSupply
from scripts.events_module.future.future_event import FutureEvent
from scripts.events_module.generate_events import OngoingEvent
from scripts.game_structure import constants
from scripts.game_structure.game.save_load import safe_save, save_clanlist, read_clans
from scripts.game_structure.game.switches import (
    switch_set_value,
    switch_get_value,
    Switch,
)
from scripts.game_structure import game
from scripts.cat.pelts import Pelt
from scripts.housekeeping.datadir import get_save_dir
from scripts.housekeeping.version import get_version_info, SAVE_VERSION_NUMBER
from scripts.clan_package.clan_symbols import clan_symbol_sprite
from scripts.events_module.consequences import create_new_cat
from scripts.clan_package.get_clan_cats import (
    get_living_clan_cat_count,
    find_alive_cats_with_rank,
)
from scripts.screens.screens_core.screens_core import rebuild_top_menu_buttons

from scripts.events_module.consequences import (
    create_new_cat
)
from scripts.clan_package.get_clan_cats import (
    get_possible_mates
)

logger = logging.getLogger(__name__)


class Clan:
    """

    TODO: Docs

    """

    leader_lives = 0
    clan_cats = []

    age = 0
    all_other_clans = []

    grief_strings = {}

    def __init__(
        self,
        name="",
        leader=None,
        deputy=None,
        medicine_cat=None,
        biome="Forest",
        camp_bg=None,
        rogue_group_bg=None,
        loner_group_bg=None,
        household_bg=None,
        no_group_bg=None,
        symbol=None,
        game_mode="classic",
        cruel_cards: list[str] = [],
        starting_members=None,
        starting_season="Newleaf",
        followingsc=True,
        your_cat=None,
        focus_cat=None,
        clan_age=None,
        relations={CatGroup.PLAYER_CLAN_ID: {}},
        self_run_init_functions=True,
        displayname="",
    ):
        """
        :param name: The save file name for the Clan, this should not be used for player-facing text beyond the save file screen
        :param displayname: The display name for the Clan, this is what should appear while the playing the game.
        """
        if name == "":
            return

        if starting_members is None:
            starting_members = []

        self.group_ID = CatGroup.PLAYER_CLAN_ID
        # name is the unique id of the clan. i'm sorry if this is confusing...
        # TODO: change to better name like clan_id
        self.name = name
        # displayname is the name you should use whenever displaying the clan name in UI
        if not displayname:
            self.displayname = name
        else:
            self.displayname = displayname
        self.clancount = "singleclan"
        self.leader = leader
        self.leader_lives = 9
        self.leader_predecessors = 0
        self.deputy = deputy
        self.deputy_predecessors = 0
        self.medicine_cat = medicine_cat
        self.med_cat_list = []
        self.med_cat_predecessors = 0

        self.med_cat_number = len(
            self.med_cat_list
        )  # Must do this after the healer is added to the list.
        self.age = 0
        self.starting_season = starting_season
        self.instructor = None
        # ^^ starclan guide

        self.clan_cats = []
        self.biome = biome
        self.override_biome = None
        self.camp_bg = camp_bg
       
        self.rogue_group_bg = rogue_group_bg
        self.loner_group_bg = loner_group_bg
        self.household_bg = household_bg
        self.no_group_bg = no_group_bg
        
        self.chosen_symbol = symbol
        self.game_mode = game_mode
        self.cruel_cards: list[str] = cruel_cards
        self.pregnancy_data = {}
        self.inheritance = {}
        # NEW LG STUFF
        self.demon = None
        # ^^ dark forest guide
        self.followingsc = followingsc
        
        self.your_cat = your_cat
        self.murdered = {}
        self.exile_return = False
        self.affair = False
        self.achievements = []
        self.talks = []
        self.focus = ""
        self.focus_moons = 0
        self.focus_cat = focus_cat
        self.clan_age = clan_age if clan_age else "established"
        self.custom_pronouns = {}

        switch_set_value(Switch.biome, biome)

        switch_set_value(Switch.camp_bg, camp_bg)
        switch_set_value(Switch.rogue_group_bg, rogue_group_bg)
        switch_set_value(Switch.loner_group_bg, loner_group_bg)
        switch_set_value(Switch.household_bg, household_bg)
        switch_set_value(Switch.no_group_bg, no_group_bg)

        switch_set_value(Switch.game_mode, game_mode)

        # Reputation is for loners/kittypets/outsiders in general that wish to join the clan.
        # it's a range from 1-100, with 30-70 being neutral, 71-100 being "welcoming",
        # and 1-29 being "hostile". if you're hostile to outsiders, they will VERY RARELY show up.
        self._reputation = 80
        self.relations = relations if relations.get(self.group_ID) else {CatGroup.PLAYER_CLAN_ID: {}}

        self.all_other_clans: list[OtherClan] = []
        self.other_clan_IDs = []

        self.starting_members = starting_members
        if game_mode in ("expanded", "cruel season"):
            self.freshkill_pile = FreshkillPile()
        else:
            self.freshkill_pile = None
        self.herb_supply = HerbSupply()
        self.primary_disaster = None
        self.secondary_disaster = None
        self.war = {CatGroup.PLAYER_CLAN_ID: {}}
        self.future_events = []
        self.last_focus_change = None
        self.clans_in_focus = []

        if self_run_init_functions:
            self.post_initialization_functions()
        self.disaster = ""
        self.second_disaster = ""
        self.disaster_moon = 0
        self.second_disaster_moon = 0

        rebuild_top_menu_buttons()

    @property
    def current_season(self):
        modifiers = {"Newleaf": 0, "Greenleaf": 3, "Leaf-fall": 6, "Leaf-bare": 9}
        return (
            self.starting_season
            if constants.CONFIG["lock_season"]
            else constants.SEASON_CALENDAR[
                (self.age + modifiers[self.starting_season]) % 12
            ]
        )

    # The clan couldn't save itself in time due to issues arising, for example, from this function: "if deputy is not
    # None: self.deputy.status_change('deputy') -> game.clan.remove_med_cat(self)"
    def post_initialization_functions(self):
        if self.deputy and self.deputy.status.alive_in_player_clan:
            self.deputy.rank_change(CatRank.DEPUTY, new_thought=False)
            self.clan_cats.append(self.deputy.ID)

        if self.leader and self.leader.status.alive_in_player_clan:
            self.leader.rank_change(CatRank.LEADER, new_thought=False)
            self.clan_cats.append(self.leader.ID)

        if self.medicine_cat and self.medicine_cat.status.alive_in_player_clan:
            self.clan_cats.append(self.medicine_cat.ID)
            self.med_cat_list.append(self.medicine_cat.ID)
            if self.medicine_cat.status.rank != CatRank.MEDICINE_CAT:
                Cat.all_cats[self.medicine_cat.ID].rank_change(
                    CatRank.MEDICINE_CAT, new_thought=False
                )

    def create_clan(self, clancount="singleclan"):
        """
        This function is only called once a new clan is
        created in the 'clan created' screen, not every time
        the program starts
        """
        game.reset_used_group_IDs()
        switch_set_value(Switch.clan_name, self.name)
        reset_loaded_clan_settings()
        game.reset_group_IDs()
        game.starclan = Afterlife()
        game.dark_forest = Afterlife()
        game.just_died.clear()
        game.dead_cats_to_grieve.clear()
        instructor_rank = choice(
            (
                CatRank.APPRENTICE,
                CatRank.MEDIATOR_APPRENTICE,
                CatRank.MEDICINE_APPRENTICE,
                CatRank.WARRIOR,
                CatRank.MEDICINE_CAT,
                CatRank.LEADER,
                CatRank.MEDIATOR,
                CatRank.DEPUTY,
                CatRank.ELDER,
                CatRank.QUEEN,
                CatRank.QUEENS_APPRENTICE
            )
        )

        self.instructor = Cat(
            status_dict={"rank": instructor_rank, "group_ID": CatGroup.STARCLAN_ID},
            backstory=choice(
                BACKSTORIES["backstory_categories"]["new_sc_guide_backstories"]
            ) if self.clan_age == "new" else choice(
                BACKSTORIES["backstory_categories"]["clan_guide_backstories"]
            ),
        )

        self.clancount = clancount
        self.instructor.status.group_history.insert(0, {"rank": instructor_rank, "group": CatGroup.PLAYER_CLAN_ID, "moons_as": self.instructor.moons})
        self.instructor.dead_for = randint(20, 200)

        self.add_cat(self.instructor)
        
        self.demon = Cat(
            status_dict={"rank": instructor_rank, "group_ID": CatGroup.DARK_FOREST_ID},
            backstory=choice(
                BACKSTORIES["backstory_categories"]["new_df_guide_backstories"]
            ) if self.clan_age == "new" else choice(
                BACKSTORIES["backstory_categories"]["df_backstories"]
            ),
        )

        self.demon.dead_for = randint(20, 200)
        self.add_cat(self.demon)
        self.all_other_clans = []

        key_copy = tuple(Cat.all_cats.keys())
        for i in key_copy:  # Going through all currently existing cats
            # cat_class is a Cat-object
            not_found = True

            for x in self.starting_members:
                if Cat.all_cats[i] == x:
                    self.add_cat(Cat.all_cats[i])
                    not_found = False
            if (
                Cat.all_cats[i] != self.leader
                and Cat.all_cats[i] != self.medicine_cat
                and Cat.all_cats[i] != self.deputy
                and Cat.all_cats[i] != self.instructor
                and Cat.all_cats[i] != self.demon
                and not_found
            ):
                Cat.all_cats[i].example = True
                self.remove_cat(Cat.all_cats[i].ID)

        allowed_range = constants.CONFIG["clan_creation"]["other_clans_range"]
        number_other_clans = randint(allowed_range[0], allowed_range[1])
        for _ in range(number_other_clans):
            other_clan_names = [str(i.displayname) for i in self.all_other_clans] + [
                game.clan.displayname
            ]
            other_clan_name = choice(
                names.names_dict["normal_prefixes"] + names.names_dict["clan_prefixes"]
            )
            while other_clan_name in other_clan_names:
                other_clan_name = choice(
                    names.names_dict["normal_prefixes"]
                    + names.names_dict["clan_prefixes"]
                )
            other_clan = OtherClan(name=other_clan_name, clancount=self.clancount)
            game.clan.relations[CatGroup.PLAYER_CLAN_ID][other_clan.group_ID] = randint(8, 12)
            game.clan.war[CatGroup.PLAYER_CLAN_ID][other_clan.group_ID] = {"at_war": False, "duration": 0}

        if self.clancount == "multiclan":
            for i, clan in enumerate(game.clan.all_other_clans[:-1]):
                game.clan.war[clan.group_ID] = {}
                game.clan.relations[clan.group_ID] = {}
                for o_clan in game.clan.all_other_clans[i+1:]:
                    game.clan.relations[clan.group_ID][o_clan.group_ID] = randint(8, 12)
                    game.clan.war[clan.group_ID][o_clan.group_ID] = {"at_war": False, "duration": 0}

        self.save_clan()
        # this has to be done after saving the first time
        # doing this without any previous clans will cause a crash otherwise
        if self.clan_age == "established":
            self.generate_mates()
            self.generate_families()
            self.populate_sc()
            self.populate_ur()
            self.populate_df()
        else:
            self.generate_outsiders()
            self.generate_outsider_mates()
            self.generate_outsider_families()

        self.populate_your_group()

        # give thoughts,actions and relationships to cats
        # LIFEGEN: this is moved down to after we generate outsiders and dead cats
        for cat_id in Cat.all_cats:
            if cat_id not in self.clan_cats:
                self.clan_cats.append(cat_id)
            the_cat = Cat.all_cats.get(cat_id)
            the_cat.init_all_relationships()
            if self.clan_age == "new" and the_cat not in (self.instructor, self.demon):
                if the_cat.backstory == "clanborn" and the_cat.status.rank not in (
                    CatRank.KITTEN,
                    CatRank.NEWBORN,
                ):
                    the_cat.backstory = "clan_founder"
            if the_cat.status.rank == CatRank.APPRENTICE:
                the_cat.rank_change(CatRank.APPRENTICE)
            the_cat.get_new_thought()
            the_cat.pelt.rebuild_sprite = True

        # # create leader's ceremony
        # self.leader.generate_lead_ceremony()
        # lifegen commented out
        if self.clancount == "multiclan":
            for clan in self.all_other_clans:
                clan.leader.generate_lead_ceremony()

        save_cats(game.clan.name, Cat, game)
        self.save_clan()
        save_clanlist(self.name)
        switch_set_value(Switch.clan_list, read_clans())

        # CHECK IF CAMP BG IS SET -fail-safe in case it gets set to None-
        # LG: it WILL be set to None if the MC is born outside of it
        if switch_get_value(Switch.camp_bg) is None:
            random_camp_options = ["camp1", "camp2"]
            random_camp = choice(random_camp_options)
            switch_set_value(Switch.camp_bg, random_camp)
        # LG
        if not switch_get_value(Switch.rogue_group_bg):
            switch_set_value(Switch.rogue_group_bg, "camp1")
        if not switch_get_value(Switch.loner_group_bg):
            switch_set_value(Switch.loner_group_bg, "camp1")
        if not switch_get_value(Switch.household_bg):
            switch_set_value(Switch.household_bg, "camp1")
        if not switch_get_value(Switch.no_group_bg):
            switch_set_value(Switch.no_group_bg, "camp1")

        # if no game mode chosen, set to Classic
        if switch_get_value(Switch.game_mode) == "":
            switch_set_value(Switch.game_mode, "classic")
            self.game_mode = "classic"

        rebuild_top_menu_buttons()

    def generate_mates(self):
        """Generates up to three pairs of mates."""

        def get_adult_mateless_cat():
            alive_cats = [i for i in Cat.all_cats.values() if (
                i.moons >= 14 and
                i.status.alive_in_player_clan
                )
                ]
            if alive_cats:
                return choice(alive_cats)
            return None

        num_mates = randint(0,3)

        for i in range(num_mates):
            same_age_cats = []
            random_cat = get_adult_mateless_cat()
            if random_cat:
                same_age_cats = get_possible_mates(random_cat)[0]

            if same_age_cats:
                random_mate_cat = choice(same_age_cats)
                if random_cat.is_potential_mate(random_mate_cat):
                    random_cat.set_mate(random_mate_cat)

    def generate_families(self):

        def get_kit_parent():
            alive_cats = [i for i in Cat.all_cats.values() if (
                i.moons >= 20 and
                i.moons <= 100 and
                i.status.alive_in_player_clan
                )
            ]

            for cat in alive_cats:
                if not cat.inheritance:
                    cat.inheritance = Inheritance(cat)

            alive_cats = [i for i in alive_cats if not i.inheritance.get_blood_kits()]

            if alive_cats:
                return choice(alive_cats)
            return None

        def get_app_parent():
            alive_cats = [i for i in Cat.all_cats.values() if (
                i.moons >= 40 and
                i.moons <= 100 and
                i.status.alive_in_player_clan)]

            for cat in alive_cats:
                if not cat.inheritance:
                    cat.inheritance = Inheritance(cat)

            alive_cats = [i for i in alive_cats if not i.inheritance.get_blood_kits()]

            if alive_cats:
                return choice(alive_cats)
            return None
        
        clan_kits = find_alive_cats_with_rank(Cat, [CatRank.KITTEN])
        clan_apps = find_alive_cats_with_rank(Cat, [
            CatRank.APPRENTICE,
            CatRank.MEDICINE_APPRENTICE,
            CatRank.MEDIATOR_APPRENTICE,
            CatRank.QUEENS_APPRENTICE,
        ])

        if not clan_kits and not clan_apps:
            return
        
        if clan_kits:
            for kit in clan_kits:
                if not kit.inheritance:
                    kit.inheritance = Inheritance(kit)
                if kit.backstory == "clanborn" and not kit.parent1:
                    parent = get_kit_parent()
                    if parent:
                        kit.parent1 = parent.ID
                        parent.inheritance.update_inheritance()

                        if parent.mate:
                            kit.parent2 = choice(parent.mate)
                            if not Cat.all_cats.get(kit.parent2).inheritance:
                                Cat.all_cats.get(kit.parent2).inheritance = Inheritance(Cat.all_cats.get(kit.parent2))
                            Cat.all_cats.get(kit.parent2).inheritance.update_inheritance()

                        for other_kit in clan_kits:
                            if other_kit.ID != kit.ID and kit.moons == other_kit.moons and not other_kit.parent1 and other_kit.backstory == "clanborn":
                                other_kit.parent1 = parent.ID
                                parent.inheritance.update_inheritance()
                                if kit.parent2:
                                    other_kit.parent2 = kit.parent2
                                    Cat.all_cats.get(kit.parent2).inheritance.update_inheritance()
                                    if not other_kit.inheritance:
                                        other_kit.inheritance = Inheritance(other_kit)
                kit.inheritance.update_inheritance()

        if clan_apps:
            for app in clan_apps:
                if app.backstory == "clanborn":
                    parent = get_app_parent()
                    if parent:
                        app.parent1 = parent.ID
                        if not app.inheritance:
                            app.inheritance = Inheritance(app)
                        app.inheritance.update_inheritance()
                        parent.inheritance.update_inheritance()
                        if parent.mate:
                            app.parent2 = choice(parent.mate)
                            if not Cat.all_cats.get(app.parent2).inheritance:
                                Cat.all_cats.get(app.parent2).inheritance = Inheritance(Cat.all_cats.get(app.parent2))
                            app.inheritance.update_inheritance()
                            Cat.all_cats.get(app.parent2).inheritance.update_inheritance()

        for cat in Cat.all_cats.values():
            if not cat.inheritance:
                cat.inheritance = Inheritance(cat)
            else:
                cat.inheritance.update_inheritance()

    def populate_sc(self):
        for i in range(randint(2,5)):
            random_backstory = choice(["dead1",
                "dead3",
                "dead4",
                "dead6",
                "dead8",
                "dead10",
                "dead12",
                "dead15"])
            sc_cat = create_new_cat(
                Cat,
                new_name=True,
                alive=False,
                backstory=random_backstory,
                original_group=CatGroup.NONE
                )[0]
            sc_cat.history.beginning = None
            sc_cat.dead_for = randint(20, 200)
            sc_cat.status.add_to_group(CatGroup.STARCLAN_ID)
            sc_cat.history.add_afterlife_acceptance(
                CatGroup.STARCLAN, is_kit=sc_cat.age.is_baby()
            )
            self.add_cat(sc_cat)

    def populate_ur(self):
        for i in range(randint(2,5)):
            random_backstory = choice(["dead1",
                "dead2",
                "dead3",
                "dead4",
                "dead5",
                "dead6",
                "dead8",
                "dead9",
                "dead10",
                "dead11",
                "dead12"])
            status = choice([CatRank.LONER, CatRank.KITTYPET])
            ur_cat = create_new_cat(
                Cat,
                rank=status,
                alive=False,
                outside=True,
                backstory=random_backstory,
                original_social=CatSocial.LONER
                )[0]
            ur_cat.history.beginning = None
            ur_cat.dead_for = randint(20,100)
            ur_cat.status.add_to_group(CatGroup.UNKNOWN_RESIDENCE_ID)
            self.add_cat(ur_cat)

    def populate_df(self):
        for i in range(randint(2,5)):
            random_backstory = choice(["dead2",
                "dead5",
                "dead7",
                "dead8",
                "dead9",
                "dead11",
                "dead12",
                "dead13",
                "dead14"])
            df_cat = create_new_cat(
                Cat,
                new_name=True,
                alive=False,
                backstory=random_backstory,
                original_group=CatGroup.NONE
                )[0]
            df_cat.history.beginning = None
            df_cat.dead_for = randint(20, 200)
            df_cat.status.add_to_group(CatGroup.DARK_FOREST_ID)
            df_cat.history.add_afterlife_acceptance(
                CatGroup.DARK_FOREST, is_kit=df_cat.age.is_baby()
            )
            self.add_cat(df_cat)


    def generate_outsiders(self):
        for i in range(randint(0,5)):
            outsider = create_new_cat(
                Cat,
                moons=randint(15, 120),
                outside=True,
                original_social=choice(
                    (CatSocial.LONER, CatSocial.ROGUE, CatSocial.KITTYPET)
                ),
                )[0]
            outsider.history.beginning = None
            self.add_cat(outsider)

    def generate_outsider_mates(self):
        """Generates up to three pairs of mates."""

        def get_adult_mateless_cat():
            alive_cats = [i for i in Cat.all_cats.values() if i.moons >= 14 and not i.dead and not i.mate]
            if alive_cats:
                return choice(alive_cats)
            return None

        num_mates = randint(0,3)

        for i in range(num_mates):
            same_age_cats = []
            random_cat = get_adult_mateless_cat()
            if random_cat:
                same_age_cats = get_possible_mates(random_cat)[0]

            if same_age_cats:
                random_mate_cat = choice(same_age_cats)
                if random_cat.is_potential_mate(random_mate_cat):
                    random_cat.set_mate(random_mate_cat)

    def generate_outsider_families(self):
        def get_kit_parent():
            alive_cats = [i for i in Cat.all_cats.values() if i.moons >= 20 and i.moons <= 100 and not i.dead]

            for cat in alive_cats:
                if not cat.inheritance:
                    cat.inheritance = Inheritance(cat)

            alive_cats = [i for i in alive_cats if not i.inheritance.get_blood_kits()]

            if alive_cats:
                return choice(alive_cats)
            return None

        def get_app_parent():
            alive_cats = [i for i in Cat.all_cats.values() if i.moons >= 40 and i.moons <= 100 and not i.dead]

            for cat in alive_cats:
                if not cat.inheritance:
                    cat.inheritance = Inheritance(cat)

            alive_cats = [i for i in alive_cats if not i.inheritance.get_blood_kits()]

            if alive_cats:
                return choice(alive_cats)
            return None
        
        clan_kits = find_alive_cats_with_rank(Cat, [CatRank.NEWBORN, CatRank.KITTEN])
        clan_apps = find_alive_cats_with_rank(Cat, [
            CatRank.APPRENTICE,
            CatRank.MEDICINE_APPRENTICE,
            CatRank.MEDIATOR_APPRENTICE,
            CatRank.QUEENS_APPRENTICE,
        ])

        if not clan_kits and not clan_apps:
            return
        
        if clan_kits:
            for kit in clan_kits:
                if not kit.inheritance:
                    kit.inheritance = Inheritance(kit)
                if kit.ID != game.clan.your_cat.ID and not kit.parent1:
                    parent = get_kit_parent()
                    if parent:
                        kit.parent1 = parent.ID
                        parent.inheritance.update_inheritance()

                        if parent.mate:
                            kit.parent2 = choice(parent.mate)
                            if not Cat.all_cats.get(kit.parent2).inheritance:
                                Cat.all_cats.get(kit.parent2).inheritance = Inheritance(Cat.all_cats.get(kit.parent2))
                            Cat.all_cats.get(kit.parent2).inheritance.update_inheritance()

                        for other_kit in clan_kits:
                            if other_kit.ID != kit.ID and other_kit.ID != game.clan.your_cat.ID and kit.moons == other_kit.moons and not other_kit.parent1:
                                other_kit.parent1 = parent.ID
                                parent.inheritance.update_inheritance()
                                if kit.parent2:
                                    other_kit.parent2 = kit.parent2
                                    Cat.all_cats.get(kit.parent2).inheritance.update_inheritance()
                                    if not other_kit.inheritance:
                                        other_kit.inheritance = Inheritance(other_kit)
                kit.inheritance.update_inheritance()

        if clan_apps:
            for app in clan_apps:
                parent = get_app_parent()
                if parent:
                    app.parent1 = parent.ID
                    if not app.inheritance:
                        app.inheritance = Inheritance(app)
                    app.inheritance.update_inheritance()
                    parent.inheritance.update_inheritance()
                    if parent.mate:
                        app.parent2 = choice(parent.mate)
                        if not Cat.all_cats.get(app.parent2).inheritance:
                            Cat.all_cats.get(app.parent2).inheritance = Inheritance(Cat.all_cats.get(app.parent2))
                        app.inheritance.update_inheritance()
                        Cat.all_cats.get(app.parent2).inheritance.update_inheritance()

    def populate_your_group(self):
        if not game.clan.your_cat:
            return
        group_ID = game.clan.your_cat.status.group_ID

        info_dict = {
            CatGroup.ROGUE_GROUP_ID: {
                "range": [0, 5],
                "social": CatSocial.ROGUE,
                "rank": CatRank.ROGUE
            },
            CatGroup.LONER_GROUP_ID: {
                "range": [0, 5],
                "social": CatSocial.LONER,
                "rank": CatRank.LONER
            },
            CatGroup.HOUSEHOLD_ID: {
                "range": [0, 2],
                "social": CatSocial.KITTYPET,
                "rank": CatRank.KITTYPET
            }
        }

        if group_ID not in info_dict:
            return

        for i in range(info_dict[group_ID]["range"][0], info_dict[group_ID]["range"][1]):
            new_cat = create_new_cat(
                Cat,
                rank=info_dict[group_ID]["rank"],
                original_social=info_dict[group_ID]["social"],
                new_name=False,
                outside=True
                )[0]
            new_cat.history.beginning = None
            self.add_cat(new_cat)
            new_cat.status.add_to_group(group_ID)
            # print("Adding", new_cat.name, "to your group!", new_cat.status.group, game.clan.your_cat.status.group)
            # print(new_cat.ID)

    def add_cat(self, cat):  # cat is a 'Cat' object
        """Adds cat into the list of clan cats"""
        if cat.ID in Cat.all_cats and cat.ID not in self.clan_cats:
            self.clan_cats.append(cat.ID)

    def add_to_clan(self, cat):
        """
        TODO: DOCS
        """
        if (
            cat.ID in Cat.all_cats
            and cat.status.group.is_any_clan_group()
            and cat.ID in Cat.outside_cats
        ):
            Cat.outside_cats.pop(cat.ID)

    def remove_cat(self, ID):  # ID is cat.ID
        """
        This function is for completely removing the cat from the game,
        it's not meant for a cat that's simply dead
        """

        if Cat.all_cats[ID] in Cat.all_cats_list:
            Cat.all_cats_list.remove(Cat.all_cats[ID])

        if ID in Cat.all_cats:
            Cat.all_cats.pop(ID)

        if ID in self.clan_cats:
            self.clan_cats.remove(ID)

    def __repr__(self):
        if self.name is not None:
            _ = (
                f"{self.name}: led by {self.leader.name}"
                f"with {self.medicine_cat.name} as med. cat"
            )
            return _

        else:
            return "No Clan"

    def new_leader(self, leader):
        """
        TODO: DOCS
        """

        if leader:
            leader.generate_lead_ceremony()
            self.leader = leader
            Cat.all_cats[leader.ID].rank_change(CatRank.LEADER)
            self.leader_predecessors += 1
            # self.leader_lives = max(1, choice(constants.CONFIG["clan_creation"]["leader_lives_nr"]))

        # todo: this leads nowhere, can it be deleted?
        switch_set_value(Switch.new_leader, None)

    def new_deputy(self, deputy):
        """
        TODO: DOCS
        """
        if deputy:
            self.deputy = deputy
            Cat.all_cats[deputy.ID].rank_change(CatRank.DEPUTY)
            self.deputy_predecessors += 1

    def new_medicine_cat(self, medicine_cat):
        """
        TODO: DOCS
        """
        if medicine_cat:
            if medicine_cat.status.rank != CatRank.MEDICINE_CAT:
                Cat.all_cats[medicine_cat.ID].rank_change(CatRank.MEDICINE_CAT)
            if medicine_cat.ID not in self.med_cat_list:
                self.med_cat_list.append(medicine_cat.ID)
            medicine_cat = self.med_cat_list[0]
            self.medicine_cat = Cat.all_cats[medicine_cat]
            self.med_cat_number = len(self.med_cat_list)

    def remove_med_cat(self, medicine_cat):
        """
        Removes a med cat. Use when retiring, or switching to warrior
        """
        if medicine_cat:
            if medicine_cat.ID in game.clan.med_cat_list:
                game.clan.med_cat_list.remove(medicine_cat.ID)
                game.clan.med_cat_number = len(game.clan.med_cat_list)
            if self.medicine_cat:
                if medicine_cat.ID == self.medicine_cat.ID:
                    if game.clan.med_cat_list:
                        game.clan.medicine_cat = Cat.fetch_cat(
                            game.clan.med_cat_list[0]
                        )
                        game.clan.med_cat_number = len(game.clan.med_cat_list)
                    else:
                        game.clan.medicine_cat = None

    @staticmethod
    def switch_clans(clan, save=True):
        """
        TODO: DOCS
        """
        if save:
            save_clanlist(clan, True)
        else:
            save_clanlist(clan)
        switch_set_value(Switch.switch_clan, True)

    def save_clan(self):
        """
        TODO: DOCS
        """

        clan_data = {
            "clancount_mode": self.clancount,
            "clanname": self.name,
            "displayname": self.displayname,
            "clanage": self.age,
            "biome": self.biome,

            "camp_bg": self.camp_bg,
            "rogue_group_bg": self.rogue_group_bg,
            "loner_group_bg": self.loner_group_bg,
            "household_bg": self.household_bg,
            "no_group_bg": self.no_group_bg,

            "clan_symbol": self.chosen_symbol,
            "gamemode": self.game_mode,
            "cruel_cards": self.cruel_cards,
            "used_group_IDs": game.used_group_IDs,
            "last_focus_change": self.last_focus_change,
            "clans_in_focus": self.clans_in_focus,
            "instructor": self.instructor.ID,
            "demon": self.demon.ID,
            "reputation": self.reputation,
            "following_starclan": self.followingsc, 
            "mediated": game.mediated,
            "told_story": game.told_story,
            "starting_season": self.starting_season,
            "temperament": self.temperament,
            "relations": self.relations,
            "just_died": game.just_died,
            "dead_cats_to_grieve": [x.ID for x in game.dead_cats_to_grieve if x],
            "grief_to_assign": game.clan.grief_strings,
            "version_name": SAVE_VERSION_NUMBER,
            "version_commit": get_version_info().version_number,
            "source_build": get_version_info().is_source_build,
            "murdered": self.murdered,
            "exile_return": self.exile_return,
            "affair": self.affair,
            "custom_pronouns": self.custom_pronouns,
            "clan_age": self.clan_age
        }

        # LEADER DATA
        if self.leader:
            clan_data["leader"] = self.leader.ID
            clan_data["leader_lives"] = self.leader_lives
        else:
            clan_data["leader"] = None

        clan_data["leader_predecessors"] = self.leader_predecessors

        # DEPUTY DATA
        if self.deputy:
            clan_data["deputy"] = self.deputy.ID
        else:
            clan_data["deputy"] = None

        clan_data["deputy_predecessors"] = self.deputy_predecessors

        # MED CAT DATA
        if self.medicine_cat:
            clan_data["med_cat"] = self.medicine_cat.ID
        else:
            clan_data["med_cat"] = None
        clan_data["med_cat_number"] = self.med_cat_number
        clan_data["med_cat_predecessors"] = self.med_cat_predecessors

        # LIST OF CLAN CATS
        clan_data["clan_cats"] = ",".join([str(i) for i in self.clan_cats])

        clan_data["faded_cats"] = ",".join([str(i) for i in get_faded_ids()])

        # Patrolled cats
        clan_data["patrolled_cats"] = [str(i) for i in game.patrolled]

        # OTHER CLANS
        clan_data["other_clans"] = [i.get_save_data() for i in self.all_other_clans]

        clan_data["war"] = self.war
        clan_data['achievements'] = self.achievements
        clan_data['talks'] = self.talks
        clan_data["disaster"] = self.disaster
        clan_data["disaster_moon"] = self.disaster_moon
        clan_data["focus"] = self.focus
        clan_data["focus_moons"] = self.focus_moons

        # YOUR CAT DATA
        if self.your_cat:
            clan_data["your_cat"] = self.your_cat.ID
        else:
            alive_clan_cats = [x for x in Cat.all_cats_list if x.status.alive_in_player_clan]
            clan_data["your_cat"] = choice(alive_clan_cats).ID if alive_clan_cats else None

        if self.focus_cat:
            clan_data["focus_cat"] = self.focus_cat.ID
        else:
            clan_data["focus_cat"] = None

        # if "other_med" in game.switches:
        #     other_med = []
        #     for other_clan in game.switches["other_med"]:
        #         cats = []
        #         for c in other_clan:
        #             cats.append(c.prefix + "," + c.suffix + ",medicine cat")
        #         other_med.append(cats)
        #     clan_data["other_med"] = other_med

        self.save_herb_supply(game.clan)
        self.save_disaster(game.clan)
        self.save_future_events(game.clan)
        self.save_pregnancy(game.clan)

        save_clan_settings()
        if game.clan.game_mode in ("expanded", "cruel season"):
            self.save_freshkill_pile(game.clan)

        safe_save(f"{get_save_dir()}/{self.name}clan.json", clan_data)

        if os.path.exists(get_save_dir() + f"/{self.name}clan.txt") & (
            self.name != "current"
        ):
            os.remove(get_save_dir() + f"/{self.name}clan.txt")

    def load_clan(self):
        """
        TODO: DOCS
        """

        version_info = None
        game.reset_used_group_IDs()
        if os.path.exists(
            get_save_dir() + "/" + switch_get_value(Switch.clan_list)[0] + "clan.json"
        ):
            version_info = self.load_clan_json()
        else:
            switch_set_value(
                Switch.error_message, "There was an error loading the clan.json"
            )

        # can't put this in post initialization bc guide isn't made before that func
        self.add_guide_influence()
        load_clan_settings()
        

        return version_info

    @staticmethod
    def add_guide_influence():
        """
        Adds guide's facet influences to their current afterlife
        """
        if game.clan.instructor.status.group == CatGroup.STARCLAN:
            game.starclan.adjust_facets_by_cat(game.clan.instructor)
        elif game.clan.instructor.status.group == CatGroup.DARK_FOREST:
            game.dark_forest.adjust_facets_by_cat(game.clan.instructor)

        if game.clan.clancount == "multiclan":
            for clan in game.clan.all_other_clans:
                if clan.instructor.status.group == CatGroup.STARCLAN:
                    game.starclan.adjust_facets_by_cat(clan.instructor)
                elif clan.instructor.status.group == CatGroup.DARK_FOREST:
                    game.dark_forest.adjust_facets_by_cat(clan.instructor)

    def load_clan_json(self):
        """
        TODO: DOCS
        """
        if not switch_get_value(Switch.clan_list):
            number_other_clans = randint(3, 5)
            for _ in range(number_other_clans):
                OtherClan()
            return
        elif switch_get_value(Switch.clan_list)[0].strip() == "":
            number_other_clans = randint(3, 5)
            for _ in range(number_other_clans):
                OtherClan()
            return

        switch_set_value(
            Switch.error_message, "There was an error loading the clan.json"
        )
        with open(
            get_save_dir() + "/" + switch_get_value(Switch.clan_list)[0] + "clan.json",
            "r",
            encoding="utf-8",
        ) as read_file:  # pylint: disable=redefined-outer-name
            clan_data = ujson.loads(read_file.read())

        # LG
        your_cat = None
        if clan_data.get("your_cat"):
            your_cat = Cat.all_cats.get(clan_data["your_cat"])
        if your_cat is None:
            print("You don't have a cat! Choosing one for you...")
            candidates = [x for x in Cat.all_cats_list if x.status.alive_in_your_cat_group]
            if candidates:
                your_cat = choice(candidates)
                print(f"Hello, {your_cat.name}!")
            else:
                print("No eligible cat found to assign as your_cat.")

        # a leader, deputy or medicine cat who isn't in the save anymore leaves the role empty,
        # instead of the whole Clan failing to load
        for role in ("leader", "deputy", "med_cat"):
            if clan_data[role] and clan_data[role] not in Cat.all_cats:
                print(f"WARNING: {role} {clan_data[role]} isn't in the save, leaving the role empty")
                clan_data[role] = None

        if clan_data["leader"]:
            leader = Cat.all_cats[clan_data["leader"]]
            leader_lives = clan_data["leader_lives"]
        else:
            leader = None
            leader_lives = 0

        if clan_data["deputy"]:
            deputy = Cat.all_cats[clan_data["deputy"]]
        else:
            deputy = None

        if clan_data["med_cat"]:
            med_cat = Cat.all_cats[clan_data["med_cat"]]
        else:
            med_cat = None

        if "displayname" in clan_data:
            displayname = clan_data["displayname"]
        else:
            displayname = clan_data["clanname"]

        game.clan = Clan(
            name=clan_data["clanname"],
            displayname=displayname,
            leader=leader,
            deputy=deputy,
            your_cat=your_cat,
            medicine_cat=med_cat,
            biome=clan_data["biome"],
            camp_bg=clan_data["camp_bg"],
            rogue_group_bg=clan_data["rogue_group_bg"] if "rogue_group_bg" in clan_data else "camp1",
            loner_group_bg=clan_data["loner_group_bg"] if "loner_group_bg" in clan_data else "camp1",
            household_bg=clan_data["household_bg"] if "household_bg" in clan_data else "camp1",
            no_group_bg=clan_data["no_group_bg"] if "no_group_bg" in clan_data else "camp1",
            game_mode=clan_data["gamemode"],
            cruel_cards=clan_data.get("cruel_cards", []),
            relations=clan_data.get("relations", {CatGroup.PLAYER_CLAN_ID:{}}),
            self_run_init_functions=False,
        )
        game.clan.post_initialization_functions()
        names.load_clan_names(clan_data["clanname"])

        # LG
        if "following_starclan" in clan_data:
            game.clan.followingsc = clan_data['following_starclan']
        else:
            game.clan.followingsc = True
        # ---
        
        # LG: loading used IDs used to be here, but its moved below other_clans loading now

        game.clan.reputation = max(0, min(100, int(clan_data["reputation"])))

        game.clan.clancount = clan_data.get("clancount_mode", "singleclan")
        game.clan.age = clan_data["clanage"]
        game.clan.starting_season = (
            clan_data["starting_season"]
            if "starting_season" in clan_data
            else "Newleaf"
        )
        game.clan.leader_lives = leader_lives
        game.clan.leader_predecessors = clan_data["leader_predecessors"]

        game.clan.deputy_predecessors = clan_data["deputy_predecessors"]
        game.clan.med_cat_predecessors = clan_data["med_cat_predecessors"]
        game.clan.med_cat_number = clan_data["med_cat_number"]
        # Allows for the custom pronouns to show up in the add pronoun list after the game has closed and reopened.
        if "custom_pronouns" in clan_data.keys():
            if clan_data["custom_pronouns"]:
                if isinstance(clan_data["custom_pronouns"], list):
                    # english-only pronouns from an old version
                    game.clan.custom_pronouns["en"] = clan_data["custom_pronouns"]
                else:
                    game.clan.custom_pronouns = clan_data["custom_pronouns"]

        # Instructor Info
        if clan_data["instructor"] in Cat.all_cats:
            game.clan.instructor = Cat.all_cats[clan_data["instructor"]]
            if not game.clan.instructor.status.get_last_living_group():
                game.clan.instructor.status.group_history.insert(0, {"rank": game.clan.instructor.status.rank, "group": CatGroup.PLAYER_CLAN_ID, "moons_as": game.clan.instructor.moons})
            elif game.clan.instructor.status.get_last_living_group() != CatGroup.PLAYER_CLAN_ID:
                game.clan.instructor.status.group_history[0]["group"] = CatGroup.PLAYER_CLAN_ID
            game.clan.add_cat(game.clan.instructor)
        else:
            game.clan.instructor = Cat(
                status_dict={
                    "rank": choice((CatRank.WARRIOR, CatRank.WARRIOR, CatRank.ELDER)),
                    "group_ID": CatGroup.STARCLAN_ID,
                },
                backstory=choice(
                    BACKSTORIES["backstory_categories"]["clan_guide_backstories"]
                ),
            )
            game.clan.instructor.status.group_history.insert(0, {"rank": game.clan.instructor.status.rank, "group": CatGroup.PLAYER_CLAN_ID, "moons_as": self.instructor.moons})
            # update_sprite(game.clan.instructor)
            game.clan.add_cat(game.clan.instructor)
            
        # demon Info
        if "demon" in clan_data and clan_data["demon"] in Cat.all_cats:
            game.clan.demon = Cat.all_cats[clan_data["demon"]]
            game.clan.add_cat(game.clan.demon)
            game.clan.demon.df = True
        else:
            game.clan.demon = Cat(
                status_dict={
                    "rank": choice((CatRank.WARRIOR, CatRank.WARRIOR, CatRank.ELDER)),
                    "group_ID": CatGroup.DARK_FOREST_ID,
                }
            )
            game.clan.demon.dead = True
            game.clan.add_cat(game.clan.demon)
            game.clan.demon.df = True
   
        ##Commented this out because I don't know why it's in here twice. If lead/dep/med stuff starts sobbing... ye ##
        # game.clan.leader_lives = leader_lives
        # game.clan.leader_predecessors = clan_data["leader_predecessors"]

        # game.clan.deputy_predecessors = clan_data["deputy_predecessors"]
        # game.clan.med_cat_predecessors = clan_data["med_cat_predecessors"]
        # game.clan.med_cat_number = clan_data["med_cat_number"]

        # check for symbol
        if "clan_symbol" in clan_data:
            game.clan.chosen_symbol = clan_data["clan_symbol"]
        else:
            game.clan.chosen_symbol = clan_symbol_sprite(game.clan, return_string=True)

        if "other_clans" in clan_data:
            for other_clan in clan_data["other_clans"]:
                if not other_clan.get("group_ID"):
                    ID = game.get_free_group_ID(CatGroup.OTHER_CLAN)
                else:
                    ID = other_clan["group_ID"]
                OtherClan(
                    other_clan["name"],
                    temperament=other_clan["temperament"],
                    reputation=other_clan.get("reputation"),
                    chosen_symbol=other_clan["chosen_symbol"],
                    biome=other_clan.get("biome"),
                    camp_bg=other_clan.get("camp_bg"),
                    instructor=other_clan.get("instructor"),
                    leader=other_clan.get("leader"),
                    leader_lives=other_clan.get("leader_lives"),
                    leader_predecessors=other_clan.get("leader_predecessors", 0),
                    deputy=other_clan.get("deputy"),
                    deputy_predecessors=other_clan.get("deputy_predecessors", 0),
                    medicine_cat=other_clan.get("medicine_cat"),
                    med_cat_predecessors=other_clan.get("med_cat_predecessors", 0),
                    ID=ID,
                )
                if "relations" in other_clan:
                    game.clan.relations[CatGroup.PLAYER_CLAN_ID][ID] = int(other_clan["relations"])
                else:
                    if not clan_data["relations"].get(CatGroup.PLAYER_CLAN_ID):
                        game.clan.relations[CatGroup.PLAYER_CLAN_ID][ID] = clan_data["relations"]["player_clan"]["other_clan"+str(len(game.clan.all_other_clans))]
        else:
            ID = game.get_free_group_ID(CatGroup.OTHER_CLAN)
            if "other_clan_chosen_symbol" not in clan_data:
                for name, relation, temper in zip(
                    clan_data["other_clans_names"].split(","),
                    clan_data["other_clans_relations"].split(","),
                    clan_data["other_clan_temperament"].split(","),
                ):
                    OtherClan(name, temperament=temper, ID=ID)
                    game.clan.relations[CatGroup.PLAYER_CLAN_ID][ID] = int(relation)
            else:
                for name, relation, temper, symbol in zip(
                    clan_data["other_clans_names"].split(","),
                    clan_data["other_clans_relations"].split(","),
                    clan_data["other_clan_temperament"].split(","),
                    clan_data["other_clan_chosen_symbol"].split(","),
                ):
                    OtherClan(name, temperament=temper, chosen_symbol=symbol, ID=ID)
                    game.clan.relations[CatGroup.PLAYER_CLAN_ID][ID] = int(relation)
        if game.clan.clancount == "multiclan":
            if "relations" not in clan_data or not clan_data["relations"].get(game.clan.group_ID) or len(clan_data["relations"]) < len(game.clan.all_other_clans):
                for i, clan in enumerate(game.clan.all_other_clans[:-1]):
                    game.clan.relations[clan.group_ID] = {}
                    for j, o_clan in enumerate(game.clan.all_other_clans[i+1:]):
                        if "relations" in clan_data:
                            if rel := clan_data["relations"].get("other_clan" + (str(i+1)), {}).get("other_clan" + (str(j+1))):
                                game.clan.relations[clan.group_ID][o_clan.group_ID] = rel
                                continue
                        game.clan.relations[clan.group_ID][o_clan.group_ID] = randint(8, 12)
        
        # LG
        # MOVED HERE
        # old ID -> new ID for other clans that get moved below, so wars and relations can follow them
        group_id_remap = {}
        if clan_data.get("used_group_IDs"):
            game.used_group_IDs = clan_data["used_group_IDs"]

            # LG
            # correct for new lifegen groups
            if game.used_group_IDs.get('5') != CatGroup.ROGUE_GROUP:
                game.used_group_IDs['5'] = CatGroup.ROGUE_GROUP
            if game.used_group_IDs.get('6') != CatGroup.LONER_GROUP:
                game.used_group_IDs['6'] = CatGroup.LONER_GROUP
            if game.used_group_IDs.get('7') != CatGroup.HOUSEHOLD:
                game.used_group_IDs['7'] = CatGroup.HOUSEHOLD

            # fix clan IDs. so otherclans with 5, 6, or 7 as their id will move down the list
            # to make room for the above ones ^^
            count = 0
            for other_clan in game.clan.all_other_clans:
                count += 1
                if (
                    other_clan.group_ID in game.used_group_IDs and
                    game.used_group_IDs[other_clan.group_ID] != other_clan
                    ):
                    # generate the new ID. adds to the last number in the existing list (7)
                    new_group_id = 7 + count
                    if other_clan.group_ID != str(new_group_id):
                        group_id_remap[other_clan.group_ID] = str(new_group_id)
                    other_clan.group_ID = str(new_group_id)
                    
                    # now add to game used IDs
                    game.used_group_IDs.update({str(new_group_id): CatGroup.OTHER_CLAN})

            self.convert_group_IDs(group_id_remap)
            # ---

            for ID in game.used_group_IDs:
                game.used_group_IDs[ID] = CatGroup(game.used_group_IDs[ID])
        # ---

        # your cat always belongs on the roster. A new life that was left early could leave them off it,
        # and then the main menu cleared them out of the game
        if game.clan.your_cat and game.clan.your_cat.ID not in clan_data["clan_cats"].split(","):
            game.clan.add_cat(game.clan.your_cat)

        # LG: the Moonplace used to make healers for the other Clans without putting them on the roster, so the
        # main menu deleted them again and their mates were left pointing at nobody. Living cats of the other
        # Clans always belong on it
        for other in Cat.all_cats_list:
            if other.status.is_other_clancat and not other.dead and other.ID not in clan_data["clan_cats"].split(","):
                game.clan.add_cat(other)

        for cat in clan_data["clan_cats"].split(","):
            if cat in Cat.all_cats:
                game.clan.add_cat(Cat.all_cats[cat])
                if hasattr(Cat.all_cats[cat], "group"):
                    if Cat.all_cats[cat].group == game.clan.displayname:
                        pass
                    else:
                        is_neighbour = next(
                            filter(lambda c: c.displayname == Cat.all_cats[cat].group, game.clan.all_other_clans), None)
                        if is_neighbour:
                            Cat.all_cats[cat].status.group_history[0]["group"] = is_neighbour.group_ID
                            Cat.all_cats[cat].status.standing_history[0]["group"] = is_neighbour.group_ID

            else:
                print("WARNING: Cat not found:", cat)

        if "war" in clan_data:
            if clan_data["war"].get("at_war") is not None:
                for c in game.clan.all_other_clans:
                    if c.displayname == clan_data["war"]["enemy"]:
                        game.clan.war[CatGroup.PLAYER_CLAN_ID][c.group_ID] = {"at_war": True, "duration": clan_data["war"]["duration"]}
                    else:
                        game.clan.war[CatGroup.PLAYER_CLAN_ID][c.group_ID] = {"at_war": False, "duration": 0}
                if game.clan.clancount == "multiclan":
                    for i, clan in enumerate(game.clan.all_other_clans[:-1]):
                        game.clan.war[clan.group_ID] = {}
                        for o_clan in game.clan.all_other_clans[i+1:]:
                            game.clan.war[clan.group_ID][o_clan.group_ID] = {"at_war": False, "duration": 0}
            else:
                if clan_data["war"].get(CatGroup.PLAYER_CLAN_ID):
                    game.clan.war = self.remap_group_keys(clan_data["war"], group_id_remap)
                else:
                    for key in clan_data["war"]:
                        clan_id = key
                        if len(key) > 2:
                            clan_id = CatGroup.PLAYER_CLAN_ID if key == "player_clan" else game.clan.all_other_clans[int(key[-1])-1].group_ID
                        game.clan.war[clan_id] = {}
                        for other_key in clan_data["war"][key]:
                            other_clan_id = other_key
                            if len(other_key) > 2:
                                other_clan_id = game.clan.all_other_clans[int(other_key[-1])-1].group_ID
                            game.clan.war[clan_id][other_clan_id] = clan_data["war"][key][other_key]
                

        game.clan.relations = self.remap_group_keys(game.clan.relations, group_id_remap)

        load_faded_cat_ids(clan_data["clanname"])

        game.clan.last_focus_change = clan_data.get("last_focus_change")
        game.clan.clans_in_focus = clan_data.get("clans_in_focus", [])

        # Patrolled cats
        if "patrolled_cats" in clan_data:
            game.patrolled = clan_data["patrolled_cats"]
        
        if "dated_cats" in clan_data:
            game.dated_cats = clan_data["dated_cats"]

        # Mediated flag
        if "mediated" in clan_data:
            if not isinstance(clan_data["mediated"], list):
                game.mediated = []
            else:
                game.mediated = clan_data["mediated"]
        # LG: story flag
        if "told_story" in clan_data:
            if not isinstance(clan_data["told_story"], list):
                game.told_story = []
            else:
                game.told_story = clan_data["told_story"]

        game.clan.clan_age = clan_data["clan_age"] if "clan_age" in clan_data else "established"

        game.just_died.clear()
        # Cat who had just died
        if "just_died" in clan_data:
            game.just_died = clan_data["just_died"]

        game.dead_cats_to_grieve.clear()
        # Cats who need to be grieved
        if "dead_cats_to_grieve" in clan_data:
            game.dead_cats_to_grieve = [
                Cat.fetch_cat(x) for x in clan_data["dead_cats_to_grieve"] if Cat.fetch_cat(x)
            ]

        # Cats who are gonna grieve
        if "grief_to_assign" in clan_data:
            game.clan.grief_strings = clan_data["grief_to_assign"]

        self.load_pregnancy(game.clan)
        self.load_herb_supply(game.clan)
        self.load_future_events(game.clan)
        self.load_disaster(game.clan)
        self.load_accessories()
        if game.clan.game_mode != "classic":
            self.load_freshkill_pile(game.clan)

        if "murdered" in clan_data:
            if isinstance(clan_data["murdered"], bool):
                game.clan.murdered = {}
            else:
                game.clan.murdered = clan_data["murdered"]

        if "affair" in clan_data:
            game.clan.affair = clan_data["affair"]

        if "exile_return" in clan_data:
            game.clan.exile_return = clan_data["exile_return"]

        if "achievements" in clan_data:
            achievement_list = []
            for item in clan_data["achievements"]:
                if not isinstance(item, list):
                    achievement_list.append([item, game.clan.your_cat.ID]
                    )
                else:
                    achievement_list.append(item)

            game.clan.achievements = achievement_list
        
        if "talks" in clan_data:
            game.clan.talks = clan_data["talks"]

        if "disaster" in clan_data:
            game.clan.disaster = clan_data["disaster"]
        
        if "disaster_moon" in clan_data:
            game.clan.disaster_moon = clan_data["disaster_moon"]

        if "focus" in clan_data:
            game.clan.focus = clan_data["focus"]

        if "focus_moons" in clan_data:
            game.clan.focus_moons = clan_data["focus_moons"]

        if "focus_cat" in clan_data:
            if clan_data["focus_cat"] is None:
                game.clan.focus_cat = None
            else:
                game.clan.focus_cat = Cat.all_cats[clan_data["focus_cat"]]
        
        switch_set_value(Switch.error_message, "")

        # Return Version Info.
        return {
            "version_name": clan_data.get("version_name"),
            "version_commit": clan_data.get("version_commit"),
            "source_build": clan_data.get("source_build"),
        }
    
    @staticmethod
    def remap_group_keys(table: dict, remap: dict) -> dict:
        """war and relations are {clan ID: {other clan ID: ...}}, this moves both levels to the new IDs"""
        if not remap:
            return table
        return {
            remap.get(key, key): (
                {remap.get(k, k): v for k, v in value.items()} if isinstance(value, dict) else value
            )
            for key, value in table.items()
        }

    def convert_group_IDs(self, remap: dict = None):
        """
        LIFEGEN FUNCTION
        existing otherclan cats will now get a new group ID
        so otherclan cats from old saves dont randomly join rogue groups and stuff
        """
        if remap:
            # the other clans were moved to new IDs, move their cats along with them
            for cat in Cat.all_cats_list:
                if not cat.status.rank.is_any_clancat_rank():
                    continue
                for group in cat.status.standing_history:
                    if group.get("group") in remap:
                        group["group"] = remap[group["group"]]
                for group in cat.status.group_history:
                    if group.get("group") in remap:
                        group["group"] = remap[group["group"]]
            return

        for cat in Cat.all_cats_list:
            for group_ID in ["5", "6", "7"]:
                if cat.status.rank.is_any_clancat_rank():
                    for group in cat.status.standing_history.copy():
                        if group['group'] == group_ID:
                            index = cat.status.standing_history.index(group)
                            cat.status.standing_history.remove(group)

                            new_standing_block = {
                                "group": "8",
                                "standing": group["standing"],
                                "near": group["near"]
                            }
                            cat.status.standing_history.insert(index, new_standing_block)
                    for group in cat.status.group_history.copy():
                        if group['group'] == group_ID:
                            index = cat.status.group_history.index(group)
                            cat.status.group_history.remove(group)

                            new_group_block = {
                                "group": "8",
                                "rank": group["rank"],
                                "moons_as": group["moons_as"]
                            }
                            cat.status.group_history.insert(index, new_group_block)
    
    def load_accessories(self):
        """
        loads all accessories for cat inventories
        when all accessories is toggled on
        """
        if get_clan_setting('all accessories'):
            for cat in Cat.all_cats_list:
                if game_setting_get("lifegen_sprite_changes"):
                    acc_list = Pelt.all_lifegen_accessories
                else:
                    acc_list = Pelt.all_clangen_accessories
                
                if "NOTAIL" in cat.pelt.scars or "HALFTAIL" in cat.pelt.scars:
                    for acc in Pelt.tail_accessories:
                        if acc in acc_list:
                            try:
                                acc_list.remove(acc)
                            except ValueError:
                                print(f'attempted to remove {acc} from possible acc list, but it was not in the list!')
                # LG
                if "NOPAW" in cat.pelt.scars:
                    for acc in Pelt.paw_accessories:
                        if acc in acc_list:
                            try:
                                acc_list.remove(acc)
                            except ValueError:
                                print(f'attempted to remove {acc} from possible acc list, but it was not in the list!')
                return acc_list

    def load_pregnancy(self, clan):
        """
        Load the information about what cat is pregnant and in what 'state' they are in the pregnancy.
        """
        if not game.clan.name:
            return
        file_path = get_save_dir() + f"/{game.clan.name}/pregnancy.json"
        if os.path.exists(file_path):
            with open(
                file_path, "r", encoding="utf-8"
            ) as read_file:  # pylint: disable=redefined-outer-name
                clan.pregnancy_data = ujson.load(read_file)
        else:
            clan.pregnancy_data = {}

    def save_pregnancy(self, clan):
        """
        Save the information about what cat is pregnant and in what 'state' they are in the pregnancy.
        """
        if not game.clan.name:
            return

        keys_to_delete = []
        for key in clan.pregnancy_data:
            if key not in Cat.all_cats:
                keys_to_delete.append(key)
        for key in keys_to_delete:
            del clan.pregnancy_data[key]

        safe_save(
            f"{get_save_dir()}/{game.clan.name}/pregnancy.json", clan.pregnancy_data
        )

    def load_disaster(self, clan):
        """
        TODO: DOCS
        """
        if not game.clan.name:
            return

        file_path = get_save_dir() + f"/{game.clan.name}/disasters/primary.json"
        try:
            if os.path.exists(file_path):
                with open(
                    file_path, "r", encoding="utf-8"
                ) as read_file:  # pylint: disable=redefined-outer-name
                    disaster = ujson.load(read_file)
                    if disaster:
                        clan.primary_disaster = OngoingEvent(
                            event=disaster["event"],
                            tags=disaster["tags"],
                            duration=disaster["duration"],
                            current_duration=(
                                disaster["current_duration"]
                                if "current_duration" in disaster
                                else disaster["duration"]
                            ),
                            trigger_events=disaster["trigger_events"],
                            progress_events=disaster["progress_events"],
                            conclusion_events=disaster["conclusion_events"],
                            secondary_disasters=disaster["secondary_disasters"],
                            collateral_damage=disaster["collateral_damage"],
                        )
                    else:
                        clan.primary_disaster = {}
            else:
                os.makedirs(get_save_dir() + f"/{game.clan.name}/disasters")
                clan.primary_disaster = None
                with open(file_path, "w", encoding="utf-8") as rel_file:
                    json_string = ujson.dumps(clan.primary_disaster, indent=4)
                    rel_file.write(json_string)
        except Exception:
            logger.exception("Failed to load primary disaster; clearing it.")
            clan.primary_disaster = None

        file_path = get_save_dir() + f"/{game.clan.name}/disasters/secondary.json"
        try:
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as read_file:
                    disaster = ujson.load(read_file)
                    if disaster:
                        clan.secondary_disaster = OngoingEvent(
                            event=disaster["event"],
                            tags=disaster["tags"],
                            duration=disaster["duration"],
                            current_duration=(
                                disaster["current_duration"]
                                if "current_duration" in disaster
                                else disaster["duration"]
                            ),
                            progress_events=disaster["progress_events"],
                            conclusion_events=disaster["conclusion_events"],
                            collateral_damage=disaster["collateral_damage"],
                        )
                    else:
                        clan.secondary_disaster = {}
            else:
                os.makedirs(get_save_dir() + f"/{game.clan.name}/disasters")
                clan.secondary_disaster = None
                with open(file_path, "w", encoding="utf-8") as rel_file:
                    json_string = ujson.dumps(clan.secondary_disaster, indent=4)
                    rel_file.write(json_string)

        except Exception:
            logger.exception("Failed to load secondary disaster; clearing it.")
            clan.secondary_disaster = None

    def save_disaster(self, clan=None):
        """
        TODO: DOCS
        """
        if clan is None:
            clan = game.clan
        if not clan.name:
            return
        file_path = get_save_dir() + f"/{clan.name}/disasters/primary.json"
        if not os.path.isdir(f"{get_save_dir()}/{clan.name}/disasters"):
            os.mkdir(f"{get_save_dir()}/{clan.name}/disasters")
        if clan.primary_disaster:
            disaster = {
                "event": clan.primary_disaster.event,
                "tags": clan.primary_disaster.tags,
                "duration": clan.primary_disaster.duration,
                "current_duration": clan.primary_disaster.current_duration,
                "trigger_events": clan.primary_disaster.trigger_events,
                "progress_events": clan.primary_disaster.progress_events,
                "conclusion_events": clan.primary_disaster.conclusion_events,
                "secondary_disasters": clan.primary_disaster.secondary_disasters,
                "collateral_damage": clan.primary_disaster.collateral_damage,
            }
        else:
            disaster = {}

        safe_save(f"{get_save_dir()}/{clan.name}/disasters/primary.json", disaster)

        if clan.secondary_disaster:
            disaster = {
                "event": clan.secondary_disaster.event,
                "tags": clan.secondary_disaster.tags,
                "duration": clan.secondary_disaster.duration,
                "current_duration": clan.secondary_disaster.current_duration,
                "trigger_events": clan.secondary_disaster.trigger_events,
                "progress_events": clan.secondary_disaster.progress_events,
                "conclusion_events": clan.secondary_disaster.conclusion_events,
                "secondary_disasters": clan.secondary_disaster.secondary_disasters,
                "collateral_damage": clan.secondary_disaster.collateral_damage,
            }
        else:
            disaster = {}

        safe_save(f"{get_save_dir()}/{clan.name}/disasters/secondary.json", disaster)

    def load_future_events(self, clan):
        """
        Loads the Clan's saved future events
        """
        if not clan.name:
            return

        # load the current file path, if it exists in save
        file_path = f"{get_save_dir()}/{game.clan.name}/future_events.json"
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as save_file:
                save_list = ujson.load(save_file)
                for event in save_list:
                    try:
                        event_obj = FutureEvent(
                                parent_event=event["parent_event"],
                                event_type=event["event_type"],
                                pool=event["pool"],
                                moon_delay=event["moon_delay"],
                                involved_cats=event["involved_cats"],
                                clan=event["clan"],
                            )
                        if not event_obj.clan or event_obj.clan in [game.clan.displayname, CatGroup.PLAYER_CLAN.value]:
                            event_obj.clan = CatGroup.PLAYER_CLAN_ID
                        elif len(event_obj.clan) > 2:
                            if match := [c for c in game.clan.all_other_clans if c.displayname == event_obj.clan]:
                                event_obj.clan = match[0].group_ID
                            else:
                                event_obj.clan = game.clan.all_other_clans[int(event_obj.clan[-1])-1].group_ID

                        game.clan.future_events.append(event_obj)
                    except KeyError:
                        print(
                            f"WARNING: A saved future event was missing information and was not loaded. event: {event}"
                        )
                        continue

    def save_future_events(self, clan):
        """
        saves the Clan's current future events
        """
        save_list = []

        for event in game.clan.future_events:
            if e := event.to_dict():
                save_list.append(e)

        safe_save(f"{get_save_dir()}/{game.clan.name}/future_events.json", save_list)

    def load_herb_supply(self, clan):
        """
        Loads the Clan's saved herb supply info
        """
        if not game.clan.name:
            return

        save_dir = get_save_dir()

        current_file_path = save_dir + f"/{game.clan.name}/herb_supply.json"
        old_file_path = save_dir + f"/{game.clan.name}/herbs.json"

        try:
            # load the old file path and convert the save data into current format
            if os.path.exists(old_file_path):
                with open(old_file_path, "r", encoding="utf-8") as save_file:
                    herbs = ujson.load(save_file)
                    clan.herb_supply = HerbSupply()
                    clan.herb_supply.convert_old_save(herbs)

            # load the current file path, if it exists in save
            elif os.path.exists(current_file_path):
                with open(current_file_path, "r", encoding="utf-8") as save_file:
                    herbs = ujson.load(save_file)
                    clan.herb_supply = HerbSupply(herb_supply=herbs)

            # else just start us with an empty herb supply
            else:
                clan.herb_supply = HerbSupply()

            clan.herb_supply.set_required_herb_count(get_living_clan_cat_count(Cat))
        except Exception:
            logger.exception("Failed to load herb supply; starting with an empty supply.")
            clan.herb_supply = HerbSupply()

    def save_herb_supply(self, clan):
        """
        saves the Clan's current herb supply
        """
        if not clan.herb_supply:
            return

        combined_supply_dict = clan.herb_supply.combined_supply_dict
        combined_supply_dict = {
            group_key: {
                "storage": {
                    herb: [int(i) for i in amounts]
                    for herb, amounts in group_data["storage"].items()
                },
                "collected": {
                    herb: int(amount)
                    for herb, amount in group_data["collected"].items()
                },
            }
            for group_key, group_data in combined_supply_dict.items()
        }

        safe_save(
            f"{get_save_dir()}/{game.clan.name}/herb_supply.json",
            combined_supply_dict,
        )

        # delete old herb save file if it exists
        if os.path.exists(get_save_dir() + f"/{game.clan.name}/herbs.json"):
            os.remove(get_save_dir() + f"/{game.clan.name}/herbs.json")

    def load_freshkill_pile(self, clan):
        """
        TODO: DOCS
        """
        if not game.clan.name or clan.game_mode == "classic":
            return

        file_path = get_save_dir() + f"/{game.clan.name}/freshkill_pile.json"
        try:
            if os.path.exists(file_path):
                with open(
                    file_path, "r", encoding="utf-8"
                ) as read_file:  # pylint: disable=redefined-outer-name
                    pile = ujson.load(read_file)
                    clan.freshkill_pile = FreshkillPile(pile)

                file_path = get_save_dir() + f"/{game.clan.name}/nutrition_info.json"
                if os.path.exists(file_path) and clan.freshkill_pile:
                    with open(file_path, "r", encoding="utf-8") as read_file:
                        nutritions = ujson.load(read_file)
                        for k, nutr in nutritions.items():
                            nutrition = Nutrition()
                            nutrition.max_score = nutr["max_score"]
                            nutrition.current_score = nutr["current_score"]
                            clan.freshkill_pile.nutrition_info[k] = nutrition
                        if len(nutritions) <= 0:
                            for cat in Cat.all_cats_list:
                                clan.freshkill_pile.add_cat_to_nutrition(cat)
            else:
                clan.freshkill_pile = FreshkillPile()
        except Exception:
            logger.exception("Failed to load freshkill pile; starting with an empty pile.")
            clan.freshkill_pile = FreshkillPile()

    def save_freshkill_pile(self, clan):
        """
        TODO: DOCS
        """
        if clan.game_mode == "classic" or not clan.freshkill_pile:
            return

        safe_save(
            f"{get_save_dir()}/{game.clan.name}/freshkill_pile.json",
            clan.freshkill_pile.pile,
        )

        data = {}
        for k, nutr in clan.freshkill_pile.nutrition_info.items():
            data[k] = {
                "max_score": nutr.max_score,
                "current_score": nutr.current_score,
                "percentage": nutr.percentage
            }

        safe_save(f"{get_save_dir()}/{game.clan.name}/nutrition_info.json", data)

    ## Properties

    @property
    def reputation(self):
        return self._reputation

    @reputation.setter
    def reputation(self, a: int):
        self._reputation = int(a)
        if self._reputation > 100:
            self._reputation = 100
        elif self._reputation < 0:
            self._reputation = 0

    @property
    def temperament(self) -> tuple[str, str]:
        """Temperament is determined whenever it's accessed. This makes sure it's always accurate to the
        current cats in the Clan. However, determining Clan temperament is slow!
        Clan temperament should be used as sparsely as possible, since
        it's pretty resource-intensive to determine it."""

        leader = (
            Cat.fetch_cat(self.leader)
            if isinstance(Cat.fetch_cat(self.leader), Cat)
            else None
        )
        deputy = (
            Cat.fetch_cat(self.deputy)
            if isinstance(Cat.fetch_cat(self.deputy), Cat)
            else None
        )
        medicine_cats = find_alive_cats_with_rank(Cat, [CatRank.MEDICINE_CAT])

        all_other_cats = [
            i
            for i in Cat.all_cats_list
            if i.status.rank
            not in (CatRank.LEADER, CatRank.DEPUTY, CatRank.MEDICINE_CAT)
            and i.status.alive_in_player_clan
        ]

        sociability_list = []
        aggression_list = []
        lawfulness_list = []
        stability_list = []

        # 3x influence
        if leader:
            sociability_list += [leader.personality.sociability] * 3
            aggression_list += [leader.personality.aggression] * 3
            lawfulness_list += [leader.personality.lawfulness] * 3
            stability_list += [leader.personality.stability] * 3

        # 2x influence
        if deputy:
            sociability_list += [deputy.personality.sociability] * 2
            aggression_list += [deputy.personality.aggression] * 2
            lawfulness_list += [deputy.personality.lawfulness] * 2
            stability_list += [deputy.personality.stability] * 2

        # collective influence
        if medicine_cats:
            sociability_list.append(
                statistics.median([i.personality.sociability for i in medicine_cats])
            )
            aggression_list.append(
                statistics.median([i.personality.aggression for i in medicine_cats])
            )
            lawfulness_list.append(
                statistics.median([i.personality.lawfulness for i in medicine_cats])
            )
            stability_list.append(
                statistics.median([i.personality.stability for i in medicine_cats])
            )

        # collective influence
        if all_other_cats:
            sociability_list.append(
                statistics.median([i.personality.sociability for i in all_other_cats])
            )
            aggression_list.append(
                statistics.median([i.personality.aggression for i in all_other_cats])
            )
            lawfulness_list.append(
                statistics.median([i.personality.lawfulness for i in all_other_cats])
            )
            stability_list.append(
                statistics.median([i.personality.stability for i in all_other_cats])
            )

        # mean of [leader, leader, leader, deputy, deputy, medicine_cats, all_other_cats]
        clan_sociability = round(statistics.mean(sociability_list))
        clan_aggression = round(statistics.mean(aggression_list))
        clan_lawfulness = round(statistics.mean(lawfulness_list))
        clan_stability = round(statistics.mean(stability_list))

        if not leader and not deputy and not all_other_cats:
            print("returned default temper: stoic, observant")
            return "stoic", "observant"

        return get_temper_alignment(
            clan_sociability, clan_aggression, clan_lawfulness, clan_stability
        )

    @temperament.setter
    def temperament(self, val):
        return

    def group_ID_to_clan(self, group_ID):
        return next(filter(lambda c: c.group_ID == group_ID, game.clan.all_other_clans), game.clan)

    def get_relations(self, clan, other_clan, get_label=False):
        main_enum = clan.group_ID
        other_enum = other_clan.group_ID

        # a relation of 0 is still a relation, check the key is there instead of the value
        if main_enum in game.clan.relations.get(other_enum, {}):
            main_enum = other_clan.group_ID
            other_enum = clan.group_ID

        if get_label:
            if game.clan.relations[main_enum][other_enum] > 17:
                return "ally"
            elif 7 <= game.clan.relations[main_enum][other_enum] <= 17:
                return "neutral"
            return "hostile"
        
        return game.clan.relations[main_enum][other_enum]

    def set_relations(self, clan, other_clan, value = None, offset=0):
        main_enum = clan.group_ID
        other_enum = other_clan.group_ID

        # a relation of 0 is still a relation, check the key is there instead of the value
        if main_enum in game.clan.relations.get(other_enum, {}):
            main_enum = other_clan.group_ID
            other_enum = clan.group_ID

        if value is None:
            value = game.clan.relations[main_enum][other_enum]
        
        game.clan.relations[main_enum][other_enum] = int(value + offset)

    def get_wars(self, clan):
        enemies = []
        for key in game.clan.war:
            if key == clan:
                for o_key in game.clan.war[key]:
                    if game.clan.war[key][o_key]["at_war"]:
                        enemies.append(o_key)
            elif game.clan.war[key].get(clan, {"at_war": False})["at_war"]:
                enemies.append(key)
        return enemies

    def check_war(self, clan, other_clan):
        if match := game.clan.war.get(clan):
            return match[other_clan]["at_war"]
        return game.clan.war[other_clan][clan]["at_war"]



class OtherClan:
    """
    TODO: DOCS
    """

    interaction_dict = {
        "ally": ["offend", "praise"],
        "neutral": ["provoke", "befriend"],
        "hostile": ["antagonize", "appease", "declare"],
    }

    first_temper_list = []
    second_temper_list = []
    for _l in constants.TEMPERAMENT_DICTS[0].values():
        first_temper_list.extend(_l)
    for _l in constants.TEMPERAMENT_DICTS[1].values():
        second_temper_list.extend(_l)

    # Notes to self:
    # Friendly to joiners: gracious, amiable   
    # Neutral to joiners: cunning, logical, stoic, mellow, bloodthirsty
    # Hostile to joiners: wary, proud

    def __init__(
        self, 
        name: str = "",
        clancount="singleclan", 
        biome=None, 
        camp_bg=None, 
        reputation=None, 
        temperament: tuple[str, str] = None,
        chosen_symbol: str = "", 
        instructor=None, 
        leader=None, 
        leader_lives=9, 
        leader_predecessors=0, 
        deputy=None, 
        deputy_predecessors=0, 
        medicine_cat=None, 
        med_cat_predecessors=0, 
        ID: str = 0
    ):
        self.group_ID = ID
        if not self.group_ID:
            self.group_ID = game.get_free_group_ID(CatGroup.OTHER_CLAN)
        game.clan.other_clan_IDs.append(self.group_ID)

        clan_names = names.names_dict["normal_prefixes"]
        clan_names.extend(names.names_dict["clan_prefixes"])
        self.displayname = name or choice(clan_names)
        if biome:
            self.biome = biome
        else:
            self.biome = game.clan.biome if random() < 0.75 else choice(constants.BIOME_TYPES)
            while self.biome in ["Wetlands", "Desert", None]:
                self.biome = choice(constants.BIOME_TYPES)
        if camp_bg:
            self.camp_bg = camp_bg
        else:
            self.camp_bg = f"camp{randint(1, 4)}"

        self.temperament: tuple[str, str]

        # detect old saves and convert
        if isinstance(temperament, str):
            used_tempers = []
            for clan in game.clan.all_other_clans:
                used_tempers.extend(clan.temperament)

            self.temperament = (
                temperament,
                choice([x for x in self.second_temper_list if x not in used_tempers]),
            )
        # assign if a saved temper exists
        elif temperament:
            self.temperament = temperament
        # find temperament
        else:
            used_tempers = []
            for clan in game.clan.all_other_clans:
                used_tempers.extend(clan.temperament)

            self.temperament = (
                choice([x for x in self.first_temper_list if x not in used_tempers]),
                choice([x for x in self.second_temper_list if x not in used_tempers]),
            )
        # self.relations = relations or randint(8, 12)
        if reputation is None:
            if self.temperament[0] in ["gracious", "amiable"]:
                self.reputation = choice([randint(71, 100), randint(71, 100), randint(71, 100), randint(50, 70)])
            elif self.temperament[0] in ["wary", "proud"]:
                self.reputation = choice([randint(1, 30), randint(1, 30), randint(1, 30), randint(31, 50)])
            else:
                self.reputation = choice([randint(1, 30), randint(31, 70), randint(31, 70), randint(71, 100)])
        else:
            self.reputation = reputation

        self.chosen_symbol = (
            None  # have to establish None first so that clan_symbol_sprite works
        )
        self.chosen_symbol = (
            chosen_symbol
            if chosen_symbol
            else clan_symbol_sprite(self, return_string=True)
        )

        self.instructor = Cat.all_cats.get(instructor)
        self.leader = Cat.all_cats.get(leader)
        self.leader_lives = leader_lives if leader else 0
        self.leader_predecessors = leader_predecessors
        self.deputy = Cat.all_cats.get(deputy)
        self.deputy_predecessors = deputy_predecessors
        self.medicine_cat = Cat.all_cats.get(medicine_cat)
        self.med_cat_predecessors = med_cat_predecessors
        self.med_cat_list = []
        self.med_cat_number = len(self.med_cat_list)

        if self.leader and not self.instructor:
            instructor_rank = choice((
                CatRank.APPRENTICE,
                CatRank.MEDIATOR_APPRENTICE,
                CatRank.MEDICINE_APPRENTICE,
                CatRank.WARRIOR,
                CatRank.MEDICINE_CAT,
                CatRank.LEADER,
                CatRank.MEDIATOR,
                CatRank.DEPUTY,
                CatRank.ELDER,
            ))
            self.instructor = Cat(
                status_dict={
                    "rank": instructor_rank,
                    "group_ID": CatGroup.STARCLAN_ID,
                },
                backstory=choice(
                    BACKSTORIES["backstory_categories"]["clan_guide_backstories"]
                ),
            )
            self.instructor.dead_for = randint(20, 200)
            self.instructor.status.group_history.insert(0, {"rank": instructor_rank, "group": self.group_ID, "moons_as": self.instructor.moons})
            game.clan.add_cat(self.instructor)

        game.clan.all_other_clans.append(self)

        random_rank = [CatRank.WARRIOR, CatRank.WARRIOR, CatRank.ELDER, CatRank.APPRENTICE, CatRank.KITTEN]
        if clancount == "multiclan":
            instructor_rank = choice(
                (
                    CatRank.APPRENTICE,
                    CatRank.MEDIATOR_APPRENTICE,
                    CatRank.MEDICINE_APPRENTICE,
                    CatRank.WARRIOR,
                    CatRank.MEDICINE_CAT,
                    CatRank.LEADER,
                    CatRank.MEDIATOR,
                    CatRank.DEPUTY,
                    CatRank.ELDER,
                )
            )
            self.instructor = Cat(
                status_dict={"rank": instructor_rank, "group_ID": CatGroup.STARCLAN_ID},
                backstory=choice(
                BACKSTORIES["backstory_categories"]["clan_guide_backstories"]
                ),
            )
            self.instructor.dead_for = randint(20, 200)
            self.instructor.status.group_history.insert(0, {"rank": instructor_rank, "group": self.group_ID, "moons_as": self.instructor.moons})

            self.new_leader(create_cat(CatRank.LEADER, biome=self.biome, kittypet=constants.CONFIG["clan_creation"]["use_special_roller"], clan=self.group_ID))
            self.new_deputy(create_cat(CatRank.DEPUTY, biome=self.biome, kittypet=constants.CONFIG["clan_creation"]["use_special_roller"], clan=self.group_ID))
            self.new_medicine_cat(create_cat(CatRank.MEDICINE_CAT, biome=self.biome, kittypet=constants.CONFIG["clan_creation"]["use_special_roller"], clan=self.group_ID))
            for i in range(randint(constants.CONFIG["clan_creation"]["neighbourclan_cats"][0], constants.CONFIG["clan_creation"]["neighbourclan_cats"][1])):
                create_cat(choice(random_rank), biome=self.biome, kittypet = constants.CONFIG["clan_creation"]["use_special_roller"], clan=self.group_ID)

    def __repr__(self):
        return f"{self.displayname}Clan"
    
    def get_save_data(self):
        return {
            "group_ID": self.group_ID,
            "name": self.displayname,
            "reputation" : self.reputation,
            "temperament" : self.temperament,
            "chosen_symbol": self.chosen_symbol,
            "biome": self.biome,
            "camp_bg": self.camp_bg,
            "instructor": self.instructor.ID if self.instructor else None,
            "leader" : self.leader.ID if self.leader else None,
            "leader_lives" : self.leader_lives,
            "leader_predecessors" : self.leader_predecessors,
            "deputy" : self.deputy.ID if self.deputy else None,
            "deputy_predecessors": self.deputy_predecessors,
            "medicine_cat": self.medicine_cat.ID if self.medicine_cat else None,
            "med_cat_predecessors": self.med_cat_predecessors,
        }

    def new_leader(self, leader):
        """
        TODO: DOCS
        """

        if leader:
            leader.history.add_lead_ceremony()
            self.leader = leader
            Cat.all_cats[leader.ID].rank_change(CatRank.LEADER)
            self.leader_predecessors += 1
            # self.leader_lives = max(1, choice(constants.CONFIG["clan_creation"]["leader_lives_nr"]))
        switch_set_value(Switch.new_leader, None)

    def new_deputy(self, deputy):
        """
        TODO: DOCS
        """
        if deputy:
            self.deputy = deputy
            Cat.all_cats[deputy.ID].rank_change(CatRank.DEPUTY)
            self.deputy_predecessors += 1

    def new_medicine_cat(self, medicine_cat):
        """
        TODO: DOCS
        """
        if medicine_cat:
            if medicine_cat.status.rank != CatRank.MEDICINE_CAT:
                Cat.all_cats[medicine_cat.ID].rank_change(CatRank.MEDICINE_CAT)
            if medicine_cat.ID not in self.med_cat_list:
                self.med_cat_list.append(medicine_cat.ID)
            medicine_cat = self.med_cat_list[0]
            self.medicine_cat = Cat.all_cats[medicine_cat]
            self.med_cat_number = len(self.med_cat_list)

    def remove_med_cat(self, medicine_cat):
        """
        Removes a med cat. Use when retiring, or switching to warrior
        """
        if medicine_cat:
            if medicine_cat.ID in self.med_cat_list:
                self.med_cat_list.remove(medicine_cat.ID)
                self.med_cat_number = len(self.med_cat_list)
            if self.medicine_cat:
                if medicine_cat.ID == self.medicine_cat.ID:
                    if self.med_cat_list:
                        self.medicine_cat = Cat.fetch_cat(
                            self.med_cat_list[0]
                        )
                        self.med_cat_number = len(self.med_cat_list)
                    else:
                        self.medicine_cat = None

    # lifegen code reads .relations off the other clan, genemod keeps them all on the player clan
    @property
    def relations(self):
        return game.clan.relations[CatGroup.PLAYER_CLAN_ID].get(self.group_ID, 10)

    @relations.setter
    def relations(self, value):
        game.clan.relations[CatGroup.PLAYER_CLAN_ID][self.group_ID] = value

    # lifegen code still uses .name for other clans, genemod calls it displayname
    @property
    def name(self):
        return self.displayname

    @name.setter
    def name(self, value):
        self.displayname = value

    @property
    def reputation(self):
        return self._reputation

    @reputation.setter
    def reputation(self, a: int):
        self._reputation = int(a)
        if self._reputation > 100:
            self._reputation = 100
        elif self._reputation < 0:
            self._reputation = 0

class Afterlife:
    """
    Currently just used for tracking temperament & facets. All facets default to 8 if influencing_cats is empty.
    """

    def __init__(self):
        self.influencing_cats: set[str] = set()

        self._law: int = 0
        self._social: int = 0
        self._aggress: int = 0
        self._stable: int = 0

        self._total_aggression: int = 0
        self._total_lawfulness: int = 0
        self._total_sociability: int = 0
        self._total_stability: int = 0

    @property
    def aggression(self) -> int:
        if not self.influencing_cats:
            return 8
        else:
            return self._aggress

    @aggression.setter
    def aggression(self, value):
        raise Exception(
            "ERROR: Afterlife aggression cannot be set manually as it is meant to be calculated from the currently dead cats."
        )

    @property
    def sociability(self) -> int:
        if not self.influencing_cats:
            return 8
        else:
            return self._social

    @sociability.setter
    def sociability(self, value):
        raise Exception(
            "ERROR: Afterlife sociability cannot be set manually as it is meant to be calculated from the currently dead cats."
        )

    @property
    def lawfulness(self) -> int:
        if not self.influencing_cats:
            return 8
        else:
            return self._law

    @lawfulness.setter
    def lawfulness(self, value):
        raise Exception(
            "ERROR: Afterlife lawfulness cannot be set manually as it is meant to be calculated from the currently dead cats."
        )

    @property
    def stability(self) -> int:
        if not self.influencing_cats:
            return 8
        else:
            return self._stable

    @stability.setter
    def stability(self, value):
        raise Exception(
            "ERROR: Afterlife aggresstabilitysion cannot be set manually as it is meant to be calculated from the currently dead cats."
        )

    @property
    def temperament(self) -> (str, str):
        return get_temper_alignment(
            self.sociability, self.aggression, self.lawfulness, self.stability
        )

    def adjust_facets_by_cat(self, cat: Cat, do_removal: bool = False):
        """
        Adjusts the afterlife's facet averages according to the facets of the given cat
        :param cat: The cat object adjust facets by
        :param do_removal: Set True if the cat's facets are being removed from the afterlife's
        """
        if do_removal:
            self.influencing_cats.remove(cat.ID)
        else:
            self.influencing_cats.add(cat.ID)

        num_of_influencers = len(self.influencing_cats)

        if do_removal:
            self._total_lawfulness -= cat.personality.lawfulness
            self._total_sociability -= cat.personality.sociability
            self._total_aggression -= cat.personality.aggression
            self._total_stability -= cat.personality.stability
        else:
            self._total_lawfulness += cat.personality.lawfulness
            self._total_sociability += cat.personality.sociability
            self._total_aggression += cat.personality.aggression
            self._total_stability += cat.personality.stability

        self._law = self._get_adjusted_facet_average(
            self._total_lawfulness,
            num_of_influencers,
        )

        self._social = self._get_adjusted_facet_average(
            self._total_sociability,
            num_of_influencers,
        )

        self._aggress = self._get_adjusted_facet_average(
            self._total_aggression,
            num_of_influencers,
        )

        self._stable = self._get_adjusted_facet_average(
            self._total_stability,
            num_of_influencers,
        )

    @staticmethod
    def _get_adjusted_facet_average(
        total: int,
        num_of_influencers: int,
    ) -> int:
        """
        Handles the math for adjust average facets.
        :param total: The facet's total value derived from all influencing cats
        :param num_of_influencers: The number of cats influencing the average
        :return: The adjusted average
        """
        if not num_of_influencers:
            return 0
        return total // num_of_influencers


def get_temper_alignment(
    sociability: int, aggression: int, lawfulness: int, stability: int
) -> tuple[str, str]:
    """
    Returns the temperament strings associated with given values
    """
    first_temper = _find_alignment(
        constants.TEMPERAMENT_DICTS[0], sociability, aggression
    )
    second_temper = _find_alignment(
        constants.TEMPERAMENT_DICTS[1], lawfulness, stability
    )

    return first_temper, second_temper


def _find_alignment(temper_dict: dict, first_value: int, second_value: int) -> str:
    """
    Helper function that returns the string on a temper alignment chart for the first and second values.
    :param temper_dict: The temper alignment chart dictionary.
    :param first_value: The first value to find the alignment for. This is the chart's "y_value", or when viewing it as a dictionary: its keys.
    :param second_value: The second value to find the alignment for. This is the chart's "x-value", or when viewing it as a dictionary: its values.
    """
    if 11 <= first_value:
        temper = list(temper_dict.values())[2]
    elif 7 <= first_value:
        temper = list(temper_dict.values())[1]
    else:
        temper = list(temper_dict.values())[0]

    if 11 <= second_value:
        temper = temper[2]
    elif 7 <= second_value:
        temper = temper[1]
    else:
        temper = temper[0]

    return temper


clan_class = Clan()
clan_class.remove_cat(cat_class.ID)
