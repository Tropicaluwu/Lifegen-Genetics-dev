from random import choice, randrange
from re import sub
from typing import Optional
import random

import ujson
from uuid import uuid4

import i18n
import pygame
import pygame_gui
from pygame_gui.core import ObjectID
from ..cat.enums import CatAge, CatRank, CatGroup, CatSocial, CatStanding
from scripts.ui.elements.modified_scrolling_container import (
    UIModifiedScrollingContainer,
)

import scripts.screens.screens_core.screens_core
from scripts.cat.cats import Cat, cat_class, BACKSTORIES, create_example_cats, create_cat
from scripts.cat.pronouns import get_default_pronouns
from scripts.cat.pelts import Pelt
from scripts.cat.legacy_pelt import LegacyPelt
from scripts.cat.personality import Personality
from scripts.cat.sprites.display_sprites import generate_sprite
from scripts.screens.EventsScreen import EventsScreen
from scripts.cat.names import names
from scripts.clan import Clan
from scripts.clan_package.settings import set_clan_setting
from scripts.events_module.patrol.patrol import Patrol
from scripts.game_structure import image_cache, constants
from ..game_structure.game.switches import switch_set_value, switch_get_value, Switch

from scripts.game_structure import game
from .screens_core.screens_core import rebuild_top_menu_buttons
from ..ui.elements.sprite_button import UISpriteButton
from ..ui.elements.image_button import UIImageButton
from ..ui.elements.surface_image_button import UISurfaceImageButton
from ..ui.elements.text_box_tweaked import UITextBoxTweaked
from ..ui.theme import get_text_box_theme
from ..ui.scale import ui_scale, ui_scale_dimensions, ui_scale_offset, ui_scale_blit
from .Screens import Screens
from .enums import GameScreen
from ..cat import save_load
from ..cat.enums import CatRank
from ..cat.sprites.load_sprites import sprites
from ..clan_package.settings import get_clan_setting, load_clan_settings, reset_loaded_clan_settings
from ..game_structure.game.settings import game_setting_set, game_setting_get
from ..game_structure.game.switches import switch_get_value, switch_set_value, Switch
from ..game_structure.screen_settings import MANAGER, screen
from ..ui.windows.symbol_filter import SymbolFilterWindow
from ..ui.generate_box import get_box, BoxStyles
from ..ui.generate_button import ButtonStyles, get_button_dict
from ..ui.icon import Icon
from scripts.cat.skills import SkillPath, Skill
from scripts.events_module.patrol.patrol import Patrol



class MakeClanScreen(Screens):
    # UI images

    ui_images = {
        "clan_frame": pygame.image.load(
            "resources/images/pick_clan_screen/clan_name_frame.png"
        ).convert_alpha(),
        "name_clan": pygame.image.load(
            "resources/images/pick_clan_screen/name_clan_light.png"
        ).convert_alpha(),
        "leader": pygame.image.load(
            "resources/images/pick_clan_screen/clan_light.png"
        ).convert_alpha(),

        "your_name": (
            (pygame.image.load(
            'resources/images/pick_clan_screen/your_name_screen.png'
        ).convert_alpha())
        if not game_setting_get("dark mode") else 
            (pygame.image.load(
                'resources/images/pick_clan_screen/your_name_screen_dark.png'
            ).convert_alpha()))
        }
    your_name_txt1 = pygame.transform.scale(pygame.image.load(
        'resources/images/pick_clan_screen/your_name_text_1.png').convert_alpha(), (796, 52))
    your_name_txt2 = pygame.transform.scale(pygame.image.load(
        'resources/images/pick_clan_screen/your_name_text_2.png').convert_alpha(), (536, 52))
    
    #images for the customizing screen
    sprite_preview_bg = pygame.transform.scale(pygame.image.load(
        'resources/images/sprite_preview.png').convert_alpha(), (1600, 1400))
    
    sprite_preview_bg_dark = pygame.transform.scale(pygame.image.load(
        'resources/images/sprite_preview_dark.png').convert_alpha(), (1600, 1400))
    
    poses_bg = pygame.transform.scale(pygame.image.load(
        'resources/images/poses_bg.png').convert_alpha(), (1600, 1400))
    
    poses_bg_dark = pygame.transform.scale(pygame.image.load(
        'resources/images/poses_bg_dark.png').convert_alpha(), (1600, 1400))
    
    choice_bg = pygame.transform.scale(pygame.image.load(
        'resources/images/custom_choice_bg.png').convert_alpha(), (1600, 1400))
    
    choice_bg_dark = pygame.transform.scale(pygame.image.load(
        'resources/images/custom_choice_bg_dark.png').convert_alpha(), (1600, 1400))


    classic_mode_text = "screens.make_clan.classic_info"

    expanded_mode_text = "screens.make_clan.expanded_info"
    
    cruel_mode_text = "screens.make_clan.cruel_season_info"

    single_clan_text = "screens.make_clan.singleclan_info"

    multi_clan_text = "screens.make_clan.multiclan_info"

    # This section holds all the information needed
    game_mode = 'expanded'  # To save the users selection before conformation.
    clan_count_mode = 'singleclan'
    clan_name = ""  # To store the clan name before conformation
    leader = None  # To store the clan leader before conformation
    deputy = None
    med_cat = None
    members = []
    elected_camp = None
    your_cat = None

    # holds the symbol we have selected
    symbol_selected = None
    tag_list_len = 0
    # Holds biome we have selected
    biome_selected = None
    selected_camp_tab = 1
    selected_season = None
    # Camp number selected
    camp_num = "1"
    # Holds the cat we have currently selected.
    selected_cat = None
    # Hold which sub-screen we are on
    sub_screen = 'name clan'
    # Holds which ranks we are currently selecting.
    choosing_rank = None
    # To hold the images for the sections. Makes it easier to kill them
    elements = {}
    tabs = {}
    symbol_buttons = {}

    # used in symbol screen only - parent container is in element dict
    text = {}

    # LG: all accs
    if game_setting_get("lifegen_sprite_changes"):
        all_accs = (Pelt.all_lifegen_accessories)
    else:
        all_accs = (Pelt.all_clangen_accessories)

    def __init__(self, name="make_clan_screen"):
        super().__init__(name)
        # current page for symbol choosing
        self.current_page = 1

        self.rolls_left = constants.CONFIG["clan_creation"]["rerolls"]
        self.menu_warning = None

    def screen_switches(self):
        super().screen_switches()
        self.set_mute_button_position("topright")
        self.show_mute_buttons()
        self.set_bg("default", "mainmenu_bg")
        reset_loaded_clan_settings()

        self.clan_frame_img = pygame.transform.scale(
            self.ui_images["clan_frame"],
            ui_scale_dimensions((216, 50)),
        )
        self.name_clan_img = pygame.transform.scale(
            self.ui_images["name_clan"],
            ui_scale_dimensions((800, 700)),
        )
        self.leader_img = pygame.transform.scale(
            self.ui_images["leader"],
            ui_scale_dimensions((800, 700)),
        )
        self.name_cat_img = pygame.transform.scale(
            self.ui_images["your_name"],
            ui_scale_dimensions((800, 700)),
        )
        
        constants.reset_config()

        # Reset variables
        self.game_mode = 'expanded'
        self.clan_name = ""
        self.selected_camp_tab = 1
        self.biome_selected = None
        self.selected_season = "Newleaf"
        self.symbol_selected = None
        self.leader = None  # To store the Clan leader before confirmation
        self.deputy = None
        self.med_cat = None
        self.members = []
        self.clan_size = "medium"
        self.clan_age = "established"
        
        self.custom_cat = None
        self.elements = {}

        self.preview_age = "kitten"
        self.newborn_pose = 0
        self.kitten_sprite = 0
        self.adolescent_pose = 0
        self.adult_pose = 0
        self.elder_pose = 0
        
        self.opacity=100
        self.skill = "Random"
        self.personality = ""
        self.permanent_condition = None
        self.page = 0
        self.faith = "flexible"
        game.choose_cats = {}
        self.skills = ["Random"]
        self.current_members = []
        self.social = CatSocial.CLANCAT

        for skillpath in SkillPath:
            count = 0
            for skill in skillpath.value:
                count += 1
                if count == 1:
                    self.skills.append(skill)

        # NEW CUSTOMISER BUTTON DICTS

        self.current_selection = "pelt_pattern"
        self.customiser_sort = "default"
        self.search_text = ""
        self.previous_search_text = "search"

        self.tortie_enabled = False
        self.current_selection_buttons = {}
        # Page 0
        self.preview_age_buttons = {}
        self.newborn_pose_buttons = {}
        self.kitten_pose_buttons = {}
        self.adolescent_pose_buttons = {}
        self.adult_pose_buttons = {}
        self.elder_pose_buttons = {}
        self.fur_length_buttons = {}
        self.reverse_buttons = {}
        # Page 1
        self.pelt_colour_buttons = {}
        self.pelt_pattern_buttons = {}
        self.tint_buttons = {}

        self.tortie_patches_buttons = {}
        self.tortie_colour_buttons = {}
        self.tortie_pattern_buttons = {}

        self.pelt_colour_names = {}
        self.pelt_pattern_names = {}

        self.white_patches_buttons = {}
        self.white_patches_names = {}

        self.points_buttons = {}
        self.points_names = {}

        self.vitiligo_buttons = {}
        self.vitiligo_names = {}

        self.white_patches_tint_buttons = {}

        self.tortie_patches_names = {}
        self.tortie_colour_names = {}
        self.tortie_pattern_names = {}
        

        # Page 2
        self.eye_colour_buttons = {}
        self.eye_colour_names = {}

        self.heterochromia_buttons = {}
        self.heterochromia_names = {}

        self.skin_buttons = {}
        self.skin_names = {}

        self.scar_buttons = {}
        self.scar_names = {}

        self.accessory_buttons = {}
        self.accessory_names = {}

        # Page 3
        self.condition_buttons = {}
        self.condition_names = {}

        self.trait_buttons = {}
        self.trait_names = {}

        self.skill_buttons = {}
        self.skill_names = {}

        self.faith_buttons = {}
        self.faith_names = {}

        self.sex_buttons = {}

        self.customiser_button_dicts = [
            self.current_selection_buttons,
            self.preview_age_buttons,
            self.newborn_pose_buttons,
            self.kitten_pose_buttons,
            self.adolescent_pose_buttons,
            self.adult_pose_buttons,
            self.elder_pose_buttons,
            self.fur_length_buttons,
            self.reverse_buttons,

            self.pelt_colour_buttons,
            self.pelt_pattern_buttons,
            self.tint_buttons,

            self.white_patches_buttons,
            self.white_patches_names,
            self.points_buttons,
            self.points_names,

            self.vitiligo_buttons,
            self.vitiligo_names,

            self.white_patches_tint_buttons,

            self.tortie_patches_buttons,
            self.tortie_colour_buttons,
            self.tortie_pattern_buttons,

            self.pelt_colour_names,
            self.pelt_pattern_names,

            self.tortie_patches_names,
            self.tortie_colour_names,
            self.tortie_pattern_names,

            self.eye_colour_buttons,
            self.eye_colour_names,

            self.heterochromia_buttons,
            self.heterochromia_names,

            self.skin_buttons,
            self.skin_names,

            self.scar_buttons,
            self.scar_names,

            self.accessory_buttons,
            self.accessory_names,

            self.condition_buttons,
            self.condition_names,

            self.trait_buttons,
            self.trait_names,

            self.skill_buttons,
            self.skill_names,

            self.faith_buttons,
            self.faith_names,

            self.sex_buttons
            ]
        
        switch_set_value(
            Switch.disallowed_symbol_tags, []
        )

        # Buttons that appear on every screen.
        # self.menu_warning = pygame_gui.elements.UITextBox(
        #     '',
        #     ui_scale(pygame.Rect((50, 50), (600, -1))),
        #     object_id=get_text_box_theme("#text_box_22_horizleft"),
        #     manager=MANAGER,
        # )
        self.main_menu = UISurfaceImageButton(
            ui_scale(pygame.Rect((25, 50), (153, 30))),
            "buttons.main_menu",
            get_button_dict(ButtonStyles.SQUOVAL, (153, 30)),
            manager=MANAGER,
            object_id="@buttonstyles_squoval",
            starting_height=2,
        )

        if switch_get_value(Switch.customise_new_life):
            for c in list(Cat.all_cats.keys()):
                self.current_members.append(c)
            create_example_cats()
            self.hide_menu_buttons()
            self.open_choose_leader()
        else:
            create_example_cats()
            self.open_clan_count()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            if event.ui_element == self.main_menu:
                # leaving a new life early, the kits made to choose from have to go
                if switch_get_value(Switch.customise_new_life):
                    self.delete_example_cats()
                    switch_set_value(Switch.customise_new_life, False)
                if switch_get_value(Switch.clan_list):
                    load_clan_settings()
                self.change_screen(GameScreen.START)
            elif self.sub_screen == "clan count mode":
                self.handle_clan_count_mode_event(event)
            elif self.sub_screen == "name clan":
                self.handle_name_clan_event(event)
            elif self.sub_screen == 'choose name':
                self.handle_choose_name_event(event)
            elif self.sub_screen == 'choose leader':
                self.handle_choose_leader_event(event)
            elif self.sub_screen == 'customize cat':
                self.handle_customize_cat_event(event)
            elif self.sub_screen == 'choose camp':
                self.handle_choose_background_event(event)
            elif self.sub_screen == "choose symbol":
                self.handle_choose_symbol_event(event)
            elif self.sub_screen == "saved screen":
                self.handle_saved_clan_event(event)
            self.mute_button_pressed(event)
        
        elif event.type == pygame.KEYDOWN and game_setting_get('keybinds'):
            if self.sub_screen == 'name clan':
                self.handle_name_clan_key(event)
            elif self.sub_screen == "choose camp":
                self.handle_choose_background_key(event)
            elif self.sub_screen == "saved screen" and (
                event.key == pygame.K_RETURN or event.key == pygame.K_RIGHT
            ):
                self.change_screen(GameScreen.START)

    def handle_clan_count_mode_event(self, event):
        """Handle events for the clan count screen"""
        # Clan count mode selection buttons
        if event.ui_element == self.elements['singleclan_mode_button']:
            self.clan_count_mode = 'singleclan'
            self.refresh_text_and_buttons()
        elif event.ui_element == self.elements['multiclan_mode_button']:
            self.clan_count_mode = 'multiclan'
            self.refresh_text_and_buttons()
        # When the next_step button is pressed, go to the Clan naming page.
        elif event.ui_element == self.elements["next_step"]:
            game_setting_set("game_mode", self.game_mode)
            self.open_name_clan()
    
    def handle_name_clan_event(self, event):
        if event.ui_element == self.elements["random"]:
            self.elements["name_entry"].set_text(self.random_clan_name())
        elif event.ui_element == self.elements["reset_name"]:
            self.elements["name_entry"].set_text("")
        elif event.ui_element == self.elements["next_step"]:
            self.clan_name = self.elements["name_entry"].get_text().strip()
            self.open_choose_leader()
        elif event.ui_element == self.elements["previous_step"]:
            self.clan_name = ""
            self.open_clan_count()
        elif event.ui_element == self.elements['small']:
            self.elements['small'].disable()
            self.elements['medium'].enable()
            self.elements['large'].enable()
            self.clan_size = "small"
        elif event.ui_element == self.elements['medium']:
            self.elements['small'].enable()
            self.elements['medium'].disable()
            self.elements['large'].enable()
            self.clan_size = "medium"
        elif event.ui_element == self.elements['large']:
            self.elements['small'].enable()
            self.elements['large'].disable()
            self.elements['medium'].enable()
            self.clan_size = "large"
        elif event.ui_element == self.elements["established"]:
            self.elements['established'].disable()
            self.elements['new'].enable()
            self.clan_age = "established"
        elif event.ui_element == self.elements["new"]:
            self.elements['established'].enable()
            self.elements['new'].disable()
            self.clan_age = "new"
    
    def handle_name_clan_key(self, event):
        if event.key == pygame.K_ESCAPE:
            self.change_screen(GameScreen.START)
        elif event.key == pygame.K_LEFT:
            if not self.elements["name_entry"].is_focused:
                self.clan_name = ""
        elif event.key == pygame.K_RIGHT:
            if not self.elements["name_entry"].is_focused:
                new_name = sub(
                    r"[^A-Za-z0-9 ]+", "", self.elements["name_entry"].get_text()
                ).strip()
                if not new_name:
                    self.elements["error"].set_text("Your Clan's name cannot be empty")
                    self.elements["error"].show()
                    return
                self.clan_name = new_name
                self.open_choose_leader()
        elif event.key == pygame.K_RETURN:
            new_name = sub(
                r"[^A-Za-z0-9 ]+", "", self.elements["name_entry"].get_text()
            ).strip()
            if not new_name:
                self.elements["error"].set_text("Your Clan's name cannot be empty")
                self.elements["error"].show()
                return
            self.clan_name = new_name
            self.open_choose_leader()

    def handle_choose_leader_event(self, event):
        if event.ui_element in (
            self.elements["roll1"],
            self.elements["roll2"],
            self.elements["roll3"],
            self.elements["dice"],
        ):
            self.elements["select_cat"].hide()
            game.choose_cats = {}
            create_example_cats()  # create new cats
            self.selected_cat = (
                None  # Your selected cat now no longer exists. Sad. They go away.
            )
            self.refresh_cat_images_and_info()  # Refresh all the images.
            self.rolls_left -= 1
            if constants.CONFIG["clan_creation"]["rerolls"] == 3:
                event.ui_element.disable()
            else:
                self.elements["reroll_count"].set_text(str(self.rolls_left))
                if self.rolls_left == 0:
                    event.ui_element.disable()

        elif event.ui_element in [self.elements["cat" + str(u)] for u in range(0, 12)]:
            self.selected_cat = event.ui_element.return_cat_object()
            self.refresh_cat_images_and_info(self.selected_cat)
            self.refresh_text_and_buttons()
        elif event.ui_element == self.elements['select_cat']:
            self.your_cat = self.selected_cat
            self.selected_cat = None
            self.open_name_cat()
        elif event.ui_element == self.elements['previous_step']:
            if switch_get_value(Switch.customise_new_life):
                self.delete_example_cats()
                self.change_screen(game.last_screen_forupdate)
                switch_set_value(Switch.customise_new_life, False)
            else:
                self.clan_name = ""
                self.open_name_clan()
        elif event.ui_element == self.elements['customize']:
            self.open_customize_cat()
        elif event.ui_element == self.elements["clancat"]:
            self.social = CatSocial.CLANCAT
            self.refresh_text_and_buttons()

        elif event.ui_element == self.elements["kittypet"]:
            self.social = CatSocial.KITTYPET
            self.refresh_text_and_buttons()

        elif event.ui_element == self.elements["loner"]:
            self.social = CatSocial.LONER
            self.refresh_text_and_buttons()

        elif event.ui_element == self.elements["rogue"]:
            self.social = CatSocial.ROGUE
            self.refresh_text_and_buttons()

            
    def handle_choose_name_event(self, event):
        if event.ui_element == self.elements['next_step']:
            new_name = sub(r'[^A-Za-z0-9 ]+', "", self.elements["name_entry"].get_text()).strip()
            if not new_name:
                self.elements["error"].set_text("Your cat's name cannot be empty")
                self.elements["error"].show()
                return
            self.your_cat.name.prefix = new_name

            while self.your_cat.name.prefix.lower() == self.your_cat.name.suffix:
                print("Prefix and suffix are the same, rerolling suffix...")
                self.your_cat.name.give_suffix(self.your_cat.pelt, game.clan.biome, None)

            if switch_get_value(Switch.customise_new_life):
                self.open_clan_saved_screen()
            else:
                self.open_choose_background()

        elif event.ui_element == self.elements["random"]:
            self.elements["name_entry"].set_text(choice(names.names_dict["normal_prefixes"]))
        elif event.ui_element == self.elements['previous_step']:
            self.selected_cat = None
            self.open_choose_leader()
    
    def handle_create_other_cats(self):
        """
        Creates the rest of the Clan
        """
        self.create_clan_cats()
        # assign a leader, deputy, and medcat since the player couldnt choose them
        self.leader = Cat(status_dict={"rank": CatRank.LEADER, "age": CatAge.ADULT})
        self.deputy = Cat(status_dict={"rank": CatRank.DEPUTY, "age": CatAge.ADULT})
        self.med_cat = Cat(status_dict={"rank": CatRank.MEDICINE_CAT, "age": CatAge.ADULT})
        for cat in game.choose_cats.values():
            self.members.append(cat)
        self.members.append(self.your_cat)
        
    def create_clan_cats(self):
        """ 
        Creates the other Clan cats
        """
        e = random.sample(range(12), 3)
        not_allowed = ['NOPAW', 'NOTAIL', 'HALFTAIL', 'NOEAR', 'BOTHBLIND', 'RIGHTBLIND', 'LEFTBLIND', 'BRIGHTHEART',
                    'NOLEFTEAR', 'NORIGHTEAR', 'MANLEG']
        c_size = 15
        backstories = ["clan_founder"]
        for i in range(1, 18):
            backstories.append(f"clan_founder{i}")
        if self.clan_age == "established":
            backstories = ['halfclan1', 'halfclan2', 'outsider_roots1', 'outsider_roots2', 'loner1', 'loner2', 'kittypet1', 'kittypet2', 'kittypet3', 'kittypet4', 'rogue1', 'rogue2', 'rogue3', 'rogue4', 'rogue5', 'rogue6', 'rogue7', 'rogue8', 'abandoned1', 'abandoned2', 'abandoned3', 'abandoned4', 'otherclan1', 'otherclan2', 'otherclan3', 'otherclan4', 'otherclan5', 'otherclan6', 'otherclan7', 'otherclan8', 'otherclan9', 'otherclan10', 'disgraced1', 'disgraced2', 'disgraced3', 'refugee1', 'refugee2', 'refugee3', 'refugee4', 'refugee5', 'tragedy_survivor1', 'tragedy_survivor2', 'tragedy_survivor3', 'tragedy_survivor4', 'tragedy_survivor5', 'tragedy_survivor6', 'guided1', 'guided2', 'guided3', 'guided4', 'orphaned1', 'orphaned2', 'orphaned3', 'orphaned4', 'orphaned5', 'orphaned6', 'outsider1', 'outsider2', 'outsider3', 'kittypet5', 'kittypet6', 'kittypet7', 'guided5', 'guided6', 'outsider4', 'outsider5', 'outsider6', 'orphaned7', 'halfclan4', 'halfclan5', 'halfclan6', 'halfclan7', 'halfclan8', 'halfclan9', 'halfclan10', 'outsider_roots3', 'outsider_roots4', 'outsider_roots5', 'outsider_roots6', 'outsider_roots7', 'outsider_roots8']
        elif self.clan_age == "new":
            unique_backstories = ["clan_founder4", "clan_founder13", "clan_founder14", "clan_founder15"]
            chosen_unique = choice(unique_backstories)
            backstories = [
                story for story in backstories
                if story not in unique_backstories or story == chosen_unique
            ]

        if self.clan_size == "small":
            c_size = 10
        elif self.clan_size == 'large':
            c_size = 20
        
        special_ranks = 0
        special_rank_str = [CatRank.MEDICINE_CAT,
                            CatRank.MEDICINE_APPRENTICE,
                            CatRank.WARRIOR,
                            CatRank.APPRENTICE,
                            CatRank.KITTEN,
                            CatRank.ELDER,
                            CatRank.MEDIATOR,
                            CatRank.MEDIATOR_APPRENTICE,
                            CatRank.QUEEN,
                            CatRank.QUEENS_APPRENTICE]

        for a in range(c_size):
            if a in e:
                game.choose_cats[a] = Cat(status_dict={"rank": CatRank.WARRIOR}, biome=None)
            else:
                
                status_percentages = [
                    (CatRank.MEDICINE_CAT, 1),
                    (CatRank.MEDICINE_APPRENTICE, 1),
                    (CatRank.WARRIOR, 38),
                    (CatRank.APPRENTICE, 15),
                    (CatRank.KITTEN, 5),
                    (CatRank.ELDER, 5),
                    (CatRank.MEDIATOR, 2),
                    (CatRank.MEDIATOR_APPRENTICE, 3),
                    (CatRank.QUEEN, 2),
                    (CatRank.QUEENS_APPRENTICE, 3),
                ]

                status_choices = []
                for status, percentage in status_percentages:
                    status_choices.extend([status] * percentage)

                s = random.choice(status_choices)

                if special_ranks > 5:
                    if s in special_rank_str:
                        s = random.choice(status_choices)

                if s in special_rank_str:
                    special_ranks += 1

                game.choose_cats[a] = Cat(status_dict={"rank": s}, biome=None)

            if game.choose_cats[a].moons >= 160:
                game.choose_cats[a].moons = choice(range(120, 155))
            elif game.choose_cats[a].moons == 0:
                game.choose_cats[a].moons = choice([1, 2, 3, 4, 5])

            # fucking inventory
            game.choose_cats[a].pelt.inventory = []

            if self.clan_age == "new":
                if game.choose_cats[a].status.rank not in ['newborn', 'kitten']:
                    game.choose_cats[a].backstory = choice(backstories)
                else:
                    game.choose_cats[a].backstory = 'clanborn'
            else:
                if random.randint(1,5) == 1 and game.choose_cats[a].status.rank not in ['newborn', 'kitten']:
                    game.choose_cats[a].backstory = choice(backstories)
                else:
                    game.choose_cats[a].backstory = 'clanborn'
    
    def handle_choose_background_event(self, event):
        if event.ui_element == self.elements['previous_step']:
            self.open_name_cat()
        elif event.ui_element == self.elements['forest_biome']:
            self.biome_selected = "Forest"
            self.selected_camp_tab = 1
            self.refresh_text_and_buttons()
        elif event.ui_element == self.elements["mountain_biome"]:
            self.biome_selected = "Mountainous"
            self.selected_camp_tab = 1
            self.refresh_text_and_buttons()
        elif event.ui_element == self.elements["plains_biome"]:
            self.biome_selected = "Plains"
            self.selected_camp_tab = 1
            self.refresh_text_and_buttons()
        elif event.ui_element == self.elements["beach_biome"]:
            self.biome_selected = "Beach"
            self.selected_camp_tab = 1
            self.refresh_text_and_buttons()
        elif event.ui_element == self.tabs["tab1"]:
            self.selected_camp_tab = 1
            self.refresh_selected_camp()
        elif event.ui_element == self.tabs["tab2"]:
            self.selected_camp_tab = 2
            self.refresh_selected_camp()
        elif event.ui_element == self.tabs["tab3"]:
            self.selected_camp_tab = 3
            self.refresh_selected_camp()
        elif event.ui_element == self.tabs["tab4"]:
            self.selected_camp_tab = 4
            self.refresh_selected_camp()
        elif event.ui_element == self.tabs["tab5"]:
            self.selected_camp_tab = 5
            self.refresh_selected_camp()
        elif event.ui_element == self.tabs["tab6"]:
            self.selected_camp_tab = 6
            self.refresh_selected_camp()
        elif event.ui_element == self.tabs["tab7"]:
            self.selected_camp_tab = 7
            self.refresh_selected_camp()
        elif event.ui_element == self.tabs["tab8"]:
            self.selected_camp_tab = 8
            self.refresh_selected_camp()
        elif event.ui_element == self.tabs["tab9"]:
            self.selected_camp_tab = 9
            self.refresh_selected_camp()
        elif event.ui_element == self.tabs["tab10"]:
            self.selected_camp_tab = 10
            self.refresh_selected_camp()
        elif event.ui_element == self.tabs["newleaf_tab"]:
            self.selected_season = "Newleaf"
            self.refresh_text_and_buttons()
        elif event.ui_element == self.tabs["greenleaf_tab"]:
            self.selected_season = "Greenleaf"
            self.refresh_text_and_buttons()
        elif event.ui_element == self.tabs["leaffall_tab"]:
            self.selected_season = "Leaf-fall"
            self.refresh_text_and_buttons()
        elif event.ui_element == self.tabs["leafbare_tab"]:
            self.selected_season = "Leaf-bare"
            self.refresh_text_and_buttons()
        elif event.ui_element == self.elements["random_background"]:
            # Select a random biome and background

            self.biome_selected = self.random_biome_selection()

            if self.biome_selected == 'Forest':
                self.selected_camp_tab = 1
                if self.social == CatSocial.CLANCAT:
                    self.selected_camp_tab = randrange(1, 7)
            elif self.biome_selected == "Mountainous":
                self.selected_camp_tab = 1
                if self.social == CatSocial.CLANCAT:
                    self.selected_camp_tab = randrange(1, 7)
            elif self.biome_selected == "Plains":
                self.selected_camp_tab = 1
                if self.social == CatSocial.CLANCAT:
                    self.selected_camp_tab = randrange(1, 10)
            else:
                self.selected_camp_tab = 1
                if self.social == CatSocial.CLANCAT:
                    self.selected_camp_tab = randrange(1, 5)
            self.refresh_selected_camp()
            self.refresh_text_and_buttons()
        elif event.ui_element == self.elements["next_step"]:
            self.open_choose_symbol()

    def handle_choose_background_key(self, event):
        if event.key == pygame.K_RIGHT:
            if self.biome_selected is None:
                self.biome_selected = "Forest"
            elif self.biome_selected == "Forest":
                self.biome_selected = "Mountainous"
            elif self.biome_selected == "Mountainous":
                self.biome_selected = "Plains"
            elif self.biome_selected == "Plains":
                self.biome_selected = "Beach"
            self.selected_camp_tab = 1
            self.refresh_text_and_buttons()
        elif event.key == pygame.K_LEFT:
            if self.biome_selected is None:
                self.biome_selected = "Beach"
            elif self.biome_selected == "Beach":
                self.biome_selected = "Plains"
            elif self.biome_selected == "Plains":
                self.biome_selected = "Mountainous"
            elif self.biome_selected == "Mountainous":
                self.biome_selected = "Forest"
            self.selected_camp_tab = 1
            self.refresh_text_and_buttons()
        elif event.key == pygame.K_UP and self.biome_selected is not None:
            if self.selected_camp_tab > 1:
                self.selected_camp_tab -= 1
                self.refresh_selected_camp()
        elif event.key == pygame.K_DOWN and self.biome_selected is not None:
            if self.selected_camp_tab < 6:
                self.selected_camp_tab += 1
                self.refresh_selected_camp()
        elif event.key == pygame.K_RETURN:
            self.save_clan()
            self.open_clan_saved_screen()

    def handle_choose_symbol_event(self, event):
        if event.ui_element == self.elements["previous_step"]:
            self.open_choose_background()
        elif event.ui_element == self.elements["page_right"]:
            self.current_page += 1
            self.refresh_symbol_list()
        elif event.ui_element == self.elements["page_left"]:
            self.current_page -= 1
            self.refresh_symbol_list()
        elif event.ui_element == self.elements["done_button"]:
            self.save_clan()
            self.open_clan_saved_screen()
        elif event.ui_element == self.elements["random_symbol_button"]:
            if self.symbol_selected:
                if self.symbol_selected in self.symbol_buttons:
                    self.symbol_buttons[self.symbol_selected].enable()
            self.symbol_selected = choice(sprites.clan_symbols)
            self.refresh_text_and_buttons()
        elif event.ui_element == self.elements["filters_tab"]:
            SymbolFilterWindow()
        else:
            for symbol_id, element in self.symbol_buttons.items():
                if event.ui_element == element:
                    if self.symbol_selected:
                        if self.symbol_selected in self.symbol_buttons:
                            self.symbol_buttons[self.symbol_selected].enable()
                    self.symbol_selected = symbol_id
                    self.refresh_text_and_buttons()

    def handle_saved_clan_event(self, event):
        if event.ui_element == self.elements["continue"]:
            # redoing this here bc its usually done on the symbol screen
            # which we don't get with a new life
            if switch_get_value(Switch.customise_new_life):
                self.save_clan()
                self.open_clan_saved_screen()
                switch_set_value(Switch.customise_new_life, False)
            self.change_screen(GameScreen.CAMP)

    def exit_screen(self):
        self.main_menu.kill()
        # self.menu_warning.kill()
        self.clear_all_page()
        self.rolls_left = constants.CONFIG["clan_creation"]["rerolls"]
        self.fullscreen_bgs = {}
        self.game_bgs = {}
        self.set_mute_button_position("bottomright")
        constants.load_clan_config()
        return super().exit_screen()

    def on_use(self):
        super().on_use()
        # Don't allow someone to enter no name for their clan
        if self.sub_screen == "name clan":
            if self.elements["name_entry"].get_text() == "":
                self.elements["next_step"].disable()
            elif self.elements["name_entry"].get_text().startswith(" "):
                self.elements["error"].set_text(
                    "screens.make_clan.error_clan_name_space"
                )
                self.elements["error"].show()
                self.elements["next_step"].disable()
            else:
                self.elements["error"].hide()
                self.elements['next_step'].enable()
            # Set the background for the name clan page - done here to avoid GUI layering issues
            screen.blit(self.name_clan_img, ui_scale_blit((0, 0)))
            
        elif self.sub_screen == 'choose name':
            if self.elements["name_entry"].get_text() == "":
                self.elements['next_step'].disable()
            elif self.elements["name_entry"].get_text().startswith(" "):
                self.elements["error"].set_text("Your name cannot start with a space.")
                self.elements["error"].show()
                self.elements['next_step'].disable()
            else:
                self.elements["error"].hide()
                self.elements['next_step'].enable()

            screen.blit(self.name_cat_img, ui_scale_blit((0,0)))
        if self.sub_screen == "choose symbol":
            if (
                len(switch_get_value(Switch.disallowed_symbol_tags))
                != self.tag_list_len
            ):
                self.tag_list_len = len(switch_get_value(Switch.disallowed_symbol_tags))
                self.refresh_symbol_list()

    def clear_all_page(self):
        """Clears the entire page, including layout images"""
        for image in self.elements:
            self.elements[image].kill()
        for tab in self.tabs:
            self.tabs[tab].kill()
        for button in self.symbol_buttons:
            self.symbol_buttons[button].kill()
        self.symbol_buttons = {}
        self.elements = {}

        for item in self.customiser_button_dicts:
            for ele in item:
                item[ele].kill()
            item = {}

    def refresh_text_and_buttons(self):
        """Refreshes the button states and text boxes"""
        if self.sub_screen == "clan count mode":
            if self.clan_count_mode == 'singleclan':
                display_text = self.single_clan_text
                display_name = "Single Clan"
            else:
                display_text = self.multi_clan_text
                display_name = "Multiple Clans"
            self.elements['mode_details'].set_text(display_text)
            self.elements['mode_name'].set_text(display_name)

            if self.clan_count_mode == 'singleclan':
                self.elements['singleclan_mode_button'].disable()
                self.elements['multiclan_mode_button'].enable()
            elif self.clan_count_mode == 'multiclan':
                self.elements['singleclan_mode_button'].enable()
                self.elements['multiclan_mode_button'].disable()
        elif self.sub_screen == "game mode":
            # Set the mode explanation text
            if self.game_mode == "classic":
                display_text = self.classic_mode_text
                display_name = "screens.make_clan.classic_label"
            elif self.game_mode == "expanded":
                display_text = self.expanded_mode_text
                display_name = "screens.make_clan.expanded_label"
            elif self.game_mode == "cruel season":
                display_text = self.cruel_mode_text
                display_name = "screens.make_clan.cruel_season_label"
            else:
                display_text = ""
                display_name = "ERROR"
            self.elements["mode_details"].set_text(display_text)
            self.elements["mode_name"].set_text(display_name)

            # Update the enabled buttons for the game selection to disable the
            # buttons for the mode currently selected. Mostly for aesthetics, and it
            # make it very clear which mode is selected.
            if self.game_mode == "classic":
                self.elements["classic_mode_button"].disable()
                self.elements["expanded_mode_button"].enable()
                self.elements["cruel_mode_button"].enable()
            elif self.game_mode == "expanded":
                self.elements["classic_mode_button"].enable()
                self.elements["expanded_mode_button"].disable()
                self.elements["cruel_mode_button"].enable()
            elif self.game_mode == "cruel season":
                self.elements["classic_mode_button"].enable()
                self.elements["expanded_mode_button"].enable()
                self.elements["cruel_mode_button"].disable()
            else:
                self.elements["classic_mode_button"].enable()
                self.elements["expanded_mode_button"].enable()
                self.elements["cruel_mode_button"].enable()

            # Don't let the player go forwards with cruel mode, it's not done yet.
            if self.game_mode == "cruel season":
                self.elements["next_step"].disable()
            else:
                self.elements["next_step"].enable()
        elif self.sub_screen in ("choose leader", "choose deputy", "choose med cat"):
            # select cat will always show bc all kittens are valid :3
            if self.selected_cat:
                self.elements["select_cat"].show()
        
            if self.social == CatSocial.CLANCAT:
                self.elements["clancat"].disable()
                self.elements["kittypet"].enable()
                self.elements["loner"].enable()
                self.elements["rogue"].enable()

            elif self.social == CatSocial.KITTYPET:
                self.elements["clancat"].enable()
                self.elements["kittypet"].disable()
                self.elements["loner"].enable()
                self.elements["rogue"].enable()

            elif self.social == CatSocial.LONER:
                self.elements["clancat"].enable()
                self.elements["kittypet"].enable()
                self.elements["loner"].disable()
                self.elements["rogue"].enable()

            elif self.social == CatSocial.ROGUE:
                self.elements["clancat"].enable()
                self.elements["kittypet"].enable()
                self.elements["loner"].enable()
                self.elements["rogue"].disable()

        # Refresh the choose-members background to match number of cat's chosen.
        elif self.sub_screen == "choose members":
            if len(self.members) == 0:
                self.elements["background"].set_image(
                    pygame.transform.scale(
                        pygame.image.load(
                            "resources/images/pick_clan_screen/clan_none_light.png"
                        ).convert_alpha(),
                        ui_scale_dimensions((800, 700)),
                    )
                )
                if self.leader or self.deputy or self.med_cat:
                    self.elements["next_step"].enable()
                else:
                    self.elements["next_step"].disable()
            elif len(self.members) == 1:
                self.elements["background"].set_image(
                    pygame.transform.scale(
                        pygame.image.load(
                            "resources/images/pick_clan_screen/clan_one_light.png"
                        ).convert_alpha(),
                        ui_scale_dimensions((800, 700)),
                    )
                )
                self.elements["next_step"].enable()
                # self.elements["next_step"].disable()
            elif len(self.members) == 2:
                self.elements["background"].set_image(
                    pygame.transform.scale(
                        pygame.image.load(
                            "resources/images/pick_clan_screen/clan_two_light.png"
                        ).convert_alpha(),
                        ui_scale_dimensions((800, 700)),
                    )
                )
                self.elements["next_step"].enable()
                # self.elements["next_step"].disable()
            elif len(self.members) == 3:
                self.elements["background"].set_image(
                    pygame.transform.scale(
                        pygame.image.load(
                            "resources/images/pick_clan_screen/clan_three_light.png"
                        ).convert_alpha(),
                        ui_scale_dimensions((800, 700)),
                    )
                )
                self.elements["next_step"].enable()
                # self.elements["next_step"].disable()
            elif 4 <= len(self.members) <= 6:
                self.elements["background"].set_image(
                    pygame.transform.scale(
                        pygame.image.load(
                            "resources/images/pick_clan_screen/clan_four_light.png"
                        ).convert_alpha(),
                        ui_scale_dimensions((800, 700)),
                    )
                )
                self.elements["next_step"].enable()
                # In order for the "previous step" to work properly, we must enable this button, just in case it
                # was disabled in the next step.
                self.elements["select_cat"].enable()
            elif len(self.members) == 7:
                self.elements["background"].set_image(
                    pygame.transform.scale(
                        pygame.image.load(
                            "resources/images/pick_clan_screen/clan_full_light.png"
                        ).convert_alpha(),
                        ui_scale_dimensions((800, 700)),
                    )
                )
                self.elements["select_cat"].disable()
                self.elements["next_step"].enable()

            # Hide the recruit cat button if no cat is selected.
            if self.selected_cat is not None:
                self.elements["select_cat"].show()
            else:
                self.elements["select_cat"].hide()

        elif self.sub_screen == "choose camp":
            # Enable/disable biome buttons
            if self.biome_selected == "Forest":
                self.elements["forest_biome"].disable()
                self.elements["mountain_biome"].enable()
                self.elements["plains_biome"].enable()
                self.elements["beach_biome"].enable()
            elif self.biome_selected == "Mountainous":
                self.elements["forest_biome"].enable()
                self.elements["mountain_biome"].disable()
                self.elements["plains_biome"].enable()
                self.elements["beach_biome"].enable()
            elif self.biome_selected == "Plains":
                self.elements["forest_biome"].enable()
                self.elements["mountain_biome"].enable()
                self.elements["plains_biome"].disable()
                self.elements["beach_biome"].enable()
            elif self.biome_selected == "Beach":
                self.elements["forest_biome"].enable()
                self.elements["mountain_biome"].enable()
                self.elements["plains_biome"].enable()
                self.elements["beach_biome"].disable()

            if self.selected_season == "Newleaf":
                self.tabs["newleaf_tab"].disable()
                self.tabs["greenleaf_tab"].enable()
                self.tabs["leaffall_tab"].enable()
                self.tabs["leafbare_tab"].enable()
            elif self.selected_season == "Greenleaf":
                self.tabs["newleaf_tab"].enable()
                self.tabs["greenleaf_tab"].disable()
                self.tabs["leaffall_tab"].enable()
                self.tabs["leafbare_tab"].enable()
            elif self.selected_season == "Leaf-fall":
                self.tabs["newleaf_tab"].enable()
                self.tabs["greenleaf_tab"].enable()
                self.tabs["leaffall_tab"].disable()
                self.tabs["leafbare_tab"].enable()
            elif self.selected_season == "Leaf-bare":
                self.tabs["newleaf_tab"].enable()
                self.tabs["greenleaf_tab"].enable()
                self.tabs["leaffall_tab"].enable()
                self.tabs["leafbare_tab"].disable()

            if self.biome_selected and self.selected_camp_tab:
                self.elements["next_step"].enable()

            # Deal with tab and shown camp image:
            self.refresh_selected_camp()
        elif self.sub_screen == "choose symbol":
            if self.symbol_selected:
                if self.symbol_selected in self.symbol_buttons:
                    self.symbol_buttons[self.symbol_selected].disable()
                # refresh selected symbol image
                self.elements["selected_symbol"].set_image(
                    pygame.transform.scale(
                        sprites.get_symbol(self.symbol_selected),
                        ui_scale_dimensions((100, 100)),
                    ).convert_alpha()
                )
                symbol_name = self.symbol_selected.replace("symbol", "")
                self.text["selected"].set_text(
                    "screens.make_clan.symbol_selected",
                    text_kwargs={"symbol": symbol_name},
                )
                self.elements["selected_symbol"].show()
                self.elements["done_button"].enable()

    def refresh_selected_camp(self):
        """Updates selected camp image and tabs"""

        self.tabs["tab1"].kill()
        self.tabs["tab2"].kill()
        self.tabs["tab3"].kill()
        self.tabs["tab4"].kill()
        self.tabs["tab5"].kill()
        self.tabs["tab6"].kill()
        self.tabs["tab7"].kill()
        self.tabs["tab8"].kill()
        self.tabs["tab9"].kill()
        self.tabs["tab10"].kill()

        # this is all edited for lg
        camp_dict = self.get_possible_camps()

        for camp_num, camp_info in camp_dict[self.biome_selected].items():
            tab_rect = ui_scale(pygame.Rect((0, 0), (camp_info['button_width'], 30)))
            tab_rect.topright = (
                ui_scale_offset((5, 180))
                if int(camp_num) == 1 else
                ui_scale_offset((5, 5))
                )

            self.tabs[f"tab{camp_num}"] = UISurfaceImageButton(
                tab_rect,
                f"screens.make_clan.{camp_info['camp_name']}",
                get_button_dict(ButtonStyles.VERTICAL_TAB, (camp_info['button_width'], 30)),
                object_id="@buttonstyles_vertical_tab",
                manager=MANAGER,
                anchors=(
                    {
                        "right": "right",
                        "right_target": self.elements["art_frame"],
                        "top_target": self.tabs[f"tab{int(camp_num) - 1}"] 
                    }
                    if int(camp_num) > 1 else 
                    {
                        "right": "right",
                        "right_target": self.elements["art_frame"]
                    }
                )
            )

        tab_num = 10
        # how many camp tabs u need

        for num in range(tab_num + 1):
            if num == 0:
                continue
            (
                self.tabs[f"tab{num}"].disable()
                if self.selected_camp_tab == num
                else self.tabs[f"tab{num}"].enable()
            )

        # I have to do this for proper layering.
        if "camp_art" in self.elements:
            self.elements["camp_art"].kill()
        if self.biome_selected:
            src = pygame.image.load(
                self.get_camp_art_path(self.selected_camp_tab)
            ).convert_alpha()
            self.elements["camp_art"] = pygame_gui.elements.UIImage(
                ui_scale(pygame.Rect((175, 170), (450, 400))),
                pygame.transform.scale(
                    src.copy(),
                    ui_scale_dimensions((450, 400)),
                ),
                manager=MANAGER,
            )
            self.get_camp_bg(src)

        self.draw_art_frame()

    def get_possible_camps(self):
        """
        LG: returns a dict of all possible camps based on selected biome and social
        """
        # this dict makes tab generation waaaaay easier
        # even if the dict itself is pretty uggo
        if self.social == CatSocial.CLANCAT:
            camp_dict = {
                "Forest": {
                    "1": {"camp_name": "camp_classic", "button_width": 85},
                    "2": {"camp_name": "camp_gully", "button_width": 70},
                    "3": {"camp_name": "camp_grotto", "button_width": 85},
                    "4": {"camp_name": "camp_lakeside", "button_width": 100},
                    "5": {"camp_name": "camp_pine", "button_width": 100},
                    "6": {"camp_name": "camp_birch", "button_width": 85}
                },
                "Mountainous": {
                    "1": {"camp_name": "camp_cliff", "button_width": 70},
                    "2": {"camp_name": "camp_cavern", "button_width": 90},
                    "3": {"camp_name": "camp_crystal_river", "button_width": 130},
                    "4": {"camp_name": "camp_rocky_slope", "button_width": 135},
                    "5": {"camp_name": "camp_quarry", "button_width": 85},
                    "6": {"camp_name": "camp_ruins", "button_width": 85}
                },
                "Plains": {
                    "1": {"camp_name": "camp_grasslands", "button_width": 115},
                    "2": {"camp_name": "camp_tunnels", "button_width": 90},
                    "3": {"camp_name": "camp_wastelands", "button_width": 115},
                    "4": {"camp_name": "camp_taiga", "button_width": 100},
                    "5": {"camp_name": "camp_desert", "button_width": 100},
                    "6": {"camp_name": "camp_city", "button_width": 85},
                    "7": {"camp_name": "camp_farm", "button_width": 85},
                    "8": {"camp_name": "camp_bushland", "button_width": 105},
                    "9": {"camp_name": "camp_castle", "button_width": 95},
                    "10": {"camp_name": "camp_bridge", "button_width": 85}
                },
                "Beach": {
                    "1": {"camp_name": "camp_tidepools", "button_width": 110},
                    "2": {"camp_name": "camp_tidal_cave", "button_width": 110},
                    "3": {"camp_name": "camp_shipwreck", "button_width": 110},
                    "4": {"camp_name": "camp_fjord", "button_width": 80},
                    "5": {"camp_name": "camp_tropical_island", "button_width": 140},
                    "6": {"camp_name": "camp_quay", "button_width": 75},
                }
            }
        elif self.social == CatSocial.ROGUE:
            camp_dict = {
                "Forest": {
                    "1": {"camp_name": "rogue_forest", "button_width": 110}
                },
                "Mountainous": {
                    "1": {"camp_name": "rogue_mountainous", "button_width": 110}
                },
                "Plains": {
                    "1": {"camp_name": "rogue_plains", "button_width": 110}
                },
                "Beach": {
                    "1": {"camp_name": "rogue_beach", "button_width": 110}
                }
            }
        elif self.social == CatSocial.LONER:
            camp_dict = {
                "Forest": {
                    "1": {"camp_name": "loner_forest", "button_width": 110}
                },
                "Mountainous": {
                    "1": {"camp_name": "loner_mountainous", "button_width": 110}
                },
                "Plains": {
                    "1": {"camp_name": "loner_plains", "button_width": 110}
                },
                "Beach": {
                    "1": {"camp_name": "loner_beach", "button_width": 110}
                }
            }
        elif self.social == CatSocial.KITTYPET:
            camp_dict = {
                "Forest": {
                    "1": {"camp_name": "household_forest", "button_width": 110}
                },
                "Mountainous": {
                    "1": {"camp_name": "household_mountainous", "button_width": 110}
                },
                "Plains": {
                    "1": {"camp_name": "household_plains", "button_width": 110}
                },
                "Beach": {
                    "1": {"camp_name": "household_beach", "button_width": 110}
                }
            }
        else:
            camp_dict = {
                "Forest": {
                    "1": {"camp_name": "no_group_forest", "button_width": 110}
                },
                "Mountainous": {
                    "1": {"camp_name": "no_group_mountainous", "button_width": 110}
                },
                "Plains": {
                    "1": {"camp_name": "no_group_plains", "button_width": 110}
                },
                "Beach": {
                    "1": {"camp_name": "no_group_beach", "button_width": 110}
                }
            }
        return camp_dict

    def get_camp_bg(self, src=None):
        if src is None:
            src = pygame.image.load(
                self.get_camp_art_path(self.selected_camp_tab)
            ).convert_alpha()

        name = "_".join(
            [
                str(self.biome_selected),
                str(self.selected_camp_tab),
                self.selected_season,
            ]
        )
        if name not in self.game_bgs:
            self.game_bgs[
                name
            ] = scripts.screens.screens_core.screens_core.default_game_bgs[self.theme][
                "default"
            ]
            self.fullscreen_bgs[
                name
            ] = scripts.screens.screens_core.screens_core.process_blur_bg(src)

        self.set_bg(name)

    def refresh_selected_cat_info(self, selected: Optional[Cat] = None):
        # SELECTED CAT INFO
        if selected is None:
            # self.elements["next_step"].disable()
            self.elements["cat_info"].hide()
            self.elements["cat_name"].hide()
            return

        if self.sub_screen == "choose leader" and not game_setting_get("no special suffixes"):
            self.elements["cat_name"].set_text(
                str(selected.name)
            )
        else:
            self.elements["cat_name"].set_text(str(selected.name))
        self.elements["select_cat"].set_text(
            self.elements["select_cat"].text, text_kwargs={"m_c": selected}
        )
        self.elements["cat_name"].show()
        self.elements["cat_info"].set_text(
            selected.get_info_block(make_clan=True), text_kwargs={"m_c": selected}
        )
        self.elements["cat_info"].show()

    def refresh_cat_images_and_info(self, selected=None):
        """Update the image of the cat selected in the middle. Info and image.
        Also updates the location of selected cats."""

        column_poss = [50, 100]

        # updates selected cat info
        self.refresh_selected_cat_info(selected)

        # CAT IMAGES
        for u in range(6):
            if "cat" + str(u) in self.elements:
                self.elements["cat" + str(u)].kill()
            if game.choose_cats[u] == selected:
                self.elements["cat" + str(u)] = self.elements[
                    "cat" + str(u)
                ] = UISpriteButton(
                    ui_scale(pygame.Rect((270, 200), (150, 150))),
                    pygame.transform.scale(
                        game.choose_cats[u].sprite, ui_scale_dimensions((150, 150))
                    ),
                    cat_object=game.choose_cats[u],
                    object_id="#offspring_predict_cat",
                    tool_tip_text=selected.create_genelist(),
                    manager=MANAGER,
                )
            else:
                self.elements[
                    "cat" + str(u)
                    ] = UISpriteButton(
                        ui_scale(pygame.Rect((column_poss[0], 130 + 50 * u), (50, 50))),
                        pygame.transform.scale(
                            game.choose_cats[u].sprite, ui_scale_dimensions((150, 150))
                        ),
                        cat_object=game.choose_cats[u], manager=MANAGER
                        )
        for u in range(6, 12):
            if "cat" + str(u) in self.elements:
                self.elements["cat" + str(u)].kill()
            if game.choose_cats[u] == selected:
                self.elements[
                    "cat" + str(u)
                    ] = self.elements[
                        "cat" + str(u)
                        ] = UISpriteButton(
                            ui_scale(pygame.Rect((270, 200), (150, 150))),
                            pygame.transform.scale(
                                game.choose_cats[u].sprite, ui_scale_dimensions((150, 150))
                            ),
                            cat_object=game.choose_cats[u],
                            object_id="#offspring_predict_cat",
                            tool_tip_text=game.choose_cats[u].create_genelist(),
                            manager=MANAGER
                            )
            else:
                self.elements[
                    "cat" + str(u)
                        ] = UISpriteButton(
                            ui_scale(
                                pygame.Rect((column_poss[1], 130 + 50 * (u - 6)), (50, 50))
                            ),
                            pygame.transform.scale(
                                game.choose_cats[u].sprite, ui_scale_dimensions((150, 150))
                            ),
                            cat_object=game.choose_cats[u], manager=MANAGER
                            )

    def random_clan_name(self):
        clan_names = (
            names.names_dict["normal_prefixes"] + names.names_dict["clan_prefixes"]
        )
        while True:
            chosen_name = choice(clan_names)
            if chosen_name.casefold() not in (
                clan.casefold() for clan in switch_get_value(Switch.clan_list)
            ):
                return chosen_name
            print("Generated clan name was already in use! Rerolling...")

    def random_biome_selection(self):
        # Select a random biome and background
        old_biome = self.biome_selected
        possible_biomes = ["Forest", "Mountainous", "Plains", "Beach"]
        # ensuring that the new random camp will not be the same one
        if old_biome is not None:
            possible_biomes.remove(old_biome)
        chosen_biome = choice(possible_biomes)
        return chosen_biome

    def _get_cat_tooltip_string(self, cat: Cat):
        """Get tooltip for cat. Tooltip displays name, sex, age group, and trait."""

        return f"<b>{cat.name}</b><br>{cat.genderalign_string}<br>{i18n.t('general.' + cat.age, count=1)}<br>{i18n.t('cat.personality.' + cat.personality.trait)}<br>{cat.skills.skill_string(short=True)}"

    def open_name_cat(self):
        # Clear previous screen
        self.clear_all_page()
        self.sub_screen = "choose name"
        
        self.elements["leader_image"] = pygame_gui.elements.UIImage(ui_scale(pygame.Rect((290, 150), (200, 200))),
                                                                    pygame.transform.scale(
                                                                        self.your_cat.sprite,
                                                                        (200, 200)), manager=MANAGER)

        self.elements['text1'] = pygame_gui.elements.UIImage(ui_scale(pygame.Rect((220, 365), (393, 26))),
                                                                  MakeClanScreen.your_name_txt1, manager=MANAGER)
        self.elements['text2'] = pygame_gui.elements.UIImage(ui_scale(pygame.Rect((270, 400), (267, 26))),
                                                                  MakeClanScreen.your_name_txt2, manager=MANAGER)
        # self.elements['background'].disable()

        self.elements["random"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((285, 447), (34, 34))),
            Icon.DICE,
            get_button_dict(ButtonStyles.ICON, (34, 34)),
            object_id="@buttonstyles_icon",
            manager=MANAGER,
            sound_id="dice_roll",
        )

        self.elements["error"] = pygame_gui.elements.UITextBox(
            "",
            ui_scale(pygame.Rect((0, 700), (596, -1))),
            manager=MANAGER,
            object_id="#default_dark",
            visible=False,
            anchors={"centerx": "centerx"}
        )

        self.elements["previous_step"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((253, 620), (147, 30))),
            "buttons.previous_step",
            get_button_dict(ButtonStyles.MENU_LEFT, (147, 30)),
            object_id="@buttonstyles_menu_left",
            manager=MANAGER,
            starting_height=2,
        )
        self.elements["next_step"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((0, 620), (147, 30))),
            "buttons.next_step",
            get_button_dict(ButtonStyles.MENU_RIGHT, (147, 30)),
            object_id="@buttonstyles_menu_right",
            manager=MANAGER,
            starting_height=2,
            anchors={"left_target": self.elements["previous_step"]},
        )
        self.elements["name_entry"] = pygame_gui.elements.UITextEntryLine(ui_scale(pygame.Rect((325, 450), (140, 30)))
                                                                          , manager=MANAGER, initial_text=self.your_cat.name.prefix)
        self.elements["name_entry"].set_allowed_characters(
            list("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_- "))
        self.elements["name_entry"].set_text_length_limit(11)

        if self.social == CatSocial.CLANCAT:
            if game_setting_get("dark mode"):
                self.elements["clan"] = pygame_gui.elements.UITextBox("-kit",
                                                                ui_scale(pygame.Rect((435, 452), (100, 25))),
                                                                object_id="#text_box_30_horizcenter_light",
                                                                manager=MANAGER)
            
            else:
                self.elements["clan"] = pygame_gui.elements.UITextBox("-kit",
                                                                ui_scale(pygame.Rect((435, 452), (100, 25))),
                                                                object_id="#text_box_30_horizcenter",
                                                                manager=MANAGER)
        


    def open_clan_count(self):
        
        # Clear previous screen
        self.clear_all_page()
        self.sub_screen = "clan count mode"

        text_box = image_cache.load_image(
            "resources/images/game_mode_text_box.png"
        ).convert_alpha()

        self.elements["game_mode_background"] = pygame_gui.elements.UIImage(
            ui_scale(pygame.Rect((325, 130), (399, 461))),
            pygame.transform.scale(text_box, ui_scale_dimensions((399, 461))),
            manager=MANAGER,
        )
        self.elements["permi_warning"] = pygame_gui.elements.UITextBox(
            "screens.make_clan.clan_count_warning",
            ui_scale(pygame.Rect((100, 581), (600, 40))),
            object_id=get_text_box_theme("#text_box_30_horizcenter"),
            manager=MANAGER,
        )

        # Create all the elements.

        self.elements["singleclan_mode_button"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((109, 240), (132, 30))),
            "screens.make_clan.singleclan_label",
            get_button_dict(ButtonStyles.SQUOVAL, (132, 30)),
            object_id="@buttonstyles_squoval",
            manager=MANAGER,
        )
        # plain text button like the single clan one, the old image had "expanded mode" drawn on it
        self.elements["multiclan_mode_button"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((109, 320), (132, 30))),
            "screens.make_clan.multiclan_label",
            get_button_dict(ButtonStyles.SQUOVAL, (132, 30)),
            object_id="@buttonstyles_squoval",
            manager=MANAGER,
        )
        self.elements["previous_step"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((253, 620), (147, 30))),
            "buttons.previous_step",
            get_button_dict(ButtonStyles.MENU_LEFT, (147, 30)),
            object_id="@buttonstyles_menu_left",
            manager=MANAGER,
            starting_height=2,
        )
        self.elements["previous_step"].disable()
        self.elements["next_step"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((0, 620), (147, 30))),
            "buttons.next_step",
            get_button_dict(ButtonStyles.MENU_RIGHT, (147, 30)),
            object_id="@buttonstyles_menu_right",
            manager=MANAGER,
            starting_height=2,
            anchors={"left_target": self.elements["previous_step"]},
        )
        self.elements["mode_details"] = pygame_gui.elements.UITextBox(
            "",
            ui_scale(pygame.Rect((325, 160), (405, 461))),
            object_id="#text_box_30_horizleft_pad_40_40",
            manager=MANAGER,
        )
        self.elements["mode_details"].padding = (40, 40)

        self.elements["mode_name"] = pygame_gui.elements.UITextBox(
            "",
            ui_scale(pygame.Rect((425, 135), (200, 27))),
            object_id="#text_box_30_horizcenter_light",
            manager=MANAGER,
        )

        self.refresh_text_and_buttons()

    def open_name_clan(self):
        """Opens the name Clan screen"""
        self.clear_all_page()
        self.sub_screen = "name clan"

        # Create all the elements.
        self.elements["random"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((224, 595), (34, 34))),
            Icon.DICE,
            get_button_dict(ButtonStyles.ICON, (34, 34)),
            object_id="@buttonstyles_icon",
            manager=MANAGER,
            sound_id="dice_roll",
        )

        self.elements["error"] = pygame_gui.elements.UITextBox(
            "",
            ui_scale(pygame.Rect((0, 700), (596, -1))),
            manager=MANAGER,
            object_id="#default_dark",
            visible=False,
            anchors={"centerx": "centerx"}
        )

        self.elements["previous_step"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((253, 635), (147, 30))),
            "buttons.previous_step",
            get_button_dict(ButtonStyles.MENU_LEFT, (147, 30)),
            object_id="@buttonstyles_menu_left",
            manager=MANAGER,
            starting_height=2
        )
        self.elements["next_step"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((0, 635), (147, 30))),
            "buttons.next_step",
            get_button_dict(ButtonStyles.MENU_RIGHT, (147, 30)),
            object_id="@buttonstyles_menu_right",
            manager=MANAGER,
            starting_height=2,
            anchors={"left_target": self.elements["previous_step"]},
        )
        self.elements["next_step"].disable()
        self.elements["name_entry"] = pygame_gui.elements.UITextEntryLine(
            ui_scale(pygame.Rect((265, 597), (140, 29))),
            manager=MANAGER,
        )
        self.elements["name_entry"].set_forbidden_characters("forbidden_file_path")
        self.elements["name_entry"].set_text_length_limit(11)

        self.elements["clan"] = pygame_gui.elements.UITextBox(
            "-Clan",
            ui_scale(pygame.Rect((375, 600), (100, 25))),
            object_id="#text_box_30_horizcenter_light",
            manager=MANAGER,
        )
        self.elements["reset_name"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((455, 595), (134, 30))),
            "screens.make_clan.reset_name",
            get_button_dict(ButtonStyles.SQUOVAL, (134, 30)),
            object_id="@buttonstyles_squoval",
            manager=MANAGER,
        )

        self.elements["clan_size"] = pygame_gui.elements.UITextBox(
            "This Clan will be... ",
            ui_scale(pygame.Rect((200, 100), (405, 25))),
            object_id=get_text_box_theme("#text_box_30_horizcenter"),
            manager=MANAGER
            )

        self.elements["small"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((220, 160), (100, 30))),
            "Small",
            get_button_dict(ButtonStyles.SQUOVAL, (100, 30)),
            object_id="@buttonstyles_squoval",
            manager=MANAGER
        )
        self.elements["title"] = pygame_gui.elements.UITextBox(
            "screens.make_clan.name_clan_title",
            ui_scale(pygame.Rect((0, 525), (300, 40))),
            object_id="@clangen_32",
            anchors={"centerx": "centerx"},
        )
        self.elements["subtitle"] = pygame_gui.elements.UITextBox(
            "screens.make_clan.name_clan_subtitle",
            ui_scale(pygame.Rect((0, -5), (300, 30))),
            object_id="@buttonstyles_rounded_rect",
            anchors={"centerx": "centerx", "top_target": self.elements["title"]},
        )

        self.elements["medium"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((350, 160), (100, 30))),
            "Medium",
            get_button_dict(ButtonStyles.SQUOVAL, (100, 30)),
            object_id="@buttonstyles_squoval",
            manager=MANAGER
        )

        self.elements["large"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((480, 160), (100, 30))),
            "Large",
            get_button_dict(ButtonStyles.SQUOVAL, (100, 30)),
            object_id="@buttonstyles_squoval",
            manager=MANAGER
        )

        self.elements["medium"].disable()

        self.elements["established"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((295, 200), (80, 30))),
            "Old",
            get_button_dict(ButtonStyles.SQUOVAL, (80, 30)),
            object_id="@buttonstyles_squoval",
            tool_tip_text="The Clan has existed for many moons and cats' backstories will reflect this.",
            manager=MANAGER
        )
        self.elements["new"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((425, 200), (80, 30))),
            "New",
            get_button_dict(ButtonStyles.SQUOVAL, (80, 30)),
            object_id="@buttonstyles_squoval",
            tool_tip_text="The Clan is newly established and cats' backstories will reflect this.",
            manager=MANAGER
        )
        self.elements["established"].disable()

    def clan_name_header(self):
        self.elements["name_backdrop"] = pygame_gui.elements.UIImage(
            ui_scale(pygame.Rect((292, 100), (216, 50))),
            self.clan_frame_img,
            manager=MANAGER,
        )
        self.elements["clan_name"] = pygame_gui.elements.UITextBox(
            "general.clan",
            ui_scale(pygame.Rect((292, 100), (216, 50))),
            object_id=ObjectID("#text_box_30_horizcenter_vertcenter", "#dark"),
            text_kwargs={"name": self.clan_name},
            manager=MANAGER,
        )

    def open_choose_leader(self):
        """Set up the screen for the choose leader phase."""
        self.clear_all_page()
        self.sub_screen = "choose leader"

        self.elements["background"] = pygame_gui.elements.UIImage(
            ui_scale(pygame.Rect((0, 414), (800, 286))),
            self.leader_img,
            manager=MANAGER,
        )

        self.elements["background"].disable()
        self.clan_name_header()

        self.elements["title"] = pygame_gui.elements.UITextBox(
            "screens.make_clan.your_cat_title",
            ui_scale(pygame.Rect((0, 610), (800, 90))),
            object_id="@clangen_32",
            anchors={"centerx": "centerx"},
        )

        # Roll_buttons
        x_pos = 155
        y_pos = 235
        self.elements["roll1"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((x_pos, y_pos), (34, 34))),
            Icon.DICE,
            get_button_dict(ButtonStyles.ICON, (34, 34)),
            object_id="@buttonstyles_icon",
            manager=MANAGER,
            sound_id="dice_roll",
        )
        y_pos += 40
        self.elements["roll2"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((x_pos, y_pos), (34, 34))),
            Icon.DICE,
            get_button_dict(ButtonStyles.ICON, (34, 34)),
            object_id="@buttonstyles_icon",
            manager=MANAGER,
            sound_id="dice_roll",
        )
        y_pos += 40
        self.elements["roll3"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((x_pos, y_pos), (34, 34))),
            Icon.DICE,
            get_button_dict(ButtonStyles.ICON, (34, 34)),
            object_id="@buttonstyles_icon",
            manager=MANAGER,
            sound_id="dice_roll",
        )

        _tmp = 80
        if self.rolls_left == -1:
            _tmp += 5
        self.elements["dice"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((_tmp, 435), (34, 34))),
            Icon.DICE,
            get_button_dict(ButtonStyles.ICON, (34, 34)),
            object_id="@buttonstyles_icon",
            manager=MANAGER,
            sound_id="dice_roll",
        )
        del _tmp
        self.elements["reroll_count"] = pygame_gui.elements.UILabel(
            ui_scale(pygame.Rect((100, 440), (50, 25))),
            str(self.rolls_left),
            object_id=get_text_box_theme(""),
            manager=MANAGER,
        )

        if constants.CONFIG["clan_creation"]["rerolls"] == 3:
            if self.rolls_left <= 2:
                self.elements["roll1"].disable()
            if self.rolls_left <= 1:
                self.elements["roll2"].disable()
            if self.rolls_left == 0:
                self.elements["roll3"].disable()
            self.elements["dice"].hide()
            self.elements["reroll_count"].hide()
        else:
            if self.rolls_left == 0:
                self.elements["dice"].disable()
            elif self.rolls_left == -1:
                self.elements["reroll_count"].hide()
            self.elements["roll1"].hide()
            self.elements["roll2"].hide()
            self.elements["roll3"].hide()

        self.create_cat_info()

        self.elements['select_cat'] = UISurfaceImageButton(
            ui_scale(pygame.Rect((353, 360), (95, 30))),
            "select",
            get_button_dict(ButtonStyles.SQUOVAL, (95, 30)),
            manager=MANAGER,
            object_id="@buttonstyles_squoval",
            starting_height=1,
        )
        self.elements['select_cat'].hide()
        
        # Next and previous buttons
        self.elements["previous_step"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((253, 400), (147, 30))),
            "buttons.previous_step",
            get_button_dict(ButtonStyles.MENU_LEFT, (147, 30)),
            object_id="@buttonstyles_menu_left",
            manager=MANAGER,
            starting_height=2
        )
        self.elements["next_step"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((0, 400), (147, 30))),
            "buttons.next_step",
            get_button_dict(ButtonStyles.MENU_RIGHT, (147, 30)),
            object_id="@buttonstyles_menu_right",
            manager=MANAGER,
            starting_height=2,
            anchors={"left_target": self.elements["previous_step"]},
        )
        self.elements['next_step'].disable()
        
        # CHECKMERGE lang file
        self.elements["customize"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((50, 100), (118, 30))),
            "customize",
            get_button_dict(ButtonStyles.SQUOVAL, (118, 30)),
            object_id="@buttonstyles_squoval",
            manager=MANAGER,
            starting_height=2,
            tool_tip_text = "Customize your own cat"
        )

        self.elements["start_as"] = pygame_gui.elements.UITextBox(
            "Start as a... ",
            ui_scale(pygame.Rect((550, 150), (405, 25))),
            object_id=get_text_box_theme("#text_box_30_horizcenter"),
            manager=MANAGER
            )

        self.elements["clancat"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((700, 200), (118, 30))),
            "clancat",
            get_button_dict(ButtonStyles.SQUOVAL, (118, 30)),
            object_id="@buttonstyles_squoval",
            manager=MANAGER,
            starting_height=2,
            tool_tip_text="Start out as a Clan cat"
        )
        self.elements["clancat"].disable()
        self.elements["kittypet"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((700, 250), (118, 30))),
            "kittypet",
            get_button_dict(ButtonStyles.SQUOVAL, (118, 30)),
            object_id="@buttonstyles_squoval",
            manager=MANAGER,
            starting_height=2,
            tool_tip_text="Live comfortably with your housefolk"
        )
        self.elements["loner"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((700, 300), (118, 30))),
            "loner",
            get_button_dict(ButtonStyles.SQUOVAL, (118, 30)),
            object_id="@buttonstyles_squoval",
            manager=MANAGER,
            starting_height=2,
            tool_tip_text="Wander the lands beyond Clan territories"
        )
        self.elements["rogue"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((700, 350), (118, 30))),
            "rogue",
            get_button_dict(ButtonStyles.SQUOVAL, (118, 30)),
            object_id="@buttonstyles_squoval",
            manager=MANAGER,
            starting_height=2,
            tool_tip_text="Survive by your claws, owing loyalty to no one"
        )
        
        # TEMP LIFEGEN: hide group buttons for now
        self.elements["start_as"].hide()
        self.elements["clancat"].hide()
        self.elements["kittypet"].hide()
        self.elements["loner"].hide()
        self.elements["rogue"].hide()

        # draw cats to choose from
        self.refresh_cat_images_and_info()
    
    def randomize_custom_cat(self):
        permanent_conditions = ['born without a leg', 'weak leg', 'twisted leg', 'born without a tail', 'paralyzed', 'raspy lungs', 'wasting disease', 'blind', 'one bad eye', 'failing eyesight', 'partial hearing loss', 'deaf', 'constant joint pain', 'seizure prone', 'allergies', 'persistent headaches']

        self.custom_cat = Cat()

        pelt_options = []
        for category in LegacyPelt.pelt_categories:
            if category == "torties":
                continue
            pelt_options += LegacyPelt.pelt_categories[category]
        pelt_options.remove("TwoColour")
        
        random_pelt_name = choice(pelt_options)

        random_pelt_colour = choice(LegacyPelt.all_pelt_colours)
        random_pelt_length = choice(["short", "medium", "long"])
        random_white_patches = choice(["FULLWHITE"] + LegacyPelt.little_white + LegacyPelt.mid_white + LegacyPelt.high_white + LegacyPelt.mostly_white) if random.randint(1,8) != 1 else None
        random_eye_colour = choice(LegacyPelt.all_eye_colours)
        random_eye_colour2 = choice(LegacyPelt.all_eye_colours) if not int(random.random() * 10) else None

        tortie = True if random.randint(1,5) == 1 else False
        random_tortie_base = choice(LegacyPelt.pelt_patterns) if tortie else None
        random_tortie_colour = choice(LegacyPelt.all_pelt_colours) if tortie else None
        random_tortie_markings = choice(LegacyPelt.tortie_patches) if tortie else None
        random_tortie_pattern = choice(LegacyPelt.pelt_patterns) if tortie else None

        if tortie:
            random_pelt_name = "Tortie"
        
        random_vitiligo = choice(LegacyPelt.vitiligo_markings) if random.randint(1,20) == 1 else None
        random_points = choice(LegacyPelt.point_markings) if random.randint(1,5) == 1 else None

        random_scars = [choice(LegacyPelt.all_scars)] if random.randint(1,10) == 1 else []

        random_tint = choice(["pink", "gray", "red", "orange", "black", "yellow", "purple", "blue", "dilute","warmdilute","cooldilute"]) if random.randint(1, 4) != 1 else None
        random_white_patches_tint=choice(["offwhite", "cream", "darkcream", "gray", "pink"]) if random.randint(1,5) == 1 else None
        
        random_skin = choice(LegacyPelt.skin_sprites)
        random_reverse = choice([True, False])
        

        random_accessory = [
            choice(self.all_accs)] if random.randint(1,5) == 1 else []
        
        self.newborn_pose=random.randint(0,2)
        self.kitten_sprite=random.randint(0,2)
        self.adolescent_pose = random.randint(0,2)
        self.adult_pose = random.randint(0,2)
        self.elder_pose = random.randint(0,2)
        
        random_cat_pelt = LegacyPelt(
            name=random_pelt_name,
            colour=random_pelt_colour,
            length=random_pelt_length,
            white_patches=random_white_patches,
            eye_color=random_eye_colour,
            eye_colour2=random_eye_colour2,
            tortie_base=random_tortie_base,
            tortie_colour=random_tortie_colour,
            tortie_marking=random_tortie_markings,
            tortie_pattern=random_tortie_pattern,
            vitiligo=random_vitiligo,
            points=random_points,
            reverse=random_reverse,
            accessory=random_accessory,
            inventory=random_accessory,
            tint=random_tint,
            white_patches_tint=random_white_patches_tint,
            scars=random_scars,
            skin=random_skin,
            newborn_sprite="newborn" + str(self.newborn_pose),
            kitten_sprite="kitten" + str(self.kitten_sprite),
            # adol_sprite="adolescent" + str(self.adolescent_pose),
            adol_sprite=(
                ("adolescent_short" + str(self.adolescent_pose))
                if random_pelt_length != "long"
                else 
                ("adolescent_long" + str(self.adolescent_pose))),
            adult_sprite=(
                ("adult_short" + str(self.adult_pose))
                if random_pelt_length != "long"
                else 
                ("adult_long" + str(self.adult_pose))),
            senior_sprite="senior" + str(self.elder_pose),
            para_adult_sprite= "para_adult_long0" if random_pelt_length == "long" else "para_adult_short0",
        )

        random_cat_pelt.apply_to_cat(self.custom_cat)

        # now non-pelt stuff
        self.skill = "Random"
        self.personality = choice(
            [
                'unruly','shy','impulsive','bullying',
                'attention-seeker','daydreamer','charming',
                'fearless','skittish','quiet','self-conscious',
                'know-it-all','sweet','polite','bossy',
                'noisy','smug','secretive','grumpy',
                'manipulative','leader-like',
                'passionate','disciplined',
                'patient','rebellious','honest'
            ]
        )
        self.permanent_condition = choice(permanent_conditions) if random.randint(1,30) == 1 else None
        self.custom_cat.gender = random.choice(["male", "female"])

        if self.permanent_condition == "born without a tail":
            for i in Pelt.tail_accessories:
                if i in self.custom_cat.legacy_pelt.accessory:
                    self.custom_cat.legacy_pelt.accessory = []
                    self.custom_cat.legacy_pelt.inventory = []
                    break
        if self.permanent_condition == "born without a leg":
            for i in Pelt.paw_accessories:
                if i in self.custom_cat.legacy_pelt.accessory:
                    self.custom_cat.legacy_pelt.accessory = []
                    self.custom_cat.legacy_pelt.inventory = []
                    break

        # scars for conditions
        self.custom_cat.legacy_pelt.paralyzed = True if self.permanent_condition == "paralyzed" else False
        if self.permanent_condition == "born without a tail":
            self.custom_cat.legacy_pelt.scars = ("NOTAIL",)
        elif self.permanent_condition == "born without a leg":
            self.custom_cat.legacy_pelt.scars = ("NOPAW",)
        elif self.permanent_condition == "blind":
            if random.randint(0,10) == 1:
                self.custom_cat.legacy_pelt.scars = ["BOTHBLIND"]
        elif self.permanent_condition == "one bad eye":
            if random.randint(0,10) == 1:
                self.custom_cat.legacy_pelt.scars = (random.choice(["LEFTBLIND", "RIGHTBLIND", "BRIGHTHEART"]),)
        elif self.permanent_condition in ["deaf", "partial hearing loss"]:
            if random.randint(0,10) == 1:
                self.custom_cat.legacy_pelt.scars = (random.choice(["LEFTEAR", "RIGHTEAR", "NOEAR"]),)

        self.faith = random.choice(["flexible", "starclan", "dark forest", "neutral"])

        if tortie:
            self.tortie_enabled = True
        else:
            self.tortie_enabled = False

    def open_customize_cat(self):

        self.clear_all_page()
        self.sub_screen = "customize cat"

        # self.selected_cat = None
        # clearing selected cat for the eye colour display bug


        # genes cant be turned back into lifegen pelt picks, so customizing always starts
        # from a plain pelt even if one of the random cats was selected
        if True:
            pelt2 = LegacyPelt(
                name="SingleColour",
                length="short",
                colour="WHITE",
                white_patches=None,
                eye_color="BLUE",
                eye_colour2=None,
                tortie_base=None,
                tortie_colour=None,
                tortie_marking=None,
                tortie_pattern=None,
                vitiligo=None,
                points=None,
                accessory=[],
                inventory=[],
                paralyzed=False,
                scars=[],
                tint="pink",
                skin="PINK",
                white_patches_tint="cream",
                kitten_sprite=self.kitten_sprite,
                adol_sprite=self.adolescent_pose,
                adult_sprite=self.adult_pose,
                senior_sprite=self.elder_pose,
                para_adult_sprite= "para_adult_short0",
                reverse=False,
            )
            # CHECKCUSTOM make it an empty pelt

        # CREATE CUSTOM CAT
        self.custom_cat = Cat(moons=0)
        pelt2.apply_to_cat(self.custom_cat)

        if self.custom_cat.legacy_pelt.name in ["Tortie", "Calico"]:
            self.tortie_enabled = True
        else:
            self.tortie_enabled = False
        
        self.update_custom_cat_pages()
        self.update_disabled_buttons()
    
    def get_acc_name(self, acc):
        """ grabs accessory names for display in the customiser """
        acc_name = str(i18n.t(f"cat.accessories.{acc}", count=1)).capitalize()
        collar_found = False
        if acc in Pelt.collar_accessories:
            for style_type in sprites.COLLAR_DATA["style_data"]:
                for style, color_list in style_type.items():
                    for colour in color_list:
                        if f"{style}_{colour}" == acc:
                            collar_found = True
                            # "colorful" gets to stay so we dont end up with
                            # "rainbow colorful spiked leather collar"
                            # thats just a mouthful
                            if "colorful" in acc:
                                acc_name = str(i18n.t(f"cat.accessories.{style}", count=1)).capitalize()
                            else:
                                acc_name = str(colour.replace("_", " ") + " " + i18n.t(f"cat.accessories.{style}", count=1)).capitalize()
                            break
                        if collar_found:
                            break
                    if collar_found:
                        break
                if collar_found:
                    break

                # wtaf

        return acc_name

    def update_custom_cat_pages(self):
        self.clear_all_page()

        pelt_options = []
        for category in LegacyPelt.pelt_categories:
            if category == "torties":
                continue
            pelt_options += LegacyPelt.pelt_categories[category]
        pelt_options.remove("TwoColour")

        permanent_conditions = ['born without a leg', 'weak leg', 'twisted leg', 'born without a tail', 'paralyzed', 'raspy lungs', 'wasting disease', 'blind', 'one bad eye', 'failing eyesight', 'partial hearing loss', 'deaf', 'constant joint pain', 'seizure prone', 'allergies', 'persistent headaches']

        # UI
        self.elements["left"] = UIImageButton(ui_scale(pygame.Rect((17, 310), (51, 67))), "", object_id="#arrow_right_fancy",
                                                 starting_height=2)
        
        self.elements["right"] = UIImageButton(ui_scale(pygame.Rect((730, 310), (51, 67))), "", object_id="#arrow_left_fancy",
                                             starting_height=2)
        if self.page == 0:
            self.elements['left'].disable()
        else:
            self.elements['left'].enable()
        
        if self.page == 3:
            self.elements['right'].disable()
        else:
            self.elements['right'].enable()

        self.elements['random_customize'] = UISurfaceImageButton(
            ui_scale(pygame.Rect((327, 80), (150, 30))),
            Icon.DICE + " Random cat",
            get_button_dict(ButtonStyles.SQUOVAL, (150, 30)),
            object_id="@buttonstyles_squoval",
            manager=MANAGER,
            starting_height=2,
            sound_id="dice_roll",
        )


        # Sprite Background
        if game_setting_get("dark mode"):
            self.elements['spritebg'] = pygame_gui.elements.UIImage(
                ui_scale(pygame.Rect((275, 125), (250, 285))),
                MakeClanScreen.sprite_preview_bg_dark,
                manager=MANAGER
                )
        else:
            self.elements['spritebg'] = pygame_gui.elements.UIImage(
                ui_scale(pygame.Rect((275, 125), (250, 285))),
                MakeClanScreen.sprite_preview_bg,
                manager=MANAGER
                )
        # -----


        # Sprite
        self.update_sprite()
        # -----
      
        self.elements['randomise_selection'] = UISurfaceImageButton(
            ui_scale(pygame.Rect((385, 425), (34, 34))),
            Icon.DICE,
            get_button_dict(ButtonStyles.ICON, (34, 34)),
            object_id="@buttonstyles_icon",
            manager=MANAGER,
            starting_height=2,
            sound_id="dice_roll",
        )

        self.elements["cycle_left"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((345, 425), (34, 34))),
            Icon.ARROW_LEFT,
            get_button_dict(ButtonStyles.ICON, (34, 34)),
            object_id="@buttonstyles_icon",
            starting_height=0,
        )

        self.elements["cycle_right"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((425, 425), (34, 34))),
            Icon.ARROW_RIGHT,
            get_button_dict(ButtonStyles.ICON, (34, 34)),
            object_id="@buttonstyles_icon",
            starting_height=0,
        )

        self.elements["previous_step"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((253, 645), (147, 30))),
            "buttons.previous_step",
            get_button_dict(ButtonStyles.MENU_LEFT, (147, 30)),
            object_id="@buttonstyles_menu_left",
            manager=MANAGER,
            starting_height=2
        )
        self.elements["next_step"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((0, 645), (147, 30))),
            "buttons.next_step",
            get_button_dict(ButtonStyles.MENU_RIGHT, (147, 30)),
            object_id="@buttonstyles_menu_right",
            manager=MANAGER,
            starting_height=2,
            anchors={"left_target": self.elements["previous_step"]},
        )

        if self.page == 0:
            # PAGE 0
            # poses

            # Preview age
            x_pos = 535
            self.elements['preview text'] = pygame_gui.elements.UITextBox(
                    'Preview Age',
                    ui_scale(pygame.Rect((x_pos, 135), (170, 34))),
                    object_id=get_text_box_theme("#text_box_30_horizcenter"), manager=MANAGER
                )
            button_count = 0
            age_y_pos = 175
            for i in ["newborn", "kitten", "adolescent", "adult", "elder"]:
                self.preview_age_buttons[i] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((x_pos, age_y_pos), (95, 34))),
                    i,
                    get_button_dict(ButtonStyles.ROUNDED_RECT, (95, 34)),
                    object_id="@buttonstyles_rounded_rect",
                    manager=MANAGER,
                    starting_height=2
                )
                x_pos += 110
                button_count += 1
                if button_count == 2:
                    button_count = 0
                    age_y_pos += 40
                    x_pos = 535
            # puts the last two buttons on the bottom so theyre not all in one line

            # fur length
            x_pos = 550
            self.elements['fur_length_text'] = pygame_gui.elements.UITextBox(
                    'Fur Length',
                    ui_scale(pygame.Rect((x_pos, 310),(170, 34))),
                    object_id=get_text_box_theme("#text_box_30_horizcenter"), manager=MANAGER
                )
            button_count = 0
            fur_y_pos = 350
            for i in ["short", "medium", "long"]:
                self.fur_length_buttons[i] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((x_pos, fur_y_pos), (75, 34))),
                    str(i),
                    get_button_dict(ButtonStyles.ROUNDED_RECT, (75, 34)),
                    object_id="@buttonstyles_rounded_rect",
                    manager=MANAGER,
                    starting_height=2
                )
                x_pos += 95
                button_count += 1
                if button_count == 2:
                    fur_y_pos += 40
                    x_pos = 600

            x_pos = 600
            self.elements['reverse text'] = pygame_gui.elements.UITextBox(
                'Reverse',
                ui_scale(pygame.Rect((550, 455),(170, 34))),
                object_id=get_text_box_theme("#text_box_30_horizcenter"),
                manager=MANAGER
                )
            for i in [True, False]:
                self.reverse_buttons[str(i)] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((x_pos, 495), (34, 34))),
                    str(i)[0],
                    get_button_dict(ButtonStyles.ICON, (34, 34)),
                    object_id="@buttonstyles_icon",
                    manager=MANAGER,
                    starting_height=2
                )
                x_pos += 40

            # Newborn poses
            x_pos = 125
            self.elements['newborn_pose_text'] = pygame_gui.elements.UITextBox(
                    'Newborn',
                    ui_scale(pygame.Rect((x_pos, 80), (115, 30))),
                    object_id=get_text_box_theme("#text_box_30_horizcenter"), manager=MANAGER
                )

            for pose in range(0,3):
                self.newborn_pose_buttons[str(pose)] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((x_pos, 115), (34, 34))),
                    str(pose),
                    get_button_dict(ButtonStyles.ICON, (34, 34)),
                    object_id="@buttonstyles_icon",
                    manager=MANAGER,
                    starting_height=2
                )
                x_pos += 40

            # Kitten poses
            x_pos = 125
            self.elements['kitten_pose_text'] = pygame_gui.elements.UITextBox(
                    'Kitten',
                    ui_scale(pygame.Rect((x_pos, 175), (115, 30))),
                    object_id=get_text_box_theme("#text_box_30_horizcenter"), manager=MANAGER
                )

            for pose in range(0,3):
                self.kitten_pose_buttons[str(pose)] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((x_pos, 210), (34, 34))),
                    str(pose),
                    get_button_dict(ButtonStyles.ICON, (34, 34)),
                    object_id="@buttonstyles_icon",
                    manager=MANAGER,
                    starting_height=2
                )
                x_pos += 40
                
            # Apprentice poses
            x_pos = 125
            self.elements['adolescent_pose_text'] = pygame_gui.elements.UITextBox(
                    'Apprentice',
                    ui_scale(pygame.Rect((x_pos, 270), (115, 30))),
                    object_id=get_text_box_theme("#text_box_30_horizcenter"),
                    manager=MANAGER
                )
            for pose in range(0,3):
                self.adolescent_pose_buttons[str(pose)] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((x_pos, 305), (34, 34))),
                    str(pose),
                    get_button_dict(ButtonStyles.ICON, (34, 34)),
                    object_id="@buttonstyles_icon",
                    manager=MANAGER,
                    starting_height=2
                )
                x_pos += 40

            x_pos = 125

            self.elements['adult_pose_text'] = pygame_gui.elements.UITextBox(
                'Adult',
                ui_scale(pygame.Rect((x_pos, 370), (115, 30))),
                object_id=get_text_box_theme("#text_box_30_horizcenter"), manager=MANAGER
            )

            for pose in range(0,3):
                self.adult_pose_buttons[str(pose)] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((x_pos, 405), (34, 34))),
                    str(pose),
                    get_button_dict(ButtonStyles.ICON, (34, 34)),
                    object_id="@buttonstyles_icon",
                    manager=MANAGER,
                    starting_height=2
                )
                x_pos += 40

            x_pos = 125
            self.elements['elder_pose_text'] = pygame_gui.elements.UITextBox(
                    'Elder',
                    ui_scale(pygame.Rect((x_pos, 470), (115, 30))),
                    object_id=get_text_box_theme("#text_box_30_horizcenter"),
                    manager=MANAGER
                )
            for pose in range(0,3):
                self.elder_pose_buttons[str(pose)] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((x_pos, 505), (34, 34))),
                    str(pose),
                    get_button_dict(ButtonStyles.ICON, (34, 34)),
                    object_id="@buttonstyles_icon",
                    manager=MANAGER,
                    starting_height=2
                )
                x_pos += 40
        
        if self.page == 1:

            if self.current_selection not in [
                "pelt_pattern", "pelt_colour", "white_patches",
                "points", "vitiligo", "tortie_pattern",
                "tortie_colour", "tortie_patches"
                ]:
                self.current_selection = "pelt_pattern"

            
            self.elements["scroll_container"] = UIModifiedScrollingContainer(
                ui_scale(pygame.Rect((550, 85), (175, 480))),
                manager=MANAGER,
                starting_height=1,
                allow_scroll_x=False,
                allow_scroll_y=True,
            )
            
            x_pos = 120
            selection_y_pos = 100
            for i in ["pelt_pattern", "pelt_colour", "white_patches", "points", "vitiligo"]:
                self.current_selection_buttons[i] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((x_pos, selection_y_pos), (120, 40))),
                    i.replace("_", " "),
                    get_button_dict(ButtonStyles.ROUNDED_RECT, (120, 40)),
                    object_id="@buttonstyles_rounded_rect",
                    manager=MANAGER,
                    starting_height=2
                )
                selection_y_pos += 50

            self.elements["tortie_text"] = pygame_gui.elements.UITextBox(
                        "Tortie",
                        ui_scale(pygame.Rect((x_pos, selection_y_pos + 10), (65, 34))),
                        object_id=get_text_box_theme("#text_box_30_horizleft"),
                        manager=MANAGER
                    )
            if self.tortie_enabled is True:
                self.elements["tortie_checkbox"] = UIImageButton(
                    ui_scale(pygame.Rect((x_pos + 60, selection_y_pos + 12), (30, 30))),
                    "",
                    object_id="@checked_checkbox",
                    manager=MANAGER
                    )
            else:
                self.elements["tortie_checkbox"] = UIImageButton(
                    ui_scale(pygame.Rect((x_pos + 60, selection_y_pos + 12), (30, 30))),
                    "",
                    object_id="@unchecked_checkbox",
                    manager=MANAGER
                    )
            
            selection_y_pos += 75
            for i in ["tortie_pattern", "tortie_colour", "tortie_patches"]:
                self.current_selection_buttons[i] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((x_pos, selection_y_pos), (120, 40))),
                    i.replace("_", " "),
                    get_button_dict(ButtonStyles.ROUNDED_RECT, (120, 40)),
                    object_id="@buttonstyles_rounded_rect",
                    manager=MANAGER,
                    starting_height=2
                )
                selection_y_pos += 50

                if self.tortie_enabled is False:
                    self.current_selection_buttons[i].disable()
                else:
                    self.current_selection_buttons[i].enable()

            x_pos = 0
            pelt_y_pos = 0
            if self.current_selection == "pelt_pattern":
                for pelt in pelt_options:
                    # pelt checkboxes
                    self.pelt_pattern_buttons[pelt] = UIImageButton(
                        ui_scale(pygame.Rect((x_pos, pelt_y_pos + 4), (34, 34))),
                        "",
                        object_id="@unchecked_checkbox",
                        container=self.elements["scroll_container"],
                        manager=MANAGER
                        )
                    # now the labels
                    self.pelt_pattern_names[pelt] = pygame_gui.elements.UITextBox(
                        str(pelt),
                        ui_scale(pygame.Rect((x_pos + 32, pelt_y_pos), (200, 34))),
                        object_id=get_text_box_theme("#text_box_30_horizleft"),
                        container=self.elements["scroll_container"],
                        manager=MANAGER
                    )
                    pelt_y_pos += 40

                self.elements["match_tortie"] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((340, 465), (123, 34))),
                    "match tortie",
                    get_button_dict(ButtonStyles.SQUOVAL, (123, 34)),
                    object_id="@buttonstyles_rounded_rect",
                    manager=MANAGER,
                    starting_height=2
                )
            elif self.current_selection == "pelt_colour":
                for colour in LegacyPelt.all_pelt_colours:
                    self.pelt_colour_buttons[colour] = UIImageButton(
                        ui_scale(pygame.Rect((x_pos, pelt_y_pos + 4), (34, 34))),
                        "",
                        object_id="@unchecked_checkbox",
                        container=self.elements["scroll_container"],
                        manager=MANAGER
                        )
                    self.pelt_colour_names[colour] = pygame_gui.elements.UITextBox(
                        str(colour).lower().capitalize(),
                        ui_scale(pygame.Rect((x_pos + 32, pelt_y_pos), (200, 34))),
                        object_id=get_text_box_theme("#text_box_30_horizleft"),
                        container=self.elements["scroll_container"],
                        manager=MANAGER
                    )
                    pelt_y_pos += 40

                tint_x_pos = 256
                tint_y_pos = 480
                for tint in [
                    None, "pink", "gray", "red", "orange", "black",
                    "yellow", "purple", "blue", "dilute", "warmdilute", "cooldilute"
                    ]:
                    if tint is None:
                        btn = "none"
                    else:
                        btn = tint
                    self.tint_buttons[tint] = UIImageButton(
                        ui_scale(pygame.Rect((tint_x_pos, tint_y_pos), (40, 40))),
                        "",
                        object_id=f"#tint_button_{btn}",
                        manager=MANAGER
                        )
                    tint_x_pos += 50
                    if tint == "black":
                        tint_y_pos += 50
                        tint_x_pos = 256

            elif self.current_selection == "white_patches":
                # search bar first
                self.elements["search_button"] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((475, 530), (34, 34))),
                    Icon.MAGNIFY,
                    get_button_dict(ButtonStyles.ICON, (34, 34)),
                    object_id="@buttonstyles_icon",
                    manager=MANAGER,
                    starting_height=2
                )
                self.elements["clear"] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((297, 530), (34, 34))),
                    "X",
                    get_button_dict(ButtonStyles.ICON, (34, 34)),
                    object_id="@buttonstyles_icon",
                    manager=MANAGER,
                    starting_height=2
                )
                self.elements["search_bar_image"] = pygame_gui.elements.UIImage(
                    ui_scale(pygame.Rect((344, 530), (118, 34))),
                    pygame.image.load("resources/images/search_bar.png").convert_alpha(),
                    manager=MANAGER
                    )
                self.elements["search_bar"] = pygame_gui.elements.UITextEntryLine(
                    ui_scale(pygame.Rect((354, 532), (102, 27))),
                    object_id="#search_entry_box",
                    initial_text=self.previous_search_text,
                    manager=MANAGER
                    )
                patch_list = LegacyPelt.little_white + LegacyPelt.mid_white + LegacyPelt.high_white + LegacyPelt.mostly_white + ["FULLWHITE"]
                if self.customiser_sort == "alphabetical":
                    patch_list.sort()

                new_patch_list = []
                searched = self.search_text
                if searched not in ["", "search"]:
                    for patch in patch_list:
                        if searched in patch.lower():
                            new_patch_list.append(patch)
                else:
                    new_patch_list = patch_list

                # now draw the buttons
                for patch in ["None"] + new_patch_list:
                    self.white_patches_buttons[patch] = UIImageButton(
                    ui_scale(pygame.Rect((x_pos, pelt_y_pos + 4), (34, 34))),
                    "",
                    object_id="@unchecked_checkbox",
                    container=self.elements["scroll_container"],
                    manager=MANAGER
                    )
                    self.white_patches_names[patch] = pygame_gui.elements.UITextBox(
                        str(patch).lower().capitalize(),
                        ui_scale(pygame.Rect((x_pos + 32, pelt_y_pos), (200, 34))),
                        object_id=get_text_box_theme("#text_box_30_horizleft"),
                        container=self.elements["scroll_container"],
                        manager=MANAGER
                    )
                    pelt_y_pos += 40
                self.elements["default"] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((560, 38), (75, 34))),
                    "Default",
                    get_button_dict(ButtonStyles.MENU_LEFT, (75, 34)),
                    object_id="@buttonstyles_menu_left",
                    manager=MANAGER,
                    starting_height=2
                )
                self.elements["alphabetical"] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((635, 38), (75, 34))),
                    "ABC",
                    get_button_dict(ButtonStyles.MENU_RIGHT, (75, 34)),
                    object_id="@buttonstyles_menu_right",
                    manager=MANAGER,
                    starting_height=2
                )

                tint_x_pos = 268
                tint_y_pos = 472
                for tint in [
                    None, "offwhite", "cream", "darkcream", "gray", "pink"
                    ]:
                    if tint is None:
                        btn = "none"
                    else:
                        btn = tint
                    self.white_patches_tint_buttons[tint] = UIImageButton(
                        ui_scale(pygame.Rect((tint_x_pos, tint_y_pos), (40, 40))),
                        "",
                        object_id=f"#tint_button_{btn}",
                        manager=MANAGER
                        )
                    tint_x_pos += 45
                    if tint == "pink":
                        tint_y_pos += 50
                        tint_x_pos = 256
                    # ^^ to make adding tint buttons a bit easier

            elif self.current_selection == "points":
                for point in ["None"] + LegacyPelt.point_markings:
                    self.points_buttons[point] = UIImageButton(
                        ui_scale(pygame.Rect((x_pos, pelt_y_pos + 4), (34, 34))),
                        "",
                        object_id="@unchecked_checkbox",
                        container=self.elements["scroll_container"],
                        manager=MANAGER
                    )
                    self.points_names[point] = pygame_gui.elements.UITextBox(
                        str(point).lower().capitalize(),
                        ui_scale(pygame.Rect((x_pos + 32, pelt_y_pos),(200, 34))),
                        object_id=get_text_box_theme("#text_box_30_horizleft"),
                        container=self.elements["scroll_container"],
                        manager=MANAGER
                    )
                    pelt_y_pos += 40
            elif self.current_selection == "vitiligo":
                for patch in ["None"] + LegacyPelt.vitiligo_markings:
                    self.vitiligo_buttons[patch] = UIImageButton(
                        ui_scale(pygame.Rect((x_pos, pelt_y_pos + 4), (34, 34))),
                        "",
                        object_id="@unchecked_checkbox",
                        container=self.elements["scroll_container"],
                        manager=MANAGER
                    )
                    self.vitiligo_names[patch] = pygame_gui.elements.UITextBox(
                        str(patch).lower().capitalize(),
                        ui_scale(pygame.Rect((x_pos + 32, pelt_y_pos),(200, 34))),
                        object_id=get_text_box_theme("#text_box_30_horizleft"),
                        container=self.elements["scroll_container"],
                        manager=MANAGER
                    )
                    pelt_y_pos += 40
            
            # TORTIES
            elif self.current_selection == "tortie_pattern":
                for pattern in LegacyPelt.pelt_patterns:
                    self.tortie_pattern_buttons[pattern] = UIImageButton(
                        ui_scale(pygame.Rect((x_pos, pelt_y_pos + 4), (34, 34))),
                        "",
                        object_id="@unchecked_checkbox",
                        container=self.elements["scroll_container"],
                        manager=MANAGER
                    )
                    string = str(pattern).lower().capitalize()
                    if string == "Singlecolour":
                        string = "SingleColour"
                    self.tortie_pattern_names[pattern] = pygame_gui.elements.UITextBox(
                        string,
                        ui_scale(pygame.Rect((x_pos + 32, pelt_y_pos), (200, 34))),
                        object_id=get_text_box_theme("#text_box_30_horizleft"),
                        container=self.elements["scroll_container"],
                        manager=MANAGER
                    )
                    pelt_y_pos += 40

                self.elements["match_base"] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((340, 465), (123, 34))),
                    "match base",
                    get_button_dict(ButtonStyles.SQUOVAL, (123, 34)),
                    object_id="@buttonstyles_rounded_rect",
                    manager=MANAGER,
                    starting_height=2
                )

            elif self.current_selection == "tortie_colour":
                for colour in LegacyPelt.all_pelt_colours:
                    self.tortie_colour_buttons[colour] = UIImageButton(
                        ui_scale(pygame.Rect((x_pos, pelt_y_pos + 4), (34, 34))),
                        "",
                        object_id="@unchecked_checkbox",
                        container=self.elements["scroll_container"],
                        manager=MANAGER
                    )
                    self.tortie_colour_names[colour] = pygame_gui.elements.UITextBox(
                        str(colour).lower().capitalize(),
                        ui_scale(pygame.Rect((x_pos + 32, pelt_y_pos), (200, 34))),
                        object_id=get_text_box_theme("#text_box_30_horizleft"),
                        container=self.elements["scroll_container"],
                        manager=MANAGER
                    )
                    pelt_y_pos += 40

            elif self.current_selection == "tortie_patches":
                for patch in LegacyPelt.tortie_patches:
                    self.tortie_patches_buttons[patch] = UIImageButton(
                        ui_scale(pygame.Rect((x_pos, pelt_y_pos + 4), (34, 34))),
                        "",
                        object_id="@unchecked_checkbox",
                        container=self.elements["scroll_container"],
                        manager=MANAGER
                        )
                    self.tortie_patches_names[patch] = pygame_gui.elements.UITextBox(
                        str(patch).lower().capitalize(),
                        ui_scale(pygame.Rect((x_pos + 32, pelt_y_pos), (200, 34))),
                        object_id=get_text_box_theme("#text_box_30_horizleft"),
                        container=self.elements["scroll_container"],
                        manager=MANAGER
                    )
                    pelt_y_pos += 40

        elif self.page == 2:

            if self.current_selection not in [
                "eye_colour", "heterochromia", "skin", "scar", "accessory"
                ]:
                self.current_selection = "eye_colour"

            self.elements["scroll_container"] = UIModifiedScrollingContainer(
                ui_scale(pygame.Rect((550, 85), (175, 480))),
                manager=MANAGER,
                starting_height=1,
                allow_scroll_x=False,
                allow_scroll_y=True,
            )

            x_pos = 120
            eye_y_pos = 0
            selection_y_pos = 150
            for i in ["eye_colour", "heterochromia", "skin", "scar", "accessory"]:
                self.current_selection_buttons[i] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((x_pos, selection_y_pos), (120, 40))),
                    i.replace("_", " "),
                    get_button_dict(ButtonStyles.ROUNDED_RECT, (120, 40)),
                    object_id="@buttonstyles_rounded_rect",
                    manager=MANAGER,
                    starting_height=2
                )
                if i == "heterochromia":
                    selection_y_pos += 60
                if i == "skin":
                    selection_y_pos += 60
                selection_y_pos += 50

            if self.current_selection == "eye_colour":
                for colour in LegacyPelt.all_eye_colours:
                    self.eye_colour_buttons[colour] = UIImageButton(
                        ui_scale(pygame.Rect((0, eye_y_pos), (34, 34))),
                        "",
                        object_id="@unchecked_checkbox",
                        container=self.elements["scroll_container"],
                        manager=MANAGER
                        )
                    self.eye_colour_names[colour] = pygame_gui.elements.UITextBox(
                        colour.capitalize(),
                        ui_scale(pygame.Rect((0 + 32, eye_y_pos), (200, 34))),
                        object_id=get_text_box_theme("#text_box_30_horizleft"),
                        container=self.elements["scroll_container"],
                        manager=MANAGER
                    )
                    eye_y_pos += 40

            elif self.current_selection == "heterochromia":
                for colour in [None] + LegacyPelt.all_eye_colours:
                    self.heterochromia_buttons[str(colour)] = UIImageButton(
                        ui_scale(pygame.Rect((0, eye_y_pos), (34, 34))),
                        "",
                        object_id="@unchecked_checkbox",
                        container=self.elements["scroll_container"],
                        manager=MANAGER
                        )
                    self.heterochromia_names[str(colour)] = pygame_gui.elements.UITextBox(
                        str(colour).capitalize(),
                        ui_scale(pygame.Rect((0 + 32, eye_y_pos), (200, 34))),
                        object_id=get_text_box_theme("#text_box_30_horizleft"),
                        container=self.elements["scroll_container"],
                        manager=MANAGER
                    )
                    eye_y_pos += 40

            elif self.current_selection == "skin":
                for colour in LegacyPelt.skin_sprites:
                    self.skin_buttons[str(colour)] = UIImageButton(
                    ui_scale(pygame.Rect((0, eye_y_pos), (34, 34))),
                    "",
                    object_id="@unchecked_checkbox",
                    container=self.elements["scroll_container"],
                    manager=MANAGER
                    )
                    self.skin_names[str(colour)] = pygame_gui.elements.UITextBox(
                        str(colour).lower().capitalize(),
                        ui_scale(pygame.Rect((0 + 32, eye_y_pos),(200, 34))),
                        object_id=get_text_box_theme("#text_box_30_horizleft"),
                        container=self.elements["scroll_container"],
                        manager=MANAGER
                    )
                    eye_y_pos += 40
            elif self.current_selection == "scar":
                for scar in ["None"] + LegacyPelt.all_scars:
                    self.scar_buttons[str(scar)] = UIImageButton(
                    ui_scale(pygame.Rect((0, eye_y_pos), (34, 34))),
                    "",
                    object_id="@unchecked_checkbox",
                    container=self.elements["scroll_container"],
                    manager=MANAGER
                    )
                    self.scar_names[str(scar)] = pygame_gui.elements.UITextBox(
                        str(scar).lower().capitalize(),
                        ui_scale(pygame.Rect((0 + 32, eye_y_pos), (200, 34))),
                        object_id=get_text_box_theme("#text_box_30_horizleft"),
                        container=self.elements["scroll_container"],
                        manager=MANAGER
                    )
                    eye_y_pos += 40
            elif self.current_selection == "accessory":

                self.elements["search_button"] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((475, 530), (34, 34))),
                    Icon.MAGNIFY,
                    get_button_dict(ButtonStyles.ICON, (34, 34)),
                    object_id="@buttonstyles_icon",
                    manager=MANAGER,
                    starting_height=2
                )
                self.elements["clear"] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((297, 530), (34, 34))),
                    "X",
                    get_button_dict(ButtonStyles.ICON, (34, 34)),
                    object_id="@buttonstyles_icon",
                    manager=MANAGER,
                    starting_height=2
                )
                self.elements["search_bar_image"] = pygame_gui.elements.UIImage(
                    ui_scale(pygame.Rect((344, 530), (118, 34))),
                    pygame.image.load("resources/images/search_bar.png").convert_alpha(),
                    manager=MANAGER
                    )
                self.elements["search_bar"] = pygame_gui.elements.UITextEntryLine(
                    ui_scale(pygame.Rect((354, 532), (102, 27))),
                    object_id="#search_entry_box",
                    initial_text=self.previous_search_text,
                    manager=MANAGER
                    )
                acc_list = (self.all_accs)
                if self.customiser_sort == "alphabetical":
                    acc_list.sort()

                new_acc_list = []
                
                searched = self.search_text
                if searched not in ["", "search"]:
                    for acc in acc_list:
                        if searched.lower() in str(self.get_acc_name(acc)) or searched in acc.lower():
                            new_acc_list.append(acc)
                else:
                    new_acc_list = acc_list

                for acc in (
                    ["None"] + new_acc_list
                    ):
                    self.accessory_buttons[acc] = UIImageButton(
                        ui_scale(pygame.Rect((0, eye_y_pos), (34, 34))),
                        "",
                        object_id="@unchecked_checkbox",
                        container=self.elements["scroll_container"],
                        manager=MANAGER
                        )

                    if acc != "None":
                        acc_name = self.get_acc_name(acc)
                        if 11 <= len(acc_name):  # check name length
                            short_name = str(acc_name)[0:9]
                            acc_name = short_name + '...'
                    else:
                        acc_name = acc
                    self.accessory_names[str(acc)] = pygame_gui.elements.UITextBox(
                        acc_name,
                        ui_scale(pygame.Rect((0 + 32, eye_y_pos),(200, 34))),
                        object_id=get_text_box_theme("#text_box_30_horizleft"),
                        container=self.elements["scroll_container"],
                        manager=MANAGER
                    )
                    eye_y_pos += 40

                self.elements["default"] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((560, 38), (75, 34))),
                    "Default",
                    get_button_dict(ButtonStyles.MENU_LEFT, (75, 34)),
                    object_id="@buttonstyles_menu_left",
                    manager=MANAGER,
                    starting_height=2
                )
                self.elements["alphabetical"] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((635, 38), (75, 34))),
                    "ABC",
                    get_button_dict(ButtonStyles.MENU_RIGHT, (75, 34)),
                    object_id="@buttonstyles_menu_right",
                    manager=MANAGER,
                    starting_height=2
                )

        elif self.page == 3:

            if self.current_selection not in [
                "condition", "trait", "skill", "faith", "sex"
                ]:
                self.current_selection = "condition"

            self.elements["scroll_container"] = UIModifiedScrollingContainer(
                ui_scale(pygame.Rect((550, 85), (175, 480))),
                manager=MANAGER,
                starting_height=1,
                allow_scroll_x=False,
                allow_scroll_y=True,
            )

            x_pos = 120
            selection_y_pos = 150
            for i in ["condition", "trait", "skill"]:
                self.current_selection_buttons[i] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((x_pos, selection_y_pos), (120, 40))),
                    i.replace("_", " "),
                    get_button_dict(ButtonStyles.ROUNDED_RECT, (120, 40)),
                    object_id="@buttonstyles_rounded_rect",
                    manager=MANAGER,
                    starting_height=2
                )
                if i == "skill":
                    selection_y_pos += 60
                if i == "faith":
                    selection_y_pos += 60
                selection_y_pos += 50

            faith_x_pos = 108
            self.elements["faith_label"] = pygame_gui.elements.UITextBox(
                    "Faith",
                    ui_scale(pygame.Rect((110, 375), (131, 25))),
                    object_id=get_text_box_theme("#text_box_30_horizcenter"),
                    manager=MANAGER
                )
            for faith in ["starclan", "neutral", "dark forest", "flexible"]:
                if faith == "starclan":
                    faith_text = "StarClan"
                elif faith == "dark forest":
                    faith_text = "Dark Forest"
                else:
                    faith_text = faith.capitalize()
                self.faith_buttons[faith] = UIImageButton(
                    ui_scale(pygame.Rect((faith_x_pos, 400), (34, 34))),
                    "",
                    object_id=f"#faith_{faith.replace(' ', '')}_button",
                    tool_tip_text=faith_text,
                    manager=MANAGER
                )
                faith_x_pos += 34

            sex_x_pos = 137
            self.elements["sex_label"] = pygame_gui.elements.UITextBox(
                    "Sex",
                    ui_scale(pygame.Rect((110, 470), (131, 25))),
                    object_id=get_text_box_theme("#text_box_30_horizcenter"),
                    manager=MANAGER
                )
            for gender in ["male", "female"]:
                self.sex_buttons[gender] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((sex_x_pos, 500), (34, 34))),
                    gender[0].upper(),
                    get_button_dict(ButtonStyles.ICON, (34, 34)),
                    object_id="@buttonstyles_icon",
                    manager=MANAGER,
                    starting_height=2
                )
                sex_x_pos += 40

            y_pos = 0
            if self.current_selection == "condition":
                for condition in ["None"] + permanent_conditions:
                    if condition != "None":
                        if 15 <= len(condition):
                            short_name = str(condition)[0:13]
                            condition_name = short_name + '...'
                        else:
                            condition_name = condition
                    else:
                        condition_name = "None"

                    self.condition_buttons[condition] = UIImageButton(
                    ui_scale(pygame.Rect((0, y_pos), (34, 34))),
                    "",
                    object_id="@unchecked_checkbox",
                    container=self.elements["scroll_container"],
                    manager=MANAGER
                    )
                    self.condition_names[condition] = pygame_gui.elements.UITextBox(
                        condition_name.capitalize(),
                        ui_scale(pygame.Rect((0 + 32, y_pos), (200, 34))),
                        object_id=get_text_box_theme("#text_box_30_horizleft"),
                        container=self.elements["scroll_container"],
                        manager=MANAGER
                    )
                    y_pos += 40

            y_pos = 0
            traits = []
            for trait in Personality.trait_ranges["kit_traits"]:
                traits.append(trait)
            traits = ['unruly','shy','impulsive','bullying','attention-seeker','daydreamer','charming','fearless','skittish','quiet','self-conscious','know-it-all','sweet','polite','bossy','noisy','smug','secretive','grumpy','manipulative','leader-like','passionate','disciplined','patient','rebellious','honest']
            if self.current_selection == "trait":
                for trait in traits:
                    if 15 <= len(trait):
                        short_name = str(trait)[0:13]
                        trait_name = short_name + '...'
                    else:
                        trait_name = trait

                    self.trait_buttons[trait] = UIImageButton(
                        ui_scale(pygame.Rect((0, y_pos), (34, 34))),
                        "",
                        object_id="@unchecked_checkbox",
                        container=self.elements["scroll_container"],
                        manager=MANAGER
                    )
                    self.trait_names[trait] = pygame_gui.elements.UITextBox(
                        trait_name.capitalize(),
                        ui_scale(pygame.Rect((0 + 32, y_pos), (200, 34))),
                        object_id=get_text_box_theme("#text_box_30_horizleft"),
                        container=self.elements["scroll_container"],
                        manager=MANAGER
                    )
                    y_pos += 40

            if self.current_selection == "skill":
                for skill in self.skills:
                    if skill != "Random":
                        skillobj = Skill.get_skill_from_string(Skill, skill, "True", skill_object_only=True)
                        skill_string = Skill.short_strings[skillobj]
                    else:
                        skill_string = skill

                    if skill_string[0] != skill_string[0].upper():
                        skill_string = skill_string.capitalize()

                    self.skill_buttons[skill] = UIImageButton(
                        ui_scale(pygame.Rect((0, y_pos), (34, 34))),
                        "",
                        object_id="@unchecked_checkbox",
                        container=self.elements["scroll_container"],
                    )

                    self.skill_names[skill] = pygame_gui.elements.UITextBox(
                        skill_string,
                        ui_scale(pygame.Rect((0 + 32, y_pos), (200, 34))),
                        object_id=get_text_box_theme("#text_box_30_horizleft"),
                        container=self.elements["scroll_container"],
                        manager=MANAGER
                    )
                    y_pos += 40
 
    def handle_customize_cat_event(self, event):
        pelt_options = []
        for category in LegacyPelt.pelt_categories:
            if category == "torties":
                continue
            pelt_options += LegacyPelt.pelt_categories[category]
        pelt_options.remove("TwoColour")

        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            # cycle buttons. oh god
            if event.ui_element == self.elements["cycle_right"] or event.ui_element == self.elements["cycle_left"]:
                if event.ui_element == self.elements["cycle_right"]:
                    num = 1
                    if self.page == 0:
                        if self.preview_age == "newborn":
                            if self.newborn_pose < 2:
                                self.newborn_pose += 1
                            else:
                                self.newborn_pose = 0
                        if self.preview_age == "kitten":
                            if self.kitten_sprite < 2:
                                self.kitten_sprite += 1
                            else:
                                self.kitten_sprite = 0
                        elif self.preview_age == "adolescent":
                            if self.adolescent_pose < 2:
                                self.adolescent_pose += 1
                            else:
                                self.adolescent_pose = 0
                        elif self.preview_age == "adult":
                            if self.adult_pose < 2:
                                self.adult_pose += 1
                            else:
                                self.adult_pose = 0
                        elif self.preview_age == "elder":
                            if self.elder_pose < 2:
                                self.elder_pose += 1
                            else:
                                self.elder_pose = 0
                elif event.ui_element == self.elements["cycle_left"]:
                    num = -1
                    if self.page == 0:
                        if self.preview_age == "kitten":
                            if self.kitten_sprite > 0:
                                self.kitten_sprite -= 1
                            else:
                                self.kitten_sprite = 2
                        if self.preview_age == "newborn":
                            if self.newborn_pose > 0:
                                self.newborn_pose -= 1
                            else:
                                self.newborn_pose = 2
                        elif self.preview_age == "adolescent":
                            if self.adolescent_pose > 0:
                                self.adolescent_pose -= 1
                            else:
                                self.adolescent_pose = 2
                        elif self.preview_age == "adult":
                            if self.adult_pose > 0:
                                self.adult_pose -= 1
                            else:
                                self.adult_pose = 2
                        elif self.preview_age == "elder":
                            if self.elder_pose > 0:
                                self.elder_pose -= 1
                            else:
                                self.elder_pose = 2
                if self.page == 1:
                    if self.current_selection == "pelt_colour":
                        colours = LegacyPelt.all_pelt_colours
                        current_index = colours.index(self.custom_cat.legacy_pelt.colour)
                        next_index = (current_index + num) % len(colours)

                        self.custom_cat.legacy_pelt.colour = colours[next_index]
                    elif self.current_selection == "white_patches":
                        patch_list = LegacyPelt.little_white + LegacyPelt.mid_white + LegacyPelt.high_white + LegacyPelt.mostly_white + ["FULLWHITE"]
                        if self.customiser_sort == "alphabetical":
                            patch_list.sort()

                        # grabbing search results
                        new_patch_list = []
                        searched = self.search_text
                        if searched not in ["", "search"]:
                            for patch in patch_list:
                                if searched.lower() in patch.lower():
                                    new_patch_list.append(patch)
                        else:
                            new_patch_list = patch_list

                        patches = ["None"] + new_patch_list
                        try:
                            current_index = patches.index(str(self.custom_cat.legacy_pelt.white_patches))
                        except ValueError:
                            current_index = 0
                        next_index = (current_index + num) % len(patches)
                        if patches[next_index] == "None":
                            self.custom_cat.legacy_pelt.white_patches = None
                        else:
                            self.custom_cat.legacy_pelt.white_patches = patches[next_index]
                    elif self.current_selection == "points":
                        points = ["None"] + LegacyPelt.point_markings
                        current_index = points.index(str(self.custom_cat.legacy_pelt.points))
                        next_index = (current_index + num) % len(points)
                        if points[next_index] == "None":
                            self.custom_cat.legacy_pelt.points = None
                        else:
                            self.custom_cat.legacy_pelt.points = points[next_index]
                    elif self.current_selection == "vitiligo":
                        vitiligo = ["None"] + LegacyPelt.vitiligo_markings
                        current_index = vitiligo.index(str(self.custom_cat.legacy_pelt.vitiligo))
                        next_index = (current_index + num) % len(vitiligo)
                        if vitiligo[next_index] == "None":
                            self.custom_cat.legacy_pelt.vitiligo = None
                        else:
                            self.custom_cat.legacy_pelt.vitiligo = vitiligo[next_index]
                    elif self.current_selection == "pelt_pattern":
                        if self.custom_cat.legacy_pelt.name in ["Tortie", "Calico"]:
                            if self.custom_cat.legacy_pelt.tortie_base == "single":
                                basename = "SingleColour"
                            else:
                                basename = self.custom_cat.legacy_pelt.tortie_base.capitalize()
                            current_index = pelt_options.index(basename)
                        else:
                            current_index = pelt_options.index(self.custom_cat.legacy_pelt.name)
                        next_index = (current_index + num) % len(pelt_options)
                        if pelt_options[next_index] in ["SingleColour", "TwoColour", "Singlecolour"] and self.custom_cat.legacy_pelt.name in ["Tortie", "Calico"]:
                            next_pelt = "single"
                        else:
                            next_pelt = pelt_options[next_index]
                        if self.custom_cat.legacy_pelt.name in ["Tortie", "Calico"]:
                            self.custom_cat.legacy_pelt.tortie_base = next_pelt.lower()
                        else:
                            self.custom_cat.legacy_pelt.name = next_pelt
                    elif self.current_selection == "tortie_colour":
                        colours = LegacyPelt.all_pelt_colours
                        current_index = colours.index(str(self.custom_cat.legacy_pelt.tortie_colour))
                        next_index = (current_index + num) % len(colours)
                        self.custom_cat.legacy_pelt.tortie_colour = colours[next_index]
                    elif self.current_selection == "tortie_patches":
                        pelts = LegacyPelt.tortie_patches
                        current_index = pelts.index(str(self.custom_cat.legacy_pelt.tortie_marking))
                        next_index = (current_index + num) % len(pelts)
                        self.custom_cat.legacy_pelt.tortie_marking = pelts[next_index]
                    elif self.current_selection == "tortie_pattern":
                        pelts = LegacyPelt.pelt_patterns
                        next_pelt = self.custom_cat.legacy_pelt.tortie_pattern
                        current_index = pelts.index(next_pelt)
                        next_index = (current_index + num) % len(pelts)
                        self.custom_cat.legacy_pelt.tortie_pattern = pelts[next_index]
                elif self.page == 2:
                    if self.current_selection == "eye_colour":
                        colours = LegacyPelt.all_eye_colours
                        current_index = colours.index(self.custom_cat.legacy_pelt.eye_colour)
                        next_index = (current_index + num) % len(colours)
                        self.custom_cat.legacy_pelt.eye_colour = colours[next_index]
                    elif self.current_selection == "heterochromia":
                        colours = ["None"] + LegacyPelt.all_eye_colours
                        current_index = colours.index(str(self.custom_cat.legacy_pelt.eye_colour2))
                        next_index = (current_index + num) % len(colours)
                        if colours[next_index] == "None":
                            next_eye = None
                        else:
                            next_eye = colours[next_index]
                        self.custom_cat.legacy_pelt.eye_colour2 = next_eye
                    elif self.current_selection == "skin":
                        colours = LegacyPelt.skin_sprites
                        current_index = colours.index(self.custom_cat.legacy_pelt.skin)
                        next_index = (current_index + num) % len(colours)
                        self.custom_cat.legacy_pelt.skin = colours[next_index]
                    elif self.current_selection == "scar":
                        scars = ["None"] + LegacyPelt.all_scars
                        current_index = scars.index(self.custom_cat.legacy_pelt.scars[-1]) if self.custom_cat.legacy_pelt.scars else 0
                        next_index = (current_index + num) % len(scars)
                        if not self.scar_buttons[scars[next_index]].is_enabled:
                            next_index += num
                        try:
                            # im such a hack
                            test = scars[next_index]
                        except IndexError:
                            next_index = 0
                        if scars[next_index] == "None":
                            next_scar = []
                        else:
                            next_scar = [scars[next_index]]
                        self.custom_cat.legacy_pelt.scars = next_scar
                    elif self.current_selection == "accessory":
                        acc_list = (self.all_accs)
                        if self.customiser_sort == "alphabetical":
                            acc_list.sort()

                        new_acc_list = []
                        searched = self.search_text
                        if searched not in ["", "search"]:
                            for acc in acc_list:
                                if searched in str(i18n.t(self.get_acc_name(acc))).lower() or searched in acc.lower():
                                    new_acc_list.append(acc)
                        else:
                            new_acc_list = acc_list

                        for i in self.accessory_buttons.items():
                            if not self.accessory_buttons[i[0]].is_enabled and i[0] not in self.custom_cat.legacy_pelt.accessory:
                                if i[0] in new_acc_list or i[0] in self.custom_cat.legacy_pelt.accessory:
                                    new_acc_list.remove(i[0])
                        accs = ["None"] + new_acc_list
                        try:
                            current_index = accs.index(self.custom_cat.legacy_pelt.accessory[0]) if self.custom_cat.legacy_pelt.accessory else 0
                        except ValueError:
                            current_index = 0
                        next_index = (current_index + num) % len(accs)
                        if accs[next_index] == "None":
                            next_acc = []
                        else:
                            next_acc = [accs[next_index]]
                        self.custom_cat.legacy_pelt.accessory = next_acc
                elif self.page == 3:
                    if self.current_selection == "condition":
                        permanent_conditions = ['None', 'born without a leg', 'weak leg', 'twisted leg', 'born without a tail', 'paralyzed', 'raspy lungs', 'wasting disease', 'blind', 'one bad eye', 'failing eyesight', 'partial hearing loss', 'deaf', 'constant joint pain', 'seizure prone', 'allergies', 'persistent headaches']
                        current_index = permanent_conditions.index(str(self.permanent_condition))
                        next_index = (current_index + num) % len(permanent_conditions)
                        if permanent_conditions[next_index] == "None":
                            self.permanent_condition = None
                        else:
                            self.permanent_condition = permanent_conditions[next_index]
                            if self.permanent_condition == "None":
                                self.permanent_condition = None

                        if self.permanent_condition != "paralyzed":
                            self.custom_cat.legacy_pelt.paralyzed = False
                        else:
                            self.custom_cat.legacy_pelt.paralyzed = True

                        if self.permanent_condition == "born without a leg":
                            self.custom_cat.legacy_pelt.scars = ("NOPAW",)
                        else:
                            if "NOPAW" in self.custom_cat.legacy_pelt.scars:
                                self.custom_cat.legacy_pelt.scars = tuple()

                        if self.permanent_condition == "born without a tail":
                            self.custom_cat.legacy_pelt.scars = ("NOTAIL",)
                        else:
                            if "NOTAIL" in self.custom_cat.legacy_pelt.scars:
                                self.custom_cat.legacy_pelt.scars = tuple()
                        
                        if self.permanent_condition != "blind":
                            if "BOTHBLIND" in self.custom_cat.legacy_pelt.scars:
                                self.custom_cat.legacy_pelt.scars = tuple()
                        if self.permanent_condition != "one bad eye":
                            if any(scar in ["LEFTBLIND", "RIGHTBLIND", "BRIGHTHEART"] for scar in self.custom_cat.legacy_pelt.scars):
                                self.custom_cat.legacy_pelt.scars = tuple()
                    elif self.current_selection == "trait":
                        traits = ['unruly','shy','impulsive','bullying','attention-seeker','daydreamer','charming','fearless','skittish','quiet','self-conscious','know-it-all','sweet','polite','bossy','noisy','smug','secretive','grumpy','manipulative','leader-like','passionate','disciplined','patient','rebellious','honest']
                        current_index = traits.index(self.personality)
                        next_index = (current_index + num) % len(traits)
                        self.personality = traits[next_index]
                    elif self.current_selection == "skill":
                        current_index = self.skills.index(self.skill)
                        next_index = (current_index + num) % len(self.skills)
                        self.skill = self.skills[next_index]

                self.update_sprite()
                self.update_disabled_buttons()
            elif event.ui_element == self.elements["randomise_selection"]:
                if self.page == 0:
                    if self.preview_age == "newborn":
                        self.newborn_pose=random.randint(0,2)
                    elif self.preview_age == "kitten":
                        self.kitten_sprite=random.randint(0,2)
                    elif self.preview_age == "adolescent":
                        self.adolescent_pose = random.randint(0,2)
                    elif self.preview_age == "adult":
                        self.adult_pose = random.randint(0,2)
                    else:
                        self.elder_pose = random.randint(0,2)
                if self.page == 1:
                    if self.current_selection == "pelt_pattern":
                        if self.custom_cat.legacy_pelt.name in ["Tortie", "Calico"]:
                            new_pattern = random.choice(LegacyPelt.pelt_patterns)
                            if new_pattern == "SingleColour":
                                new_pattern = "single"
                            self.custom_cat.legacy_pelt.tortie_base = new_pattern.lower()
                        else:
                            self.custom_cat.legacy_pelt.name = random.choice(pelt_options)
                    elif self.current_selection == "pelt_colour":
                        self.custom_cat.legacy_pelt.colour = random.choice(LegacyPelt.all_pelt_colours)
                    elif self.current_selection == "white_patches":
                        self.custom_cat.legacy_pelt.white_patches= random.choice(["FULLWHITE"] + LegacyPelt.little_white + LegacyPelt.mid_white + LegacyPelt.high_white + LegacyPelt.mostly_white + [None])
                    elif self.current_selection == "points":
                        self.custom_cat.legacy_pelt.points = random.choice(LegacyPelt.point_markings + [None])
                    elif self.current_selection == "vitiligo":
                        self.custom_cat.legacy_pelt.vitiligo = random.choice(LegacyPelt.vitiligo_markings + [None])
                    elif self.current_selection == "tortie_pattern":
                        new_pattern = random.choice(LegacyPelt.pelt_patterns)
                        if new_pattern == "SingleColour":
                            new_pattern = "single"
                        self.custom_cat.legacy_pelt.tortie_pattern = new_pattern.lower()
                    elif self.current_selection == "tortie_colour":
                        self.custom_cat.legacy_pelt.tortie_colour = random.choice(LegacyPelt.all_pelt_colours)
                    elif self.current_selection == "tortie_patches":
                        self.custom_cat.legacy_pelt.tortie_marking = random.choice(LegacyPelt.tortie_patches)
                elif self.page == 2:
                    if self.current_selection == "eye_colour":
                        self.custom_cat.legacy_pelt.eye_colour= random.choice(LegacyPelt.all_eye_colours)
                    elif self.current_selection == "heterochromia":
                        self.custom_cat.legacy_pelt.eye_colour = random.choice(LegacyPelt.all_eye_colours)
                    elif self.current_selection == "skin":
                        self.custom_cat.legacy_pelt.skin = random.choice(LegacyPelt.skin_sprites)
                    elif self.current_selection == "scar":
                        self.custom_cat.legacy_pelt.scars = (random.choice(LegacyPelt.all_scars),)
                    elif self.current_selection == "accessory":

                        acc_list = (self.all_accs)
                        new_acc_list = []
                        searched = self.search_text
                        if searched not in ["", "search"]:
                            for acc in acc_list:
                                if searched in str(i18n.t(self.get_acc_name(acc))) or searched in acc.lower():
                                    new_acc_list.append(acc)
                        else:
                            new_acc_list = acc_list

                        if self.permanent_condition == "born without a tail":
                            for i in Pelt.tail_accessories:
                                if i in new_acc_list:
                                    new_acc_list.remove(i)
                        if self.permanent_condition == "born without a leg":
                            for i in Pelt.paw_accessories:
                                if i in new_acc_list:
                                    new_acc_list.remove(i)
                        
                        acc = choice(new_acc_list)

                        self.custom_cat.legacy_pelt.accessory = [acc]
                        self.custom_cat.legacy_pelt.inventory = [acc]

                elif self.page == 3:
                    if self.current_selection == "condition":
                        permanent_conditions = ['None', 'born without a leg', 'weak leg', 'twisted leg', 'born without a tail', 'paralyzed', 'raspy lungs', 'wasting disease', 'blind', 'one bad eye', 'failing eyesight', 'partial hearing loss', 'deaf', 'constant joint pain', 'seizure prone', 'allergies', 'persistent headaches']

                        self.permanent_condition = random.choice(permanent_conditions)
                        if self.permanent_condition == "born without a leg":
                            self.custom_cat.legacy_pelt.scars = ("NOPAW",)
                        else:
                            if "NOPAW" in self.custom_cat.legacy_pelt.scars:
                                self.custom_cat.legacy_pelt.scars = tuple()
                        if self.permanent_condition == "born without a tail":
                            self.custom_cat.legacy_pelt.scars = ("NOTAIL",)
                        else:
                            if "NOTAIL" in self.custom_cat.legacy_pelt.scars:
                                self.custom_cat.legacy_pelt.scars = tuple()
                        if self.permanent_condition == "paralyzed":
                            self.custom_cat.legacy_pelt.paralyzed = True
                        else:
                            self.custom_cat.legacy_pelt.paralyzed = False
                    elif self.current_selection == "trait":
                        self.personality = random.choice(['unruly','shy','impulsive','bullying','attention-seeker','daydreamer','charming','fearless','skittish','quiet','self-conscious','know-it-all','sweet','polite','bossy','noisy','smug','secretive','grumpy','manipulative','leader-like','passionate','disciplined','patient','rebellious','honest'])
                    elif self.current_selection == "skill":
                        skill_choices = []
                        for i in self.skills:
                            if i != "Random":
                                skill_choices.append(i)
                        self.skill = random.choice(skill_choices)

                self.update_sprite()
                self.update_disabled_buttons()

            if "search_button" in self.elements and event.ui_element == self.elements["search_button"]:
                self.search_text = self.elements["search_bar"].get_text()
                self.previous_search_text = self.search_text
                self.update_custom_cat_pages()
                self.update_sprite()
                self.update_disabled_buttons()
            if "clear" in self.elements and event.ui_element == self.elements["clear"]:
                self.search_text = ""
                self.previous_search_text = self.search_text
                self.update_custom_cat_pages()
                self.update_sprite()
                self.update_disabled_buttons()
            if "match_base" in self.elements and event.ui_element == self.elements["match_base"]:
                self.custom_cat.legacy_pelt.tortie_pattern = self.custom_cat.legacy_pelt.tortie_base
                self.update_custom_cat_pages()
                self.update_sprite()
                self.update_disabled_buttons()
            if "match_tortie" in self.elements and event.ui_element == self.elements["match_tortie"]:
                self.custom_cat.legacy_pelt.tortie_base = self.custom_cat.legacy_pelt.tortie_pattern.lower()
                self.update_custom_cat_pages()
                self.update_sprite()
                self.update_disabled_buttons()

            if self.page == 0:
                for i in self.preview_age_buttons.items():
                    if event.ui_element == self.preview_age_buttons[i[0]]:
                        self.preview_age = i[0]
                        self.update_custom_cat_pages()
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.newborn_pose_buttons.items():
                    if event.ui_element == self.newborn_pose_buttons[i[0]]:
                        self.newborn_pose = int(i[0])
                        self.update_custom_cat_pages()
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.kitten_pose_buttons.items():
                    if event.ui_element == self.kitten_pose_buttons[i[0]]:
                        self.kitten_sprite = int(i[0])
                        self.update_custom_cat_pages()
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.adolescent_pose_buttons.items():
                    if event.ui_element == self.adolescent_pose_buttons[i[0]]:
                        self.adolescent_pose = int(i[0])
                        self.update_custom_cat_pages()
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.adult_pose_buttons.items():
                    if event.ui_element == self.adult_pose_buttons[i[0]]:
                        self.adult_pose = int(i[0])
                        self.update_custom_cat_pages()
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.elder_pose_buttons.items():
                    if event.ui_element == self.elder_pose_buttons[i[0]]:
                        self.elder_pose = int(i[0])
                        self.update_custom_cat_pages()
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.fur_length_buttons.items():
                    if event.ui_element == self.fur_length_buttons[i[0]]:
                        self.custom_cat.legacy_pelt.length = i[0]
                        # correct long/shorthaired poses
                        # TODO: yea
                        self.update_custom_cat_pages()
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.reverse_buttons.items():
                    if event.ui_element == self.reverse_buttons[i[0]]:
                        if i[0] == "False":
                            self.custom_cat.legacy_pelt.reverse = False
                        else:
                            self.custom_cat.legacy_pelt.reverse = True
                        self.update_custom_cat_pages()
                        self.update_sprite()
                        self.update_disabled_buttons()
            elif self.page == 1:
                if event.ui_element == self.elements["tortie_checkbox"]:
                    if self.tortie_enabled is True:
                        self.tortie_enabled = False
                        self.custom_cat.legacy_pelt.name = self.custom_cat.legacy_pelt.tortie_base.capitalize()
                        if self.custom_cat.legacy_pelt.name == "Single":
                            self.custom_cat.legacy_pelt.name = "SingleColour"
                        self.custom_cat.legacy_pelt.tortie_base = None
                        self.custom_cat.legacy_pelt.tortie_colour = None
                        self.custom_cat.legacy_pelt.tortie_pattern = None
                        self.custom_cat.legacy_pelt.tortie_marking = None
                    else:
                        self.tortie_enabled = True
                        self.custom_cat.legacy_pelt.tortie_base = self.custom_cat.legacy_pelt.name.lower()
                        if self.custom_cat.legacy_pelt.tortie_base == "singlecolour":
                            self.custom_cat.legacy_pelt.tortie_base = "single"
                        self.custom_cat.legacy_pelt.name = "Tortie"
                        self.custom_cat.legacy_pelt.tortie_colour = "GINGER"
                        self.custom_cat.legacy_pelt.tortie_pattern = "classic"
                        self.custom_cat.legacy_pelt.tortie_marking = "ONE"
                    self.update_custom_cat_pages()
                    self.update_sprite()
                    self.update_disabled_buttons()
                for i in self.pelt_pattern_buttons.items():
                    if event.ui_element == self.pelt_pattern_buttons[i[0]]:
                        if self.custom_cat.legacy_pelt.name == "Tortie":
                            self.custom_cat.legacy_pelt.tortie_base = i[0].lower()
                        else:
                            self.custom_cat.legacy_pelt.name = i[0]
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.pelt_colour_buttons.items():
                    if event.ui_element == self.pelt_colour_buttons[i[0]]:
                        self.custom_cat.legacy_pelt.colour = i[0]
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.tint_buttons.items():
                    if event.ui_element == self.tint_buttons[i[0]]:
                        self.custom_cat.legacy_pelt.tint = i[0]
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.white_patches_tint_buttons.items():
                    if event.ui_element == self.white_patches_tint_buttons[i[0]]:
                        self.custom_cat.legacy_pelt.white_patches_tint = i[0]
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.white_patches_buttons.items():
                    if event.ui_element == self.white_patches_buttons[i[0]]:
                        if i[0] == "None":
                            self.custom_cat.legacy_pelt.white_patches= None
                        else:
                            self.custom_cat.legacy_pelt.white_patches= i[0]
                            self.custom_cat.legacy_pelt.white_patches = i[0]
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.points_buttons.items():
                    if event.ui_element == self.points_buttons[i[0]]:
                        if i[0] == "None":
                            self.custom_cat.legacy_pelt.points = None
                        else:
                            self.custom_cat.legacy_pelt.points = i[0]
                        self.update_custom_cat_pages()
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.vitiligo_buttons.items():
                    if event.ui_element == self.vitiligo_buttons[i[0]]:
                        if i[0] == "None":
                            self.custom_cat.legacy_pelt.vitiligo = None
                        else:
                            self.custom_cat.legacy_pelt.vitiligo = i[0]
                        self.update_custom_cat_pages()
                        self.update_sprite()
                        self.update_disabled_buttons()
                # TORTIE
                for i in self.tortie_pattern_buttons.items():
                    if event.ui_element == self.tortie_pattern_buttons[i[0]]:
                        self.custom_cat.legacy_pelt.tortie_pattern = i[0].lower()
                        if self.custom_cat.legacy_pelt.tortie_pattern == "singlecolour":
                            self.custom_cat.legacy_pelt.tortie_pattern = "single"
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.tortie_colour_buttons.items():
                    if event.ui_element == self.tortie_colour_buttons[i[0]]:
                        self.custom_cat.legacy_pelt.tortie_colour = i[0].upper()
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.tortie_patches_buttons.items():
                    if event.ui_element == self.tortie_patches_buttons[i[0]]:
                        self.custom_cat.legacy_pelt.tortie_marking = i[0].upper()
                        self.update_sprite()
                        self.update_disabled_buttons()
            elif self.page == 2:
                for i in self.eye_colour_buttons.items():
                    if event.ui_element == self.eye_colour_buttons[i[0]]:
                        self.custom_cat.legacy_pelt.eye_colour= i[0].upper()
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.heterochromia_buttons.items():
                    if event.ui_element == self.heterochromia_buttons[i[0]]:
                        self.custom_cat.legacy_pelt.eye_colour2 = i[0].upper() if i[0] != "None" else None
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.skin_buttons.items():
                    if event.ui_element == self.skin_buttons[i[0]]:
                        self.custom_cat.legacy_pelt.skin = i[0].upper()
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.scar_buttons.items():
                    if event.ui_element == self.scar_buttons[i[0]]:
                        if i[0] == "None":
                            self.custom_cat.legacy_pelt.scars = tuple()
                        else:
                            self.custom_cat.legacy_pelt.scars = (i[0].upper(),)
                            if i[0] == "NOPAW":
                                self.permanent_condition = "born without a leg"
                                self.custom_cat.legacy_pelt.paralyzed = False
                            else:
                                if self.permanent_condition == "born without a leg":
                                    self.permanent_condition = None
                            if i[0] == "NOTAIL":
                                self.permanent_condition = "born without a tail"
                            else:
                                if self.permanent_condition == "born without a tail":
                                    self.permanent_condition = None
                            if i[0] == "BOTHBLIND":
                                self.permanent_condition = "blind"
                                self.custom_cat.legacy_pelt.paralyzed = False
                            if i[0] in ["RIGHTBLIND", "LEFTBLIND", "BRIGHTHEART"]:
                                self.permanent_condition = "one bad eye"
                                self.custom_cat.legacy_pelt.paralyzed = False
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.accessory_buttons.items():
                    if event.ui_element == self.accessory_buttons[i[0]]:
                        if i[0] == "None":
                            self.custom_cat.legacy_pelt.accessory = []
                            self.custom_cat.legacy_pelt.inventory = []
                        else:
                            self.custom_cat.legacy_pelt.accessory = [i[0]]
                            self.custom_cat.legacy_pelt.inventory = [i[0]]
                        self.update_sprite()
                        self.update_disabled_buttons()
            elif self.page == 3:
                for i in self.condition_buttons.items():
                    if event.ui_element == self.condition_buttons[i[0]]:
                        if i[0] == "None":
                            self.permanent_condition = None
                            if "NOTAIL" in self.custom_cat.legacy_pelt.scars:
                                self.custom_cat.legacy_pelt.scars = tuple()
                            if "NOPAW" in self.custom_cat.legacy_pelt.scars:
                                self.custom_cat.legacy_pelt.scars = tuple()
                            if "BRIGHTHEART" in self.custom_cat.legacy_pelt.scars:
                                self.custom_cat.legacy_pelt.scars = tuple()
                            if "BOTHBLIND" in self.custom_cat.legacy_pelt.scars:
                                self.custom_cat.legacy_pelt.scars = tuple()
                            if "LEFTBLIND" in self.custom_cat.legacy_pelt.scars:
                                self.custom_cat.legacy_pelt.scars = tuple()
                            if "RIGHTBLIND" in self.custom_cat.legacy_pelt.scars:
                                self.custom_cat.legacy_pelt.scars = tuple()
                            self.custom_cat.legacy_pelt.paralyzed = False
                        else:
                            if i[0] != "paralyzed":
                                self.custom_cat.legacy_pelt.paralyzed = False
                            else:
                                self.custom_cat.legacy_pelt.paralyzed = True

                            if i[0] == "born without a leg":
                                self.custom_cat.legacy_pelt.scars = ("NOPAW",)
                            else:
                                if "NOPAW" in self.custom_cat.legacy_pelt.scars:
                                    self.custom_cat.legacy_pelt.scars = tuple()

                            if i[0] == "born without a tail":
                                self.custom_cat.legacy_pelt.scars = ("NOTAIL",)
                            else:
                                if "NOTAIL" in self.custom_cat.legacy_pelt.scars:
                                    self.custom_cat.legacy_pelt.scars = tuple()
                            
                            if i[0] != "blind":
                                if "BOTHBLIND" in self.custom_cat.legacy_pelt.scars:
                                    self.custom_cat.legacy_pelt.scars = tuple()
                            if i[0] != "one bad eye":
                                if any(scar in ["LEFTBLIND", "RIGHTBLIND", "BRIGHTHEART"] for scar in self.custom_cat.legacy_pelt.scars):
                                    self.custom_cat.legacy_pelt.scars = tuple()

                            self.permanent_condition = i[0]
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.trait_buttons.items():
                    if event.ui_element == self.trait_buttons[i[0]]:
                        self.personality = i[0]
                        self.update_disabled_buttons()
                for i in self.skill_buttons.items():
                    if event.ui_element == self.skill_buttons[i[0]]:
                        self.skill = i[0]
                        self.update_disabled_buttons()
                for i in self.faith_buttons.items():
                    if event.ui_element == self.faith_buttons[i[0]]:
                        self.faith = i[0]
                        self.update_disabled_buttons()
                for i in self.sex_buttons.items():
                    if event.ui_element == self.sex_buttons[i[0]]:
                        self.custom_cat.gender = i[0]
                        self.update_disabled_buttons()

            for i in self.current_selection_buttons.items():
                if event.ui_element == self.current_selection_buttons[i[0]]:
                    self.current_selection = i[0]
                    self.update_custom_cat_pages()
                    self.update_sprite()
                    self.update_disabled_buttons()
            for i in ["default", "alphabetical"]:
                if i in self.elements:
                    if event.ui_element == self.elements[i]:
                        self.customiser_sort = i
                        self.update_custom_cat_pages()
                        self.update_sprite()
                        self.update_disabled_buttons()

            if event.ui_element == self.main_menu:
                self.change_screen(GameScreen.START)
            elif event.ui_element == self.elements['right']:
                if self.page < 5:
                    self.page += 1
                    self.update_custom_cat_pages()
                    self.update_disabled_buttons()
            elif event.ui_element == self.elements['left']:
                if self.page > 0:
                    self.page -= 1
                    self.update_custom_cat_pages()
                    self.update_disabled_buttons()
            elif event.ui_element == self.elements['random_customize']:
                self.randomize_custom_cat()
                self.update_custom_cat_pages()
                self.update_sprite()
                self.update_disabled_buttons()
            elif event.ui_element == self.elements['next_step']:
                # make the cat with the picked sex first so the genes (tortie toms etc) line up
                self.your_cat = Cat(moons = -1, gender=self.custom_cat.gender)
                initial_pelt = self.custom_cat.legacy_pelt
                new_pelt = LegacyPelt(
                    name=initial_pelt.name,
                    length=initial_pelt.length,
                    colour=initial_pelt.colour,
                    white_patches=initial_pelt.white_patches,
                    eye_color=initial_pelt.eye_colour,
                    eye_colour2=initial_pelt.eye_colour2,
                    tortie_base=initial_pelt.tortie_base,
                    tortie_colour=initial_pelt.tortie_colour,
                    tortie_marking=initial_pelt.tortie_marking,
                    tortie_pattern=initial_pelt.tortie_pattern,
                    vitiligo=initial_pelt.vitiligo,
                    points=initial_pelt.points,
                    accessory=initial_pelt.accessory,
                    inventory=initial_pelt.inventory,
                    paralyzed=initial_pelt.paralyzed,
                    scars=initial_pelt.scars,
                    tint=initial_pelt.tint,
                    skin=initial_pelt.skin,
                    white_patches_tint=initial_pelt.white_patches_tint,
                    newborn_sprite="newborn" + str(self.newborn_pose),
                    kitten_sprite="kitten" + str(self.kitten_sprite),
                    adol_sprite=(
                        ("adolescent_short" + str(self.adolescent_pose))
                        if initial_pelt.length != "long"
                        else
                        ("adolescent_long" + str(self.adolescent_pose))),
                    adult_sprite=(
                        ("adult_short" + str(self.adult_pose))
                        if initial_pelt.length != "long"
                        else 
                        ("adult_long" + str(self.adult_pose))),
                    senior_sprite="senior" + str(self.elder_pose),
                    para_adult_sprite= "para_adult_long0" if initial_pelt.length == "long" else "para_adult_short0",
                    reverse=initial_pelt.reverse
                )
                new_pelt.apply_to_cat(self.your_cat)

                # genemod keeps the genetic sex in .gender (tom/molly), so only set how they identify
                self.your_cat.genderalign = {"male": "tom", "female": "molly"}.get(
                    self.custom_cat.gender, self.custom_cat.gender
                )

                if self.custom_cat.gender == "male":
                    self.your_cat.pronouns = [get_default_pronouns()["1"].copy()]
                elif self.custom_cat.gender == "female":
                    self.your_cat.pronouns = [get_default_pronouns()["2"].copy()]
                else:
                    self.your_cat.pronouns = [get_default_pronouns()["0"].copy()]

                if self.permanent_condition is not None and self.permanent_condition != 'paralyzed':
                    self.your_cat.get_permanent_condition(self.permanent_condition, born_with=True)
                    self.your_cat.permanent_condition[self.permanent_condition]["moons_until"] = 1
                    self.your_cat.permanent_condition[self.permanent_condition]["moons_with"] = -1
                    self.your_cat.permanent_condition[self.permanent_condition]['born_with'] = True
                if self.custom_cat.legacy_pelt.paralyzed and 'paralyzed' not in self.your_cat.permanent_condition:
                    self.your_cat.get_permanent_condition('paralyzed')
                    self.your_cat.permanent_condition['paralyzed']["moons_until"] = 1
                    self.your_cat.permanent_condition['paralyzed']["moons_with"] = -1
                    self.your_cat.permanent_condition['paralyzed']['born_with'] = True
                if self.permanent_condition is not None and self.permanent_condition == "born without a tail" and "NOTAIL" not in self.your_cat.pelt.scars:
                    self.your_cat.pelt.scars = ('NOTAIL',)
                    self.your_cat.permanent_condition['born without a tail']["moons_until"] = 1
                    self.your_cat.permanent_condition['born without a tail']["moons_with"] = -1
                    self.your_cat.permanent_condition['born without a tail']['born_with'] = True
                elif self.permanent_condition is not None and self.permanent_condition == "born without a leg" and "NOPAW" not in self.your_cat.pelt.scars:
                    self.your_cat.pelt.scars = ('NOPAW',)
                    self.your_cat.permanent_condition['born without a leg']["moons_until"] = 1
                    self.your_cat.permanent_condition['born without a leg']["moons_with"] = -1
                    self.your_cat.permanent_condition['born without a leg']['born_with'] = True
                self.your_cat.personality = Personality(trait=self.personality, kit_trait=True)
                if self.skill == "Random":
                    self.skill = random.choice(self.skills)
                self.your_cat.skills.primary = Skill.get_skill_from_string(Skill, self.skill, "True")
                self.your_cat.lock_faith = self.faith
                self.selected_cat = None
                self.custom_cat = None
                self.open_name_cat()
            elif event.ui_element == self.elements['previous_step']:
                self.selected_cat = None
                self.custom_cat = None
                self.open_choose_leader()

    def update_disabled_buttons(self):
        if self.page == 0:
            for i in range(0,3):
                if self.newborn_pose != i:
                    self.newborn_pose_buttons[str(i)].enable()
                else:
                    self.newborn_pose_buttons[str(i)].disable()
                if self.kitten_sprite != i:
                    self.kitten_pose_buttons[str(i)].enable()
                else:
                    self.kitten_pose_buttons[str(i)].disable()
                if self.adolescent_pose != i:
                    self.adolescent_pose_buttons[str(i)].enable()
                else:
                    self.adolescent_pose_buttons[str(i)].disable()
                if self.adult_pose != i:
                    self.adult_pose_buttons[str(i)].enable()
                else:
                    self.adult_pose_buttons[str(i)].disable()
                if self.elder_pose != i:
                    self.elder_pose_buttons[str(i)].enable()
                else:
                    self.elder_pose_buttons[str(i)].disable()

            for i in ["newborn", "kitten", "adolescent", "adult", "elder"]:
                if self.preview_age != i:
                    self.preview_age_buttons[i].enable()
                else:
                    self.preview_age_buttons[i].disable()

            for i in ["short", "medium", "long"]:
                if self.custom_cat.legacy_pelt.length != i:
                    self.fur_length_buttons[i].enable()
                else:
                    self.fur_length_buttons[i].disable()

            for i in [True, False]:
                if self.custom_cat.legacy_pelt.reverse != i:
                    self.reverse_buttons[str(i)].enable()
                else:
                    self.reverse_buttons[str(i)].disable()

        if self.page == 1:
            
            for i in self.pelt_pattern_buttons.items():
                if self.custom_cat.legacy_pelt.name in ["Tortie", "Calico"]:
                    pattern = self.custom_cat.legacy_pelt.tortie_base.capitalize()
                    if pattern == "Single":
                        pattern = "SingleColour"
                else:
                    pattern = self.custom_cat.legacy_pelt.name
                if i[0] != pattern:
                    self.pelt_pattern_buttons[i[0]].enable()
                else:
                    self.pelt_pattern_buttons[i[0]].disable()
            
            for i in self.pelt_colour_buttons.items():
                if i[0] != self.custom_cat.legacy_pelt.colour:
                    self.pelt_colour_buttons[i[0]].enable()
                else:
                    self.pelt_colour_buttons[i[0]].disable()
            
            for i in self.tint_buttons.items():
                if i[0] != self.custom_cat.legacy_pelt.tint:
                    self.tint_buttons[i[0]].enable()
                else:
                    self.tint_buttons[i[0]].disable()
            
            for i in self.white_patches_tint_buttons.items():
                if i[0] != self.custom_cat.legacy_pelt.white_patches_tint:
                    self.white_patches_tint_buttons[i[0]].enable()
                else:
                    self.white_patches_tint_buttons[i[0]].disable()
            
            for i in self.white_patches_buttons.items():
                if i[0] != str(self.custom_cat.legacy_pelt.white_patches): # convert to string for the one None
                    self.white_patches_buttons[i[0]].enable()
                else:
                    self.white_patches_buttons[i[0]].disable()
            
            for i in self.points_buttons.items():
                if i[0] != str(self.custom_cat.legacy_pelt.points):
                    self.points_buttons[i[0]].enable()
                else:
                    self.points_buttons[i[0]].disable()
            
            for i in self.vitiligo_buttons.items():
                if i[0] != str(self.custom_cat.legacy_pelt.vitiligo):
                    self.vitiligo_buttons[i[0]].enable()
                else:
                    self.vitiligo_buttons[i[0]].disable()
            
            for i in self.tortie_pattern_buttons.items():
                pattern = i[0].lower()
                if pattern == "singlecolour":
                    pattern = "single"
                if pattern != self.custom_cat.legacy_pelt.tortie_pattern: # not changing to string bc this isnt accessible when its None
                    self.tortie_pattern_buttons[i[0]].enable()
                else:
                    self.tortie_pattern_buttons[i[0]].disable()
            
            for i in self.tortie_colour_buttons.items():
                if i[0] != self.custom_cat.legacy_pelt.tortie_colour:
                    self.tortie_colour_buttons[i[0]].enable()
                else:
                    self.tortie_colour_buttons[i[0]].disable()
            
            for i in self.tortie_patches_buttons.items():
                if i[0] != self.custom_cat.legacy_pelt.tortie_marking:
                    self.tortie_patches_buttons[i[0]].enable()
                else:
                    self.tortie_patches_buttons[i[0]].disable()

            if "match_tortie" in self.elements:
                if self.custom_cat.legacy_pelt.name != "Tortie":
                    self.elements["match_tortie"].disable()
                else:
                    self.elements["match_tortie"].enable()

        elif self.page == 2:
            for i in self.eye_colour_buttons.items():
                if i[0] != self.custom_cat.legacy_pelt.eye_colour:
                    self.eye_colour_buttons[i[0]].enable()
                else:
                    self.eye_colour_buttons[i[0]].disable()
            for i in self.heterochromia_buttons.items():
                if i[0] != str(self.custom_cat.legacy_pelt.eye_colour2):
                    self.heterochromia_buttons[i[0]].enable()
                else:
                    self.heterochromia_buttons[i[0]].disable()
            for i in self.skin_buttons.items():
                if i[0] != str(self.custom_cat.legacy_pelt.skin):
                    self.skin_buttons[i[0]].enable()
                else:
                    self.skin_buttons[i[0]].disable()
            for i in self.scar_buttons.items():
                if i[0] == "None" and not self.custom_cat.legacy_pelt.scars:
                    self.scar_buttons[i[0]].disable()
                else:
                    if i[0] not in self.custom_cat.legacy_pelt.scars:
                        self.scar_buttons[i[0]].enable()
                    else:
                        self.scar_buttons[i[0]].disable()
                if self.custom_cat.legacy_pelt.paralyzed is True:
                    for scar in ["BRIGHTHEART", "LEFTBLIND", "RIGHTBLIND", "BOTHBLIND", "NOPAW", "NOTAIL"]:
                        self.scar_buttons[scar].disable()
            for i in self.accessory_buttons.items():
                if i[0] == "None" and not self.custom_cat.legacy_pelt.accessory:
                    self.accessory_buttons[i[0]].disable()
                else:
                    if i[0] not in self.custom_cat.legacy_pelt.accessory:
                        self.accessory_buttons[i[0]].enable()
                    else:
                        self.accessory_buttons[i[0]].disable()
                if self.permanent_condition == "born without a tail":
                    for acc in Pelt.tail_accessories:
                        if acc in self.accessory_buttons:
                            self.accessory_buttons[acc].disable()
                        else:
                            print(acc, "button not generated?")
                if self.permanent_condition == "born without a leg":
                    for acc in Pelt.paw_accessories:
                        if acc in self.accessory_buttons:
                            self.accessory_buttons[acc].disable()
                        else:
                            print(acc, "button not generated?")

            if self.current_selection == "accessory":
                if "acc_name" in self.elements:
                    self.elements["acc_name"].kill()
                    del self.elements["acc_name"]

                if self.custom_cat.legacy_pelt.accessory:
                    self.elements["acc_name"] = pygame_gui.elements.UITextBox(
                        str(i18n.t(self.get_acc_name(self.custom_cat.legacy_pelt.accessory[0]), count=1)),
                        ui_scale(pygame.Rect((269, 470), (262, 75))),
                        object_id=get_text_box_theme("#text_box_30_horizcenter"),
                        manager=MANAGER
                    )
        elif self.page == 3:
            if self.current_selection == "condition":
                if "condition_name" in self.elements:
                    self.elements["condition_name"].kill()
                    del self.elements["condition_name"]

                if self.permanent_condition:
                    self.elements["condition_name"] = pygame_gui.elements.UITextBox(
                        self.permanent_condition.capitalize(),
                        ui_scale(pygame.Rect((300, 470), (200, 34))),
                        object_id=get_text_box_theme("#text_box_30_horizcenter"),
                        manager=MANAGER
                    )

            for i in self.condition_buttons.items():
                if i[0] == "None" and self.permanent_condition is None:
                    self.condition_buttons[i[0]].disable()
                else:
                    if i[0] != self.permanent_condition:
                        self.condition_buttons[i[0]].enable()
                    else:
                        self.condition_buttons[i[0]].disable()

            for i in self.trait_buttons.items():
                if i[0] != self.personality:
                    self.trait_buttons[i[0]].enable()
                else:
                    self.trait_buttons[i[0]].disable()

            if self.current_selection == "trait":
                if "trait_name" in self.elements:
                    self.elements["trait_name"].kill()
                    del self.elements["trait_name"]

                if self.personality:
                    self.elements["trait_name"] = pygame_gui.elements.UITextBox(
                        self.personality.capitalize(),
                        ui_scale(pygame.Rect((276, 470), (247, 49))),
                        object_id=get_text_box_theme("#text_box_30_horizcenter"),
                        manager=MANAGER
                    )

            if self.current_selection == "skill":
                if "skill_name" in self.elements:
                    self.elements["skill_name"].kill()
                    del self.elements["skill_name"]

                if self.skill:
                    if self.skill != "Random":
                        skillobj = Skill.get_skill_from_string(Skill, self.skill, "True", skill_object_only=True)
                        skill_string = Skill.short_strings[skillobj]
                    else:
                        skill_string = self.skill
                    if skill_string[0] != skill_string[0].upper():
                        skill_string = skill_string.capitalize()

                    self.elements["skill_name"] = pygame_gui.elements.UITextBox(
                        skill_string,
                        ui_scale(pygame.Rect((276, 470), (247, 49))),
                        object_id=get_text_box_theme("#text_box_30_horizcenter"),
                        manager=MANAGER
                    )

            for i in self.skill_buttons.items():
                if i[0] != self.skill:
                    self.skill_buttons[i[0]].enable()
                else:
                    self.skill_buttons[i[0]].disable()

            for i in self.faith_buttons.items():
                if i[0] != self.faith:
                    self.faith_buttons[i[0]].enable()
                else:
                    self.faith_buttons[i[0]].disable()

            for i in self.sex_buttons.items():
                if i[0] != self.custom_cat.gender:
                    self.sex_buttons[i[0]].enable()
                else:
                    self.sex_buttons[i[0]].disable()
            
        for i in self.current_selection_buttons.items():
            if self.current_selection != i[0]:
                if i[0] in ["tortie_pattern", "tortie_colour", "tortie_patches"]:
                    if self.tortie_enabled is True:
                        self.current_selection_buttons[i[0]].enable()
                else:
                    self.current_selection_buttons[i[0]].enable()
            else:
                self.current_selection_buttons[i[0]].disable()
        # filter buttons
        for i in ["default", "alphabetical"]:
            if i in self.elements:
                if i == self.customiser_sort:
                    self.elements[i].disable()
                else:
                    self.elements[i].enable()

    def update_sprite(self):
        # this sucks
        if self.custom_cat.legacy_pelt.name in ["Tortie", "Calico"]:
            if self.custom_cat.legacy_pelt.tortie_pattern in ["Singlecolour", "SingleColour", "Twocolour", "TwoColour", "singlecolour", "twocolour"]:
                print("Correcting tortie_pattern:", self.custom_cat.legacy_pelt.tortie_pattern, "| Report as LifeGen bug!")
                self.custom_cat.legacy_pelt.tortie_pattern = "single"
            if self.custom_cat.legacy_pelt.tortie_base in ["Singlecolour", "SingleColour", "Twocolour", "TwoColour", "singlecolour", "twocolour"]:
                print("Correcting tortie_base:", self.custom_cat.legacy_pelt.tortie_base, "| Report as LifeGen bug!")
                self.custom_cat.legacy_pelt.tortie_base = "single"
        else:
            if self.custom_cat.legacy_pelt.name in ["single", "singlecolour", "Singlecolour"]:
                print("Correcting pelt name:", self.custom_cat.legacy_pelt.name, "| Report as LifeGen bug!")
                self.custom_cat.legacy_pelt.name = "SingleColour"

        self.custom_cat.moons = 1
        self.custom_cat.age = CatAge.KITTEN
        if self.preview_age == "adolescent":
            self.custom_cat.moons = 6
            self.custom_cat.age = CatAge.ADOLESCENT
        elif self.preview_age in ["young adult", "adult"]:
            self.custom_cat.moons = 12
            self.custom_cat.age = CatAge.YOUNG_ADULT
        elif self.preview_age == "elder":
            self.custom_cat.moons = 121
            self.custom_cat.age = CatAge.SENIOR
        elif self.preview_age == "newborn":
            self.custom_cat.moons = 0
            self.custom_cat.age = CatAge.NEWBORN

        initial_pelt = self.custom_cat.legacy_pelt
        new_pelt = LegacyPelt(
            name=initial_pelt.name,
            length=initial_pelt.length,
            colour=initial_pelt.colour,
            white_patches=initial_pelt.white_patches,
            eye_color=initial_pelt.eye_colour,
            eye_colour2=initial_pelt.eye_colour2,
            tortie_base=initial_pelt.tortie_base,
            tortie_colour=initial_pelt.tortie_colour,
            tortie_marking=initial_pelt.tortie_marking,
            tortie_pattern=initial_pelt.tortie_pattern,
            vitiligo=initial_pelt.vitiligo,
            points=initial_pelt.points,
            accessory=initial_pelt.accessory,
            inventory=initial_pelt.inventory,
            paralyzed=initial_pelt.paralyzed,
            scars=initial_pelt.scars,
            tint=initial_pelt.tint,
            skin=initial_pelt.skin,
            white_patches_tint=initial_pelt.white_patches_tint,
            newborn_sprite="newborn" + str(self.newborn_pose),
            kitten_sprite="kitten" + str(self.kitten_sprite),
            adol_sprite=(
                ("adolescent_short" + str(self.adolescent_pose))
                if initial_pelt.length != "long"
                else 
                ("adolescent_long" + str(self.adolescent_pose))),
            adult_sprite=(
                ("adult_short" + str(self.adult_pose))
                if initial_pelt.length != "long"
                else 
                ("adult_long" + str(self.adult_pose))),
            senior_sprite="senior" + str(self.elder_pose),
            para_adult_sprite= "para_adult_long0" if initial_pelt.length == "long" else "para_adult_short0",
            reverse=initial_pelt.reverse
        )

        new_pelt.apply_to_cat(self.custom_cat)

        # self.custom_cat = Cat(moons=self.custom_cat.moons, pelt=new_pelt, loading_cat=True)
        new_sprite = generate_sprite(self.custom_cat)

        if "sprite" in self.elements:
            self.elements['sprite'].kill()
        # Sprite
        self.elements["sprite"] = pygame_gui.elements.UIImage(
            ui_scale(pygame.Rect((0, 180), (175, 175))),
            pygame.transform.scale(
                new_sprite, ui_scale_dimensions((175, 175))
            ),
            manager=MANAGER,
            anchors={"centerx": "centerx"}
        )
        # -----
        
    
    def open_choose_background(self):
        # clear screen
        self.clear_all_page()
        self.sub_screen = "choose camp"

        # Next and previous buttons
        self.elements["previous_step"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((253, 645), (147, 30))),
            "buttons.previous_step",
            get_button_dict(ButtonStyles.MENU_LEFT, (147, 30)),
            object_id="@buttonstyles_menu_left",
            manager=MANAGER,
            starting_height=2
        )
        self.elements["next_step"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((0, 645), (147, 30))),
            "buttons.next_step",
            get_button_dict(ButtonStyles.MENU_RIGHT, (147, 30)),
            object_id="@buttonstyles_menu_right",
            manager=MANAGER,
            starting_height=2,
            anchors={"left_target": self.elements["previous_step"]},
        )

        # Biome buttons
        self.elements["forest_biome"] = UIImageButton(
            ui_scale(pygame.Rect((196, 100), (100, 46))),
            "screens.make_clan.Forest",
            object_id="#forest_biome_button",
            manager=MANAGER,
        )
        self.elements["mountain_biome"] = UIImageButton(
            ui_scale(pygame.Rect((304, 100), (106, 46))),
            "screens.make_clan.Mountainous",
            object_id="#mountain_biome_button",
            manager=MANAGER,
        )
        self.elements["plains_biome"] = UIImageButton(
            ui_scale(pygame.Rect((424, 100), (88, 46))),
            "screens.make_clan.Plains",
            object_id="#plains_biome_button",
            manager=MANAGER,
        )
        self.elements["beach_biome"] = UIImageButton(
            ui_scale(pygame.Rect((520, 100), (82, 46))),
            "screens.make_clan.Beach",
            object_id="#beach_biome_button",
            manager=MANAGER,
        )

        # Camp Art Choosing Tabs, Dummy buttons, will be overridden.
        self.tabs["tab1"] = UIImageButton(
            ui_scale(pygame.Rect((0, 0), (0, 0))), "", visible=False, manager=MANAGER
        )
        self.tabs["tab2"] = UIImageButton(
            ui_scale(pygame.Rect((0, 0), (0, 0))), "", visible=False, manager=MANAGER
        )
        self.tabs["tab3"] = UIImageButton(
            ui_scale(pygame.Rect((0, 0), (0, 0))), "", visible=False, manager=MANAGER
        )
        self.tabs["tab4"] = UIImageButton(
            ui_scale(pygame.Rect((0, 0), (0, 0))), "", visible=False, manager=MANAGER
        )
        self.tabs["tab5"] = UIImageButton(
            ui_scale(pygame.Rect((0, 0), (0, 0))), "", visible=False, manager=MANAGER
        )
        self.tabs["tab6"] = UIImageButton(
            ui_scale(pygame.Rect((0, 0), (0, 0))), "", visible=False, manager=MANAGER
        )
        self.tabs["tab7"] = UIImageButton(
            ui_scale(pygame.Rect((0, 0), (0, 0))), "", visible=False, manager=MANAGER
        )
        self.tabs["tab8"] = UIImageButton(
            ui_scale(pygame.Rect((0, 0), (0, 0))), "", visible=False, manager=MANAGER
        )
        self.tabs["tab9"] = UIImageButton(
            ui_scale(pygame.Rect((0, 0), (0, 0))), "", visible=False, manager=MANAGER
        )
        self.tabs["tab10"] = UIImageButton(
            ui_scale(pygame.Rect((0, 0), (0, 0))), "", visible=False, manager=MANAGER
        )

        self.tabs["newleaf_tab"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((625, 275), (39, 34))),
            Icon.NEWLEAF,
            get_button_dict(ButtonStyles.ICON_TAB_LEFT, (39, 36)),
            object_id="@buttonstyles_icon_tab_left",
            manager=MANAGER,
            tool_tip_text="screens.make_clan.season_tooltip",
            tool_tip_text_kwargs={"season": i18n.t("general.Newleaf")},
        )
        self.tabs["greenleaf_tab"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((625, 25), (39, 34))),
            Icon.GREENLEAF,
            get_button_dict(ButtonStyles.ICON_TAB_LEFT, (39, 36)),
            object_id="@buttonstyles_icon_tab_left",
            manager=MANAGER,
            tool_tip_text="screens.make_clan.season_tooltip",
            tool_tip_text_kwargs={"season": i18n.t("general.Greenleaf")},
            anchors={"top_target": self.tabs["newleaf_tab"]},
        )
        self.tabs["leaffall_tab"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((625, 25), (39, 34))),
            Icon.LEAFFALL,
            get_button_dict(ButtonStyles.ICON_TAB_LEFT, (39, 36)),
            object_id="@buttonstyles_icon_tab_left",
            manager=MANAGER,
            tool_tip_text="screens.make_clan.season_tooltip",
            tool_tip_text_kwargs={"season": i18n.t("general.Leaf-fall")},
            anchors={"top_target": self.tabs["greenleaf_tab"]},
        )
        self.tabs["leafbare_tab"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((625, 25), (39, 34))),
            Icon.LEAFBARE,
            get_button_dict(ButtonStyles.ICON_TAB_LEFT, (39, 36)),
            object_id="@buttonstyles_icon_tab_left",
            manager=MANAGER,
            tool_tip_text="screens.make_clan.season_tooltip",
            tool_tip_text_kwargs={"season": i18n.t("general.Leaf-bare")},
            anchors={"top_target": self.tabs["leaffall_tab"]},
        )
        # Random background
        self.elements["random_background"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((255, 595), (290, 30))),
            "screens.make_clan.choose_random_background",
            get_button_dict(ButtonStyles.SQUOVAL, (290, 30)),
            object_id="@buttonstyles_squoval",
            manager=MANAGER,
        )

        # art frame
        self.draw_art_frame()

    def open_choose_symbol(self):
        # clear screen
        self.clear_all_page()

        # set basics
        self.sub_screen = "choose symbol"
        
        switch_set_value(Switch.disallowed_symbol_tags, [])
        self.tag_list_len = 0

        self.elements["previous_step"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((253, 645), (147, 30))),
            "buttons.previous_step",
            get_button_dict(ButtonStyles.MENU_LEFT, (147, 30)),
            object_id="@buttonstyles_menu_left",
            manager=MANAGER,
            starting_height=2
        )
        self.elements["done_button"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((0, 645), (147, 30))),
            "buttons.done",
            get_button_dict(ButtonStyles.MENU_RIGHT, (147, 30)),
            object_id="@buttonstyles_menu_right",
            manager=MANAGER,
            starting_height=2,
            anchors={"left_target": self.elements["previous_step"]},
        )
        self.elements["done_button"].disable()

        # create screen specific elements
        self.elements["text_container"] = pygame_gui.elements.UIAutoResizingContainer(
            ui_scale(pygame.Rect((85, 105), (0, 0))),
            object_id="text_container",
            starting_height=1,
            manager=MANAGER,
        )
        self.text["clan_name"] = pygame_gui.elements.UILabel(
            ui_scale(pygame.Rect((0, 0), (-1, -1))),
            text="general.clan",
            text_kwargs={"name": self.clan_name},
            container=self.elements["text_container"],
            object_id=get_text_box_theme("#text_box_40"),
            manager=MANAGER,
            anchors={"left": "left"},
        )
        self.text["biome"] = pygame_gui.elements.UILabel(
            ui_scale(pygame.Rect((0, 5), (-1, -1))),
            text=f"screens.make_clan.{self.biome_selected}",
            container=self.elements["text_container"],
            object_id=get_text_box_theme("#text_box_30_horizleft"),
            manager=MANAGER,
            anchors={
                "top_target": self.text["clan_name"],
            },
        )
        self.text["leader"] = pygame_gui.elements.UILabel(
            ui_scale(pygame.Rect((0, 5), (-1, -1))),
            text=f"Your name: {self.your_cat.name}",
            # CHECKMERGE: lang file
            container=self.elements["text_container"],
            object_id=get_text_box_theme("#text_box_30_horizleft"),
            manager=MANAGER,
            text_kwargs={"prefix": self.your_cat.name.prefix},
            anchors={
                "top_target": self.text["biome"],
            },
        )
        self.text["recommend"] = pygame_gui.elements.UILabel(
            ui_scale(pygame.Rect((0, 5), (-1, -1))),
            text="screens.make_clan.symbol_recommended",
            container=self.elements["text_container"],
            object_id=get_text_box_theme("#text_box_30_horizleft"),
            manager=MANAGER,
            text_kwargs={
                "symbol": (
                    f"{self.clan_name.upper()}0"
                    if f"symbol{self.clan_name.upper()}0" in sprites.clan_symbols
                    else i18n.t("screens.make_clan.not_applicable")
                )
            },
            anchors={
                "top_target": self.text["leader"] if self.text.get("leader") else self.text["biome"],
            },
        )
        self.text["selected"] = pygame_gui.elements.UILabel(
            ui_scale(pygame.Rect((0, 15), (-1, -1))),
            text=f"screens.make_clan.symbol_selected",
            container=self.elements["text_container"],
            object_id=get_text_box_theme("#text_box_30_horizleft"),
            manager=MANAGER,
            text_kwargs={"symbol": i18n.t("screens.make_clan.not_applicable")},
            anchors={
                "top_target": self.text["recommend"],
            },
        )

        self.elements["random_symbol_button"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((496, 206), (34, 34))),
            Icon.DICE,
            get_button_dict(ButtonStyles.ICON, (34, 34)),
            object_id="@buttonstyles_icon",
            manager=MANAGER,
        )

        self.elements["symbol_frame"] = pygame_gui.elements.UIImage(
            ui_scale(pygame.Rect((540, 90), (169, 166))),
            get_box(BoxStyles.FRAME, (169, 166), sides=(True, True, False, True)),
            object_id="@boxstyles_frame",
            starting_height=1,
            manager=MANAGER,
        )

        self.elements["page_left"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((47, 414), (34, 34))),
            Icon.ARROW_LEFT,
            get_button_dict(ButtonStyles.ICON, (34, 34)),
            object_id="@buttonstyles_icon",
            starting_height=1,
            manager=MANAGER,
        )
        self.elements["page_right"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((719, 414), (34, 34))),
            Icon.ARROW_RIGHT,
            get_button_dict(ButtonStyles.ICON, (34, 34)),
            object_id="@buttonstyles_icon",
            starting_height=1,
            manager=MANAGER,
        )
        self.elements["filters_tab"] = UIImageButton(
            ui_scale(pygame.Rect((100, 619), (78, 30))),
            "",
            object_id="#filters_tab_button",
            starting_height=1,
            manager=MANAGER,
        )
        self.elements["symbol_list_frame"] = pygame_gui.elements.UIImage(
            ui_scale(pygame.Rect((76, 250), (650, 370))),
            get_box(BoxStyles.ROUNDED_BOX, (650, 370)),
            object_id="#symbol_list_frame",
            starting_height=2,
            manager=MANAGER,
        )

        if not self.symbol_selected:
            if f"symbol{self.clan_name.upper()}0" in sprites.clan_symbols:
                self.symbol_selected = f"symbol{self.clan_name.upper()}0"

                self.text["selected"].set_text(
                    "screens.make_clan.symbol_selected",
                    text_kwargs={"symbol": f"{self.clan_name.upper()}0"},
                )

        if self.symbol_selected:
            symbol_name = self.symbol_selected.replace("symbol", "")
            self.text["selected"].set_text(
                "screens.make_clan.symbol_selected", text_kwargs={"symbol": symbol_name}
            )

            self.elements["selected_symbol"] = pygame_gui.elements.UIImage(
                ui_scale(pygame.Rect((573, 127), (100, 100))),
                pygame.transform.scale(
                    sprites.get_symbol(self.symbol_selected),
                    ui_scale_dimensions((100, 100)),
                ).convert_alpha(),
                object_id="#selected_symbol",
                starting_height=2,
                manager=MANAGER,
            )
            self.refresh_symbol_list()
            while self.symbol_selected not in self.symbol_buttons:
                self.current_page += 1
                self.refresh_symbol_list()
            self.elements["done_button"].enable()
        else:
            self.elements["selected_symbol"] = pygame_gui.elements.UIImage(
                ui_scale(pygame.Rect((573, 127), (100, 100))),
                pygame.transform.scale(
                    sprites.sprites["symbolADDER0"],
                    ui_scale_dimensions((100, 100)),
                ).convert_alpha(),
                object_id="#selected_symbol",
                starting_height=2,
                manager=MANAGER,
                visible=False,
            )
            self.refresh_symbol_list()
    
    def refresh_symbol_list(self):
        # get symbol list
        symbol_list = sprites.clan_symbols.copy()
        symbol_attributes = sprites.symbol_dict

        # filtering out tagged symbols
        for symbol in sprites.clan_symbols:
            index = symbol[-1]
            name = symbol.strip("symbol1234567890")
            tags = symbol_attributes[name.capitalize()][f"tags{index}"]
            for tag in tags:
                if tag in switch_get_value(Switch.disallowed_symbol_tags):
                    if symbol in symbol_list:
                        symbol_list.remove(symbol)

        # separate list into chunks for pages
        symbol_chunks = self.chunks(symbol_list, 45)

        # clamp current page to a valid page number
        self.current_page = max(1, min(self.current_page, len(symbol_chunks)))

        # handles which arrow buttons are clickable
        if len(symbol_chunks) <= 1:
            self.elements["page_left"].disable()
            self.elements["page_right"].disable()
        elif self.current_page >= len(symbol_chunks):
            self.elements["page_left"].enable()
            self.elements["page_right"].disable()
        elif self.current_page == 1 and len(symbol_chunks) > 1:
            self.elements["page_left"].disable()
            self.elements["page_right"].enable()
        else:
            self.elements["page_left"].enable()
            self.elements["page_right"].enable()

        display_symbols = []
        if symbol_chunks:
            display_symbols = symbol_chunks[self.current_page - 1]

        # Kill all currently displayed symbols
        symbol_images = [ele for ele in self.elements if ele in sprites.clan_symbols]
        for ele in symbol_images:
            self.elements[ele].kill()
            if self.symbol_buttons:
                self.symbol_buttons[ele].kill()

        x_pos = 96
        y_pos = 270
        for symbol in display_symbols:
            self.elements[f"{symbol}"] = pygame_gui.elements.UIImage(
                ui_scale(pygame.Rect((x_pos, y_pos), (50, 50))),
                sprites.sprites[symbol],
                object_id=f"#{symbol}",
                starting_height=3,
                manager=MANAGER,
            )
            self.symbol_buttons[f"{symbol}"] = UIImageButton(
                ui_scale(pygame.Rect((x_pos - 12, y_pos - 12), (74, 74))),
                "",
                object_id=f"#symbol_select_button",
                starting_height=4,
                manager=MANAGER,
            )
            x_pos += 70
            if x_pos >= 715:
                x_pos = 96
                y_pos += 70

        if self.symbol_selected in self.symbol_buttons:
            self.symbol_buttons[self.symbol_selected].disable()


    def open_clan_saved_screen(self):
        self.clear_all_page()

        self.sub_screen = 'saved screen'

        if not switch_get_value(Switch.customise_new_life):
            # CHECKMERGE
            # maybe try again to put the customiser on its own screen....
            # no new clan symbol when youre just making a new mc
            self.elements["selected_symbol"] = pygame_gui.elements.UIImage(
                ui_scale(pygame.Rect((350, 105), (100, 100))),
                pygame.transform.scale(
                    sprites.sprites[self.symbol_selected], (100, 100)
                ).convert_alpha(),
                object_id="#selected_symbol",
                starting_height=1,
                manager=MANAGER,
            )

        self.elements["leader_image"] = pygame_gui.elements.UIImage(ui_scale(pygame.Rect((350, 120), (100, 100))),
                                                                    pygame.transform.scale(
                                                                        self.your_cat.sprite,
                                                                        (100, 100)), manager=MANAGER)
        self.elements["continue"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((346, 270), (102, 30))),
            "buttons.continue",
            get_button_dict(ButtonStyles.SQUOVAL, (102, 30)),
            manager=MANAGER,
            object_id="@buttonstyles_squoval",
            starting_height=1,
        )
        self.elements["save_confirm"] = pygame_gui.elements.UITextBox(
            'Welcome to the world, ' + str(self.your_cat.name) + "!",
            ui_scale(pygame.Rect((100, 235), (600, 30))),
            object_id=get_text_box_theme(
                "#text_box_30_horizcenter"),
            manager=MANAGER
            )
        
    def delete_example_cats(self):
        """ Deletes the other generated kits so they don't also get added to the Clan """
        key_copy = tuple(Cat.all_cats.keys())
        for i in key_copy:  # Going through all currently existing cats
            # cat_class is a Cat-object
            if i not in [game.clan.your_cat.ID] + self.current_members:
                Cat.all_cats[i].example = True
                self.remove_cat(Cat.all_cats[i].ID)

    def remove_cat(self, ID):  # ID is cat.ID
        """
        This function is for completely removing the cat from the game,
        it's not meant for a cat that's simply dead
        """

        if Cat.all_cats[ID] in Cat.all_cats_list:
            Cat.all_cats_list.remove(Cat.all_cats[ID])

        if ID in Cat.all_cats:
            Cat.all_cats.pop(ID)

        if ID in game.clan.clan_cats:
            game.clan.clan_cats.remove(ID)


    def save_clan(self):
        switch_set_value(
            Switch.error_message, ""
        )
        if switch_get_value(Switch.customise_new_life):
            self.your_cat.create_inheritance_new_cat()
            game.clan.your_cat = self.your_cat
            game.clan.your_cat.moons = -1
            game.clan.add_cat(game.clan.your_cat)
            self.delete_example_cats()
            return
        self.handle_create_other_cats()
        
        game.mediated.clear()
        game.told_story.clear()
        game.patrolled.clear()
        game.dated_cats.clear()
        game.just_died.clear()
        game.dead_cats_to_grieve.clear()
        save_load.faded_ids.clear()
        Cat.outside_cats.clear()
        Patrol.used_patrols.clear()
        convert_camp = f"camp{self.selected_camp_tab}"
        displayname = self.clan_name
        clan_name = sub(r"[/\\?%*:|\"<>\x7F\x00-\x1F]", "-", self.clan_name)
        if self._clan_name_exists(clan_name):
            clan_name = self._generate_unique_clan_name(clan_name)

        self.your_cat.create_inheritance_new_cat()

        new_social = CatSocial(self.social)
        if self.social != CatSocial.CLANCAT:
            new_rank = CatRank(new_social)
        else:
            new_rank = CatRank.KITTEN

        group_dict = {
            CatSocial.CLANCAT: CatGroup.PLAYER_CLAN_ID,
            CatSocial.ROGUE: CatGroup.ROGUE_GROUP_ID,
            CatSocial.LONER: CatGroup.LONER_GROUP_ID,
            CatSocial.KITTYPET: CatGroup.HOUSEHOLD_ID
        }

        self.your_cat.status.init_your_cat_status(
            rank=new_rank,
            group_ID=group_dict[self.social]
            )
        # TODO: prefix-only names are fucked

        game.clan = Clan(
            name = clan_name,
            displayname=displayname,
            leader = self.leader,
            deputy = self.deputy,
            medicine_cat = self.med_cat,
            biome = self.biome_selected,
            camp_bg = convert_camp if self.social == CatSocial.CLANCAT else "camp1",
            rogue_group_bg = convert_camp if self.social == CatSocial.ROGUE else "camp1",
            loner_group_bg = convert_camp if self.social == CatSocial.LONER else "camp1",
            household_bg = convert_camp if self.social == CatSocial.KITTYPET else "camp1",
            no_group_bg = convert_camp if self.social is None else "camp1",
            symbol=self.symbol_selected,
            game_mode="expanded",
            starting_members=self.members,
            starting_season=self.selected_season,
            your_cat=self.your_cat,
            clan_age=self.clan_age
        )
        game.clan.your_cat.moons = -1
        game.clan.create_clan(self.clan_count_mode)
        if self.clan_age == "established":
            game.clan.leader_lives = random.randint(1,9)
        game.cur_events_list.clear()
        EventsScreen.current_clan = None
        game.herb_events_list.clear()
        game.clan.herb_supply.start_storage(len(self.members))
        game.clan.save_herb_supply(game.clan)
        game.clan.grief_strings.clear()
        Cat.sort_cats()
        rebuild_top_menu_buttons()

        if not game.clan.your_cat.status.group.is_any_clan_group():
            game.clan.your_cat.specsuffix_hidden = True
            game.clan.your_cat.change_name(new_prefix=game.clan.your_cat.name.prefix, new_suffix="")
            # outsider games have no clan hunting patrols, so auto freshkill is on by default to keep the groups from starving
            set_clan_setting("freshkill", True)

    def get_camp_art_path(self, campnum) -> Optional[str]:
        if not campnum:
            return None

        leaf = self.selected_season.replace("-", "")

        camp_bg_base_dir = f"resources/images/camp_bg/{str(self.social).lower()}"
        start_leave = leaf.casefold()
        light_dark = "dark" if game_setting_get("dark mode") else "light"

        if self.biome_selected:
            biome = self.biome_selected.lower()
        else:
            biome = game.clan.biome

        return (
            f"{camp_bg_base_dir}/{biome}/{start_leave}_camp{campnum}_{light_dark}.png"
        )

    def draw_art_frame(self):
        if "art_frame" in self.elements:
            return
        self.elements["art_frame"] = pygame_gui.elements.UIImage(
            ui_scale(pygame.Rect(((0, 20), (466, 416)))),
            get_box(BoxStyles.FRAME, (466, 416)),
            manager=MANAGER,
            starting_height=2,
            anchors={"center": "center"},
        )

    def create_cat_info(self):
        self.elements["cat_name"] = pygame_gui.elements.UITextBox(
            "",
            ui_scale(pygame.Rect((0, 10), (250, 60))),
            visible=False,
            object_id=get_text_box_theme("#text_box_30_horizcenter"),
            manager=MANAGER,
            anchors={
                "top_target": self.elements["name_backdrop"],
                "centerx": "centerx",
            },
        )

        # info for chosen cats:
        if game_setting_get("dark mode"):
            self.elements["cat_info"] = pygame_gui.elements.UITextBox(
                "",
                ui_scale(pygame.Rect((440, 220), (175, 125))),
                visible=False,
                object_id=get_text_box_theme("#text_box_26_horizcenter_light"),
                manager=MANAGER,
            )
        else:
            self.elements["cat_info"] = pygame_gui.elements.UITextBox(
                "",
                ui_scale(pygame.Rect((440, 220), (175, 125))),
                visible=False,
                object_id=get_text_box_theme("#text_box_26_horizcenter"),
                manager=MANAGER,
            )

    def _clan_name_exists(self, new_clan_name: str):
        return new_clan_name.casefold() in (
            clan.casefold() for clan in switch_get_value(Switch.clan_list)
        )

    def _generate_unique_clan_name(self, new_clan_name: str):
        return f"{new_clan_name}_{uuid4()}"


make_clan_screen = MakeClanScreen()
