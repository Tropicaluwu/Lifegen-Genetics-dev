"""The custom cat maker: starts from the picked cat (or a plain one) and edits its genes."""
import random
from copy import deepcopy
from random import choice

import i18n
import pygame
import pygame_gui
from pygame_gui.core import ObjectID

from scripts.cat import gene_menus
from scripts.cat.cats import Cat
from scripts.cat.conditions.gain_conditions import gain_permanent_condition
from scripts.cat.enums import CatAge, CatRank, CatSocial
from scripts.cat.factories.new_cat_factory import NewCatFactory
from scripts.cat.legacy_pelt import LegacyPelt
from scripts.cat.pelts import Pelt
from scripts.cat.personality import Personality
from scripts.cat.pronouns import get_default_pronouns
from scripts.cat.skills import SkillPath, Skill
from scripts.cat.sprites.display_sprites import generate_sprite
from scripts.cat.sprites.load_sprites import sprites
from scripts.game_structure import game
from scripts.game_structure.game.settings import game_setting_get
from scripts.game_structure.game.switches import switch_get_value, Switch
from scripts.game_structure.screen_settings import MANAGER, screen
from scripts.screens.enums import GameScreen
from scripts.screens.make_clan_screens.MakeClanScreenBase import MakeClanScreenBase
from scripts.ui.elements.image_button import UIImageButton
from scripts.ui.elements.modified_scrolling_container import UIModifiedScrollingContainer
from scripts.ui.elements.surface_image_button import UISurfaceImageButton
from scripts.ui.generate_box import get_box, BoxStyles
from scripts.ui.generate_button import ButtonStyles, get_button_dict
from scripts.ui.icon import Icon
from scripts.ui.scale import ui_scale, ui_scale_dimensions, ui_scale_offset
from scripts.ui.theme import get_text_box_theme


class TickBox(UIImageButton):
    """A cat maker checkbox. The tick is the button's own look, so it can't drop off when the
    button's state changes. disable() keeps meaning "this one is picked"."""

    def __init__(self, *args, object_id=None, **kwargs):
        super().__init__(*args, object_id=object_id, **kwargs)
        self.ticked = object_id == "@checked_checkbox_smalltooltip"

    def tick(self, ticked):
        if ticked != self.ticked:
            self.ticked = ticked
            style = "@checked_checkbox_smalltooltip" if ticked else "@unchecked_checkbox_smalltooltip"
            self.change_object_id(ObjectID(class_id="@image_button", object_id=style))

    def disable(self):
        self.tick(True)
        super().disable()

    def enable(self):
        self.tick(False)
        super().enable()


# accessories shown at a time in the accessory list (building all of them is slow)
ACC_PAGE = 60


class CustomCatScreen(MakeClanScreenBase):
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



    # LG: all accs
    if game_setting_get("lifegen_sprite_changes"):
        all_accs = (Pelt.all_lifegen_accessories)
    else:
        all_accs = (Pelt.all_clangen_accessories)

    # stays on the page when the page gets rebuilt
    KEEP_ELEMENTS = ("main_menu", "menu_warning")

    def __init__(self, name="custom_cat_screen"):
        super().__init__(name)
        self.custom_cat = None
        self.your_cat = None
        self.selected_cat = None
        self.customiser_button_dicts = []

    def reset_customizer(self):
        self.preview_age = "kitten"
        self.newborn_pose = 0
        self.kitten_sprite = 0
        self.adolescent_pose = 0
        self.adult_pose = 0
        self.elder_pose = 0
        
        self.opacity=100
        self.skill = "Random"
        self.personality = ""
        self.picked_conditions = []
        self.page = 0
        self.faith = "flexible"
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
        self.acc_limit = ACC_PAGE

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

        # Page 4, the fur and body genes
        self.mm_pattern = None
        self.mm_traits = set()
        self.mm_trait_buttons = {}
        self.mm_trait_names = {}
        self.mm_trait_category = "teeth"
        self.mm_category_buttons = {}

        # gene menus at the end of the lists (label: picked option, in the order picked)
        self.gene_edits = {}
        self.gene_menu_open = None  # (section, menu label) of the menu showing its options
        self.gene_menu_buttons = {}
        self.gene_option_buttons = {}
        self.gene_names = {}
        self.gene_seed = random.randrange(1000000)
        # white patches picked one by one (None: the genes pick them)
        self.white_picks = None
        self.white_buttons = {}
        self.white_rows = {}
        self.white_group = "White genes"
        self.gene_groups = {}
        self.saved_scroll = 0

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

            self.mm_trait_buttons,
            self.mm_trait_names,
            self.mm_category_buttons,
            self.gene_menu_buttons,
            self.gene_option_buttons,
            self.gene_names,
            self.white_buttons,

            self.sex_buttons
            ]

    def screen_switches(self):
        super().screen_switches()
        self.reset_customizer()
        # start from your cat if you're coming back to this page, or the cat picked on the last page
        picked = self.clan_info.your_cat
        if picked is None and switch_get_value(Switch.cat):
            picked = Cat.all_cats.get(switch_get_value(Switch.cat))
        self.selected_cat = picked
        self.open_customize_cat()
        self.update_sprite()

    @staticmethod
    def give_starting_condition(cat, name):
        """A condition picked in the cat maker ("born without a leg" is born_without_leg in the game)"""
        key = name.replace(" a ", " ").replace(" ", "_")
        gain_permanent_condition(cat, key, is_congenital=True, set_moons_until=1)
        if key not in cat.permanent_conditions:
            # some can't be there from birth
            gain_permanent_condition(cat, key)

    # conditions that can't go together, picking one swaps out the others
    CONDITION_CLASHES = (
        ("blind", "one bad eye", "failing eyesight"),
        ("deaf", "partial hearing loss"),
        ("born without a leg", "weak leg", "twisted leg", "paralyzed"),
    )

    def toggle_condition(self, name):
        """Picks a condition or takes it off, any number can be picked"""
        if name in self.picked_conditions:
            self.picked_conditions.remove(name)
        else:
            for group in self.CONDITION_CLASHES:
                if name in group:
                    self.picked_conditions = [c for c in self.picked_conditions if c not in group]
            self.picked_conditions.append(name)
        self.sync_condition_looks()

    def sync_condition_looks(self):
        """The scars and paralysis that go with the picked conditions"""
        legacy = self.custom_cat.legacy_pelt
        legacy.paralyzed = "paralyzed" in self.picked_conditions
        tied = {"NOPAW": "born without a leg", "NOTAIL": "born without a tail", "BOTHBLIND": "blind",
                "LEFTBLIND": "one bad eye", "RIGHTBLIND": "one bad eye", "BRIGHTHEART": "one bad eye"}
        scars = [scar for scar in (legacy.scars or ()) if tied.get(scar, "") in self.picked_conditions or scar not in tied]
        for scar in ("NOPAW", "NOTAIL"):
            if tied[scar] in self.picked_conditions and scar not in scars:
                scars.append(scar)
        legacy.scars = tuple(scars)

    def new_preview_cat(self, moons=2):
        """A cat for the preview, not part of the game"""
        cat = NewCatFactory.create_cat(rank=CatRank.KITTEN, moons=moons)
        Cat.all_cats.pop(cat.ID, None)
        if cat in Cat.all_cats_list:
            Cat.all_cats_list.remove(cat)
        cat.gender = {"tom": "male", "molly": "female"}.get(cat.gender, cat.gender)
        return cat

    def clear_all_page(self):
        """Clears the page, except the buttons that stay on every page"""
        for name in [n for n in self.elements if n not in self.KEEP_ELEMENTS]:
            self.elements.pop(name).kill()
        for item in self.customiser_button_dicts:
            for ele in item:
                item[ele].kill()

    def exit_screen(self):
        # the lists of buttons aren't in self.elements, so they have to go too
        self.clear_all_page()
        for item in self.customiser_button_dicts:
            item.clear()
        # the Clan creation screens put it back at the top when they open
        self.set_mute_button_position("bottomright")
        return super().exit_screen()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_START_PRESS and event.ui_element == self.elements.get("main_menu"):
            return super().handle_event(event)
        self.handle_customize_cat_event(event)
        return None

    def on_use(self):
        super().on_use()
        # put the list back where it was scrolled to (the scroll bar only exists once the
        # list has been drawn)
        if getattr(self, "pending_scroll", None):
            container = self.elements.get("scroll_container")
            # (wait until the list has been laid out once, or the scroll can't go anywhere)
            if container is not None and self.pending_scroll_waited:
                container.show()
                bar = getattr(container, "vert_scroll_bar", None)
                if bar:
                    # (showing it resets the scroll bar, so let that happen first)
                    container.update(0)
                    bar.update(0)
                    bar.set_scroll_from_start_percentage(self.pending_scroll)
                    bar.has_moved_recently = True  # so the list follows the scroll bar
                    container.update(0)
                self.pending_scroll = None
            self.pending_scroll_waited = True

    def randomize_custom_cat(self):
        permanent_conditions = ['born without a leg', 'weak leg', 'twisted leg', 'born without a tail', 'paralyzed', 'raspy lungs', 'wasting disease', 'blind', 'one bad eye', 'failing eyesight', 'partial hearing loss', 'deaf', 'constant joint pain', 'seizure prone', 'allergies', 'persistent headaches']

        self.custom_cat = self.new_preview_cat()
        self.mm_pattern = None
        self.saved_tortie = None
        self.base_genes = None
        self.base_chimera = None
        self.base_mm = None
        self.base_marking = None
        self.gene_edits = {}
        self.gene_menu_open = None
        self.gene_seed = random.randrange(1000000)
        self.white_picks = None

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

        # the looks come from a new cat made the way the game makes one (its genes, sex, fur,
        # poses...), like picking a cat to start from, so Random cat has the game's odds (the
        # random pelt above gave most cats white)
        rolled = self.new_preview_cat(moons=12)
        Cat.all_cats.pop(rolled.ID, None)
        if rolled in Cat.all_cats_list:
            Cat.all_cats_list.remove(rolled)
        self.tortie_enabled = False
        self.start_from_cat(rolled)

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
        self.picked_conditions = [choice(permanent_conditions)] if random.randint(1,30) == 1 else []

        if "born without a tail" in self.picked_conditions:
            for i in Pelt.tail_accessories:
                if i in self.custom_cat.legacy_pelt.accessory:
                    self.custom_cat.legacy_pelt.accessory = []
                    self.custom_cat.legacy_pelt.inventory = []
                    break
        if "born without a leg" in self.picked_conditions:
            for i in Pelt.paw_accessories:
                if i in self.custom_cat.legacy_pelt.accessory:
                    self.custom_cat.legacy_pelt.accessory = []
                    self.custom_cat.legacy_pelt.inventory = []
                    break

        # scars for conditions
        self.custom_cat.legacy_pelt.paralyzed = True if "paralyzed" in self.picked_conditions else False
        if "born without a tail" in self.picked_conditions:
            self.custom_cat.legacy_pelt.scars = ("NOTAIL",)
        elif "born without a leg" in self.picked_conditions:
            self.custom_cat.legacy_pelt.scars = ("NOPAW",)
        elif "blind" in self.picked_conditions:
            if random.randint(0,10) == 1:
                self.custom_cat.legacy_pelt.scars = ["BOTHBLIND"]
        elif "one bad eye" in self.picked_conditions:
            if random.randint(0,10) == 1:
                self.custom_cat.legacy_pelt.scars = (random.choice(["LEFTBLIND", "RIGHTBLIND", "BRIGHTHEART"]),)
        elif "deaf" in self.picked_conditions or "partial hearing loss" in self.picked_conditions:
            if random.randint(0,10) == 1:
                self.custom_cat.legacy_pelt.scars = (random.choice(["LEFTEAR", "RIGHTEAR", "NOEAR"]),)

        self.faith = random.choice(["flexible", "starclan", "dark forest", "neutral"])

    def open_customize_cat(self):

        self.clear_all_page()

        # self.selected_cat = None
        # clearing selected cat for the eye colour display bug


        # customizing starts from the cat picked on the previous screen (its exact
        # genes, see start_from_cat), or from a plain black cat
        if True:
            pelt2 = LegacyPelt(
                name="SingleColour",
                length="short",
                colour="BLACK",
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
                tint="none",
                skin="PINK",
                white_patches_tint="none",
                kitten_sprite=self.kitten_sprite,
                adol_sprite=self.adolescent_pose,
                adult_sprite=self.adult_pose,
                senior_sprite=self.elder_pose,
                para_adult_sprite= "para_adult_short0",
                reverse=False,
            )
            # CHECKCUSTOM make it an empty pelt

        # CREATE CUSTOM CAT
        self.custom_cat = self.new_preview_cat(moons=0)
        # no hidden genes from the random cat underneath (Random cat stays random)
        gene_menus.make_plain(self.custom_cat.phenotype)
        self.custom_cat.chimerapheno = None
        self.picked_conditions = []
        self.saved_tortie = None
        pelt2.apply_to_cat(self.custom_cat)

        if self.custom_cat.legacy_pelt.name in ["Tortie", "Calico"]:
            self.tortie_enabled = True
        else:
            self.tortie_enabled = False

        self.base_genes = None
        self.base_chimera = None
        self.base_mm = None
        self.base_marking = None
        self.base_vitiligo = None
        picked = getattr(self, "selected_cat", None)
        if picked is not None and getattr(picked, "phenotype", None) is not None:
            self.start_from_cat(picked)
        
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
        self.gene_menu_buttons.clear()
        self.gene_option_buttons.clear()
        self.gene_names.clear()
        self.white_buttons.clear()
        self.white_rows.clear()

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
        
        if self.page == 4:
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
                CustomCatScreen.sprite_preview_bg_dark,
                manager=MANAGER
                )
        else:
            self.elements['spritebg'] = pygame_gui.elements.UIImage(
                ui_scale(pygame.Rect((275, 125), (250, 285))),
                CustomCatScreen.sprite_preview_bg,
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
                ui_scale(pygame.Rect((535, 85), (190, 480))),
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
                self.elements["tortie_checkbox"] = TickBox(
                    ui_scale(pygame.Rect((x_pos + 60, selection_y_pos + 12), (30, 30))),
                    "",
                    object_id="@checked_checkbox_smalltooltip",
                    manager=MANAGER
                    )
            else:
                self.elements["tortie_checkbox"] = TickBox(
                    ui_scale(pygame.Rect((x_pos + 60, selection_y_pos + 12), (30, 30))),
                    "",
                    object_id="@unchecked_checkbox_smalltooltip",
                    manager=MANAGER
                    )
            
            selection_y_pos += 75
            # the patches always share the cat's pattern, so there's no tortie pattern
            # to pick. Their color: "Natural" (what a real tortie of this color has) or any other
            # color, which makes the cat a chimera
            for i in ["tortie_colour", "tortie_pattern", "tortie_patches"]:
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
                # Genemod's real tabby patterns (they replace LifeGen's pelt looks)
                pelt_y_pos = self.add_gene_option_rows("Tabby pattern", pelt_y_pos)

                # (no "match tortie": a tortie's patches always share its pattern now)
            elif self.current_selection == "pelt_colour":
                # Genemod's real colors (they replace LifeGen's colors)
                pelt_y_pos = self.add_gene_option_rows("Color", pelt_y_pos)

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
                    tint_x_pos += 45
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
                # the white genes and every white patch in one list (pick any patches)
                pelt_y_pos = self.add_white_rows(pelt_y_pos, self.search_text)

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
                # Genemod's real point types
                pelt_y_pos = self.add_gene_option_rows("Points", pelt_y_pos)
            elif self.current_selection == "vitiligo":
                for patch in ["None"] + LegacyPelt.vitiligo_markings:
                    self.vitiligo_buttons[patch] = TickBox(
                        ui_scale(pygame.Rect((x_pos, pelt_y_pos + 4), (34, 34))),
                        "",
                        object_id="@unchecked_checkbox_smalltooltip",
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
                pelt_y_pos = self.add_gene_option_rows("Tortie pattern", pelt_y_pos)
            elif self.current_selection == "tortie_colour":
                pelt_y_pos = self.add_gene_option_rows("Tortie color", pelt_y_pos)

            elif self.current_selection == "tortie_patches":
                for patch in LegacyPelt.tortie_patches:
                    self.tortie_patches_buttons[patch] = TickBox(
                        ui_scale(pygame.Rect((x_pos, pelt_y_pos + 4), (34, 34))),
                        "",
                        object_id="@unchecked_checkbox_smalltooltip",
                        container=self.elements["scroll_container"],
                        manager=MANAGER
                        )
                    self.tortie_patches_names[patch] = pygame_gui.elements.UITextBox(
                        gene_menus.patch_name(patch),
                        ui_scale(pygame.Rect((x_pos + 32, pelt_y_pos), (200, 34))),
                        object_id=get_text_box_theme("#text_box_30_horizleft"),
                        container=self.elements["scroll_container"],
                        manager=MANAGER
                    )
                    pelt_y_pos += 40

        elif self.page == 2:

            if self.current_selection not in [
                "eye_colour", "heterochromia", "scar", "accessory"
                ]:
                self.current_selection = "eye_colour"

            self.elements["scroll_container"] = UIModifiedScrollingContainer(
                ui_scale(pygame.Rect((535, 85), (190, 480))),
                manager=MANAGER,
                starting_height=1,
                allow_scroll_x=False,
                allow_scroll_y=True,
            )

            x_pos = 120
            eye_y_pos = 0
            selection_y_pos = 150
            # no skin: Genemod works out the nose and paw pads from the genes
            for i in ["eye_colour", "heterochromia", "scar", "accessory"]:
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
                if i == "heterochromia":
                    selection_y_pos += 60
                selection_y_pos += 50

            if self.current_selection == "eye_colour":
                # Genemod's eye colors (they replace LifeGen's)
                eye_y_pos = self.add_gene_option_rows("Both eyes", eye_y_pos)

            elif self.current_selection == "heterochromia":
                # the second eye's color
                eye_y_pos = self.add_gene_option_rows("Odd eye", eye_y_pos)

            elif self.current_selection == "skin":
                for colour in LegacyPelt.skin_sprites:
                    self.skin_buttons[str(colour)] = TickBox(
                    ui_scale(pygame.Rect((0, eye_y_pos), (34, 34))),
                    "",
                    object_id="@unchecked_checkbox_smalltooltip",
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
                # scars are check boxes (click again to take one off)
                for scar in ["None"] + LegacyPelt.all_scars:
                    checked = str(scar).upper() in (self.custom_cat.legacy_pelt.scars or ())
                    self.scar_buttons[str(scar)] = TickBox(
                    ui_scale(pygame.Rect((0, eye_y_pos), (34, 34))),
                    "",
                    object_id="@checked_checkbox_smalltooltip" if checked else "@unchecked_checkbox_smalltooltip",
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

                all_items = ["None"] + new_acc_list
                for acc in all_items[:self.acc_limit]:
                    self.accessory_buttons[acc] = TickBox(
                        ui_scale(pygame.Rect((0, eye_y_pos), (34, 34))),
                        "",
                        object_id="@unchecked_checkbox_smalltooltip",
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
                left = len(all_items) - self.acc_limit
                if left > 0:
                    self.elements["acc_more"] = UISurfaceImageButton(
                        ui_scale(pygame.Rect((0, eye_y_pos), (170, 30))),
                        f"Show more ({left})",
                        get_button_dict(ButtonStyles.SQUOVAL, (170, 30)),
                        object_id="@buttonstyles_squoval",
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
                ui_scale(pygame.Rect((535, 85), (190, 480))),
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

                    self.condition_buttons[condition] = TickBox(
                    ui_scale(pygame.Rect((0, y_pos), (34, 34))),
                    "",
                    object_id="@unchecked_checkbox_smalltooltip",
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

                    self.trait_buttons[trait] = TickBox(
                        ui_scale(pygame.Rect((0, y_pos), (34, 34))),
                        "",
                        object_id="@unchecked_checkbox_smalltooltip",
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

                    self.skill_buttons[skill] = TickBox(
                        ui_scale(pygame.Rect((0, y_pos), (34, 34))),
                        "",
                        object_id="@unchecked_checkbox_smalltooltip",
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
 
        if self.page == 4:
            # the fur and body genes
            if self.mm_trait_category not in self.MM_TRAIT_CATEGORIES:
                self.mm_trait_category = "genes_fur"
            self.elements["scroll_container"] = UIModifiedScrollingContainer(
                ui_scale(pygame.Rect((535, 85), (190, 480))),
                manager=MANAGER,
                starting_height=1,
                allow_scroll_x=False,
                allow_scroll_y=True,
            )
            selection_y_pos = 100
            for category, text in self.MM_TRAIT_CATEGORIES.items():
                self.mm_category_buttons[category] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((120, selection_y_pos), (120, 40))),
                    text,
                    get_button_dict(ButtonStyles.ROUNDED_RECT, (120, 40)),
                    object_id="@buttonstyles_rounded_rect",
                    manager=MANAGER,
                    starting_height=2
                )
                selection_y_pos += 50

        # gene menus at the end of the list
        self.add_gene_section()
        self.update_chimera_note()

    def refresh_scar_checks(self):
        """Redraws the scar checkboxes in place, checked for the scars the cat has"""
        scars = tuple(self.custom_cat.legacy_pelt.scars or ())
        for scar, button in list(self.scar_buttons.items()):
            if not button.alive():
                continue
            checked = scar.upper() in scars
            if ("@checked_checkbox_smalltooltip" in button.get_object_ids()) == checked:
                continue
            rect = button.get_relative_rect()
            container = button.ui_container
            enabled = button.is_enabled
            button.kill()
            self.scar_buttons[scar] = TickBox(
                rect,
                "",
                object_id="@checked_checkbox_smalltooltip" if checked else "@unchecked_checkbox_smalltooltip",
                container=container,
                manager=MANAGER
            )
            if not enabled:
                self.scar_buttons[scar].disable()

    def update_chimera_note(self):
        """a note under the cat when the tortie patches make it a chimera"""
        if "chimera_note" in self.elements:
            self.elements.pop("chimera_note").kill()
        if self.page == 1 and self.custom_cat.chimerapheno:
            reasons = [what for what, label, plain in (("color", "Tortie color", "Natural"),
                                                        ("pattern", "Tortie pattern", "Same as cat"))
                       if self.gene_edits.get(label, plain) != plain]
            self.elements["chimera_note"] = pygame_gui.elements.UITextBox(
                "Chimera: the patches have their own genes (" + " and ".join(reasons) + ")",
                ui_scale(pygame.Rect((260, 585), (280, 55))),
                object_id=get_text_box_theme("#text_box_22_horizcenter"),
                manager=MANAGER
            )

    MM_TRAIT_CATEGORIES = {"genes_fur": "fur genes", "genes_body": "body genes"}

    # lists that are a gene menu's options: (page, list) -> menu label
    GENE_LISTS = {(1, "pelt_pattern"): "Tabby pattern", (1, "pelt_colour"): "Color", (1, "points"): "Points",
                  (2, "eye_colour"): "Both eyes", (2, "heterochromia"): "Odd eye",
                  (1, "tortie_colour"): "Tortie color", (1, "tortie_pattern"): "Tortie pattern"}
    # and the gene menus that go at the end of each list, under "More:"
    GENE_SECTIONS = {
        (1, "pelt_pattern"): ["Tabby type", "Rufousing", "Belly rufousing", "Bleaching", "Ghosting",
                              "Pseudo-merle (silver cats)"],
        (1, "pelt_colour"): ["Silver", "Wideband", "Caramel or apricot", "Extension", "Sunshine", "Special red",
                             "Nose", "Saturation"],
        (2, "heterochromia"): ["Sectoral patch", "Sectoral color"],
    }
    # lists made of several gene menus, each under its own heading
    GENE_GROUPS = {
        (4, "genes_fur"): ["Fur type", "Satin", "Glitter"],
        (4, "genes_body"): [m.label for m in dict(gene_menus.TABS)["Body"]],
    }
    GENE_MENUS = {m.label: m for _, menus in gene_menus.TABS for m in menus}
    GENE_MENUS.update({m.label: m for m in gene_menus.EXTRA_MENUS})
    # (pangere isn't white, but pale markings look a lot like it)
    WHITE_GENE_MENUS = ["White", "Blue-eyed white", "Roan (karpati)", "Pangere"]
    WHITE_GROUPS = gene_menus.white_patch_groups()

    def gene_section(self):
        """The list the gene menus are added to on this page, like (1, "pelt_colour")"""
        if self.page == 4:
            return (4, self.mm_trait_category)
        return (self.page, self.current_selection)

    def add_gene_option_rows(self, label, y_pos):
        """A checkbox row for each option of a gene menu, from y_pos. Returns the y after them.
        The very long lists come in groups, one open at a time."""
        options = self.GENE_MENUS[label].options
        if len(options) <= 40:
            return self.add_option_rows(label, options, y_pos)
        # choices that aren't an eye color (like "None" for no odd eye) go above the groups
        y_pos = self.add_option_rows(label, [o for o in options if o not in gene_menus.EYES], y_pos)
        groups = {}
        for option in options:
            if option in gene_menus.EYES:
                groups.setdefault(gene_menus.eye_family(option), []).append(option)
        current = self.GENE_MENUS[label].read(self.custom_cat.phenotype)
        for family in gene_menus.EYE_FAMILIES:
            if family not in groups:
                continue
            open_now = self.gene_groups.get(label) == family
            self.gene_menu_buttons[("gene group", label, family)] = UISurfaceImageButton(
                ui_scale(pygame.Rect((0, y_pos + 2), (170, 34))),
                ("- " if open_now else "+ ") + family + ("  *" if current in groups[family] else ""),
                get_button_dict(ButtonStyles.ROUNDED_RECT, (170, 34)),
                object_id="@buttonstyles_rounded_rect",
                container=self.elements["scroll_container"],
                manager=MANAGER
            )
            y_pos += 40
            if open_now:
                y_pos = self.add_option_rows(label, groups[family], y_pos)
        return y_pos

    def add_option_rows(self, label, options, y_pos):
        for option in options:
            self.gene_option_buttons[(label, option)] = TickBox(
                ui_scale(pygame.Rect((0, y_pos + 4), (34, 34))),
                "",
                object_id="@unchecked_checkbox_smalltooltip",
                container=self.elements["scroll_container"],
                manager=MANAGER
            )
            self.gene_names[(label, option)] = pygame_gui.elements.UITextBox(
                gene_menus.short(option),
                ui_scale(pygame.Rect((32, y_pos), (200, 34))),
                object_id=get_text_box_theme("#text_box_30_horizleft"),
                container=self.elements["scroll_container"],
                manager=MANAGER
            )
            y_pos += 40
        return y_pos

    def add_white_rows(self, y_pos, searched):
        """The white list: buttons for each group (one open at a time, so the list stays short),
        the white genes (pick one each) and the patches (pick any number)"""
        container = self.elements["scroll_container"]
        searching = searched not in ["", "search", None]
        picked = self.current_white()
        groups = [("White genes", None), ("Picked patches", picked)]
        groups += self.WHITE_GROUPS
        for group, names in groups:
            open_now = group == self.white_group or searching
            if searching and (names is None or group == "Picked patches"):
                continue
            if not searching:
                self.gene_menu_buttons[("white group", group)] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((0, y_pos + 2), (170, 34))),
                    ("- " if open_now else "+ ") + group,
                    get_button_dict(ButtonStyles.ROUNDED_RECT, (170, 34)),
                    object_id="@buttonstyles_rounded_rect",
                    container=container,
                    manager=MANAGER
                )
                y_pos += 40
            if not open_now:
                continue
            if names is None:
                for label in self.WHITE_GENE_MENUS:
                    self.gene_names[("heading", label)] = pygame_gui.elements.UITextBox(
                        gene_menus.short(label) + ":",
                        ui_scale(pygame.Rect((0, y_pos), (200, 34))),
                        object_id=get_text_box_theme("#text_box_30_horizleft"),
                        container=container,
                        manager=MANAGER
                    )
                    y_pos = self.add_gene_option_rows(label, y_pos + 40)
                continue
            if group == "Picked patches":
                self.gene_menu_buttons["clear white"] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((0, y_pos + 2), (120, 34))),
                    "clear all",
                    get_button_dict(ButtonStyles.ROUNDED_RECT, (120, 34)),
                    object_id="@buttonstyles_rounded_rect",
                    container=container,
                    manager=MANAGER
                )
                y_pos += 40
            if group == "Color spots":
                self.gene_names[("white note", group)] = pygame_gui.elements.UITextBox(
                    "These take white away (a colored ear on a white cat...)",
                    ui_scale(pygame.Rect((0, y_pos), (170, 60))),
                    object_id=get_text_box_theme("#text_box_22_horizleft"),
                    container=container,
                    manager=MANAGER
                )
                y_pos += 60
            if searching:
                names = [n for n in names if searched.lower() in gene_menus.patch_name(n).lower()]
            for name in names:
                self.white_rows[name] = y_pos
                self.make_white_button(name, name in picked)
                self.gene_names[("white", name)] = pygame_gui.elements.UITextBox(
                    gene_menus.patch_name(name, group),
                    ui_scale(pygame.Rect((32, y_pos), (200, 34))),
                    object_id=get_text_box_theme("#text_box_30_horizleft"),
                    container=container,
                    manager=MANAGER
                )
                y_pos += 40
        return y_pos

    def make_white_button(self, name, checked):
        if name in self.white_buttons:
            self.white_buttons[name].kill()
        self.white_buttons[name] = TickBox(
            ui_scale(pygame.Rect((0, self.white_rows[name] + 4), (34, 34))),
            "",
            object_id="@checked_checkbox_smalltooltip" if checked else "@unchecked_checkbox_smalltooltip",
            container=self.elements["scroll_container"],
            manager=MANAGER
        )

    def current_white(self):
        """The white patches the cat has now (without vitiligo, which has its own list)"""
        patches = self.custom_cat.phenotype.white_pattern
        if patches in (None, "No"):
            return []
        return [p for p in patches if p not in LegacyPelt.vitiligo_markings]

    def toggle_white(self, name):
        old = self.current_white()
        if name in old:
            self.white_picks = [p for p in old if p != name]
        else:
            self.white_picks = old + [name]
        self.update_sprite()
        picked = self.current_white()
        for other in self.white_buttons:
            self.make_white_button(other, other in picked)

    def refresh_gene_buttons(self):
        """The picked option of each gene menu shows as picked"""
        genes = self.custom_cat.phenotype
        current = {}
        for (label, option), button in self.gene_option_buttons.items():
            if label not in current:
                if label in ("Tortie color", "Tortie pattern"):
                    current[label] = self.gene_edits.get(label, self.GENE_MENUS[label].options[0])
                else:
                    current[label] = self.GENE_MENUS[label].read(genes)
            if option == current[label] and not (label == "Tabby pattern" and self.mm_pattern):
                button.disable()
            else:
                button.enable()

    def add_gene_section(self):
        """Adds the gene menus for this list at its end, or shows the open menu's options instead"""
        section = self.gene_section()
        labels = self.GENE_SECTIONS.get(section)
        container = self.elements.get("scroll_container")
        if container is None:
            return
        if section in self.GENE_GROUPS:
            y = 0
            for label in self.GENE_GROUPS[section]:
                self.gene_names[("heading", label)] = pygame_gui.elements.UITextBox(
                    gene_menus.short(label) + ":",
                    ui_scale(pygame.Rect((0, y), (200, 34))),
                    object_id=get_text_box_theme("#text_box_30_horizleft"),
                    container=container,
                    manager=MANAGER
                )
                y = self.add_gene_option_rows(label, y + 40)
        if labels and self.gene_menu_open and self.gene_menu_open[0] == section:
            label = self.gene_menu_open[1]
            # the list shows this menu's options instead
            for element in list(container.scrollable_container.elements):
                element.kill()
            self.gene_option_buttons.clear()
            self.gene_names["title"] = pygame_gui.elements.UITextBox(
                label,
                ui_scale(pygame.Rect((0, 0), (170, 70))),
                object_id=get_text_box_theme("#text_box_30_horizleft"),
                container=container,
                manager=MANAGER
            )
            self.gene_menu_buttons["back"] = UISurfaceImageButton(
                ui_scale(pygame.Rect((0, 70), (120, 34))),
                "back",
                get_button_dict(ButtonStyles.ROUNDED_RECT, (120, 34)),
                object_id="@buttonstyles_rounded_rect",
                container=container,
                manager=MANAGER
            )
            self.add_gene_option_rows(label, 115)
        elif labels:
            # after the list's own rows (one text box each)
            rows = sum(1 for element in container.scrollable_container.elements
                       if isinstance(element, pygame_gui.elements.UITextBox))
            # lists in groups have a button for each group too
            rows += sum(1 for key in self.gene_menu_buttons if isinstance(key, tuple) and key[0] == "gene group")
            y = rows * 40
            if rows:
                self.gene_names["heading"] = pygame_gui.elements.UITextBox(
                    "More:",
                    ui_scale(pygame.Rect((0, y), (200, 34))),
                    object_id=get_text_box_theme("#text_box_30_horizleft"),
                    container=container,
                    manager=MANAGER
                )
                y += 40
            for label in labels:
                self.gene_menu_buttons[label] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((0, y + 2), (150, 34))),
                    gene_menus.short(label),
                    get_button_dict(ButtonStyles.ROUNDED_RECT, (150, 34)),
                    object_id="@buttonstyles_rounded_rect",
                    container=container,
                    manager=MANAGER
                )
                y += 40
            if self.gene_edits:
                self.gene_menu_buttons["reset"] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((0, y + 2), (150, 34))),
                    "reset genes",
                    get_button_dict(ButtonStyles.ROUNDED_RECT, (150, 34)),
                    object_id="@buttonstyles_rounded_rect",
                    container=container,
                    manager=MANAGER
                )
        self.refresh_gene_buttons()

    def list_scroll(self):
        """How far down the list is scrolled (0 to 1)"""
        bar = getattr(self.elements.get("scroll_container"), "vert_scroll_bar", None)
        return bar.start_percentage if bar else 0

    def set_list_scroll(self, amount):
        """Scrolls the list there once it's laid out (see on_use). It stays hidden until then,
        so it doesn't flash at the top first."""
        self.pending_scroll = amount or None
        self.pending_scroll_waited = False
        container = self.elements.get("scroll_container")
        if self.pending_scroll and container is not None:
            container.hide()

    def rebuild_keep_scroll(self):
        """Rebuilds the page, keeping the list where it was scrolled to"""
        amount = self.list_scroll()
        self.update_custom_cat_pages()
        self.update_disabled_buttons()
        self.set_list_scroll(amount)

    def pick_gene(self, label, option):
        self.gene_edits.pop(label, None)
        self.gene_edits[label] = option
        if label == "Tabby pattern":
            self.mm_pattern = None
        self.update_sprite()
        self.update_disabled_buttons()
        self.refresh_gene_buttons()
        if label in ("Tortie color", "Tortie pattern"):
            # the chimera note comes and goes (without redrawing the list, so it doesn't jump)
            self.update_chimera_note()

    def handle_gene_click(self, element):
        """Clicks on the gene menus and lists. True if it was one of them."""
        for label, button in list(self.gene_menu_buttons.items()):
            if element == button and isinstance(label, tuple) and label[0] == "white group":
                self.white_group = None if self.white_group == label[1] else label[1]
                self.rebuild_keep_scroll()
                return True
            if element == button and isinstance(label, tuple) and label[0] == "gene group":
                was_open = self.gene_groups.get(label[1]) == label[2]
                self.gene_groups[label[1]] = None if was_open else label[2]
                self.rebuild_keep_scroll()
                return True
            if element == button and label == "clear white":
                # no white at all, so the white genes go too (dominant white, salmiak,
                # karpati roan and blue-eyed white draw white without any patches, and pangere's
                # pale markings look just like white)
                for gene, option in (("White", "None"), ("Roan (karpati)", "No"), ("Blue-eyed white", "None"),
                                     ("Pangere", "None")):
                    self.gene_edits.pop(gene, None)
                    self.gene_edits[gene] = option
                self.white_picks = []
                self.update_sprite()
                self.rebuild_keep_scroll()
                return True
            if element == button:
                scroll = 0
                if label == "back":
                    # back where the list was when the menu was opened
                    self.gene_menu_open = None
                    scroll = self.saved_scroll
                elif label == "reset":
                    self.gene_edits = {}
                    self.update_sprite()
                    scroll = self.list_scroll()
                else:
                    self.saved_scroll = self.list_scroll()
                    self.gene_menu_open = (self.gene_section(), label)
                self.update_custom_cat_pages()
                self.update_disabled_buttons()
                self.set_list_scroll(scroll)
                return True
        for (label, option), button in list(self.gene_option_buttons.items()):
            if element == button:
                if label == "White":
                    self.white_picks = None
                self.pick_gene(label, option)
                if label == "White" and self.white_buttons:
                    picked = self.current_white()
                    for other in self.white_buttons:
                        self.make_white_button(other, other in picked)
                return True
        for name, button in list(self.white_buttons.items()):
            if element == button:
                self.toggle_white(name)
                return True
        # the arrows and dice under the cat go through a gene list too
        label = None
        if self.gene_menu_open and self.gene_menu_open[0] == self.gene_section():
            label = self.gene_menu_open[1]
        elif self.gene_section() in self.GENE_LISTS:
            label = self.GENE_LISTS[self.gene_section()]
        steps = {self.elements.get("cycle_left"): -1, self.elements.get("cycle_right"): 1}
        if label and (element in steps or element == self.elements.get("randomise_selection")):
            options = self.GENE_MENUS[label].options
            current = self.GENE_MENUS[label].read(self.custom_cat.phenotype)
            if element in steps:
                index = options.index(current) if current in options else -1
                option = options[(index + steps[element]) % len(options)]
            else:
                option = random.choice(options)
            self.pick_gene(label, option)
            return True
        return False

    def apply_gene_edits(self, cat, final=False):
        """the gene menus' picks, on top of the genes made from the pelt picks"""
        if not self.gene_edits and self.white_picks is None:
            return
        genes = cat.phenotype
        tabs = {m.label: tab for tab, menus in gene_menus.TABS for m in menus}
        edited = {tabs.get(label) for label in self.gene_edits}
        eyes = {attr: getattr(genes, attr) for attr in (
            "lefteye", "righteye", "lefteyetype", "righteyetype", "extraeye", "extraeyetype", "extraeyecolour")}
        white_pattern, tortiepattern = genes.white_pattern, genes.tortiepattern
        genes.maker_eyes = None
        for label, option in self.gene_edits.items():
            self.GENE_MENUS[label].write(genes, option)
        # a tortie with patches of a color a real tortie can't have: a chimera, the patches
        # being a second set of genes in that color
        chimera_color = self.gene_edits.get("Tortie color", "Natural")
        chimera_pattern = self.gene_edits.get("Tortie pattern", "Same as cat")
        is_chimera = self.tortie_enabled and (chimera_color != "Natural" or chimera_pattern != "Same as cat")
        if is_chimera:
            patches = [p.replace("rev", "") for p in (genes.tortiepattern.get("0") or ["ONE"])]
            if chimera_color == "Natural":
                # the color a real tortie's patches would have
                chimera_color = gene_menus.RED_COLORS[(gene_menus.shown(genes, "dilute"),
                                                       gene_menus.shown(genes, "pinkdilute"))]
            gene_menus.set_tortie(genes, "No")
            genes.tortiepattern = {}
            chimera = deepcopy(genes)
            gene_menus.set_color(chimera, chimera_color)
            if chimera_pattern != "Same as cat":
                # the patches keep their own pattern whatever the main pattern is
                gene_menus.set_pattern(chimera, chimera_pattern)
            chimera.chimerapattern = patches
            chimera.GeneSort()
            chimera.PolyEval()
            cat.chimerapheno = chimera
        # Genemod picks some details by chance; a fixed seed keeps them still between clicks
        state = random.getstate()
        random.seed(self.gene_seed)
        genes.GeneSort()
        genes.PolyEval()
        genes.EyeColourFinder()
        if "Eyes" in edited or "Both eyes" in self.gene_edits or "Odd eye" in self.gene_edits:
            gene_menus.apply_maker_eyes(genes)
        else:
            for attr, value in eyes.items():
                setattr(genes, attr, value)
        genes.white_pattern = []
        genes.PhenotypeOutput(genes.white_pattern)
        genes.SpriteInfo(cat.moons)
        genes.tortiepattern = tortiepattern if genes.tortiepattern and tortiepattern else genes.tortiepattern
        if cat.chimerapheno and is_chimera:
            genes.tortiepattern = {}
            chimera = cat.chimerapheno
            for attr in ("lefteye", "righteye", "lefteyetype", "righteyetype", "extraeye", "extraeyetype",
                         "extraeyecolour", "white_pattern"):
                setattr(chimera, attr, deepcopy(getattr(genes, attr)))
            chimera.PhenotypeOutput(chimera.white_pattern)
            chimera.SpriteInfo(cat.moons)
        if self.white_picks is not None:
            # picked one by one (vitiligo stays, it has its own list)
            vitiligo = [p for p in (white_pattern if isinstance(white_pattern, list) else [])
                        if p in LegacyPelt.vitiligo_markings]
            genes.white_pattern = vitiligo + list(self.white_picks)
            # the white genes match how much white was picked, so kits get about that much
            if "W" not in genes.white:
                genes.white, grade = gene_menus.white_genes_for(self.white_picks)
                if grade:
                    genes.whitegrade = grade
        elif "White" in edited:
            genes.white_pattern = Pelt.generate_white(
                genes.white, genes.pointgene, genes.whitegrade, genes.vitiligo, None, genes.pax3)
        else:
            genes.white_pattern = white_pattern
        random.setstate(state)
        # fur length can change, and the poses go with it
        cat.pelt.length = Pelt(genes).length
        fur = "long" if cat.pelt.length == "long" else "short"
        for age, pose in cat.pelt.cat_sprites.items():
            if isinstance(pose, str):
                cat.pelt.cat_sprites[age] = pose.replace("_long", "_" + fur).replace("_short", "_" + fur)
        if final:
            cat.genetic_conditions(False)
        cat.pelt.rebuild_sprite = True

    def mm_category_traits(self):
        return []

    def make_mm_trait_button(self, trait, y_pos):
        """A checkbox for one physical trait (checked when picked; any number can be picked)"""
        self.mm_trait_buttons[trait] = TickBox(
            ui_scale(pygame.Rect((0, y_pos * 40 + 4), (34, 34))),
            "",
            object_id="@checked_checkbox_smalltooltip" if trait in self.mm_traits else "@unchecked_checkbox_smalltooltip",
            container=self.elements["scroll_container"],
            manager=MANAGER
        )

    def start_from_cat(self, picked):
        """the cat maker starts as this cat: its genes (hidden ones too), sex, fur, poses,
        scars and accessories. Every list shows its picks, and changes go on top."""
        self.base_genes = deepcopy(picked.phenotype)
        self.base_chimera = deepcopy(picked.chimerapheno)
        # the sex buttons use "male"/"female", cats use "tom"/"molly"
        self.custom_cat.gender = {"tom": "male", "molly": "female"}.get(picked.gender, picked.gender)
        self.custom_cat.genderalign = picked.genderalign
        pelt = self.custom_cat.legacy_pelt
        pelt.length = picked.pelt.length if picked.pelt.length in ("short", "medium", "long") else "short"
        pelt.scars = tuple(scar for scar in (picked.pelt.scars or ()) if scar in LegacyPelt.all_scars)
        marks = self.vitiligo_marks(picked.phenotype)
        self.base_vitiligo = "KARPATI" if "K" in picked.phenotype.karp else (marks[0] if marks else None)
        pelt.vitiligo = self.base_vitiligo
        pelt.accessory = list(picked.pelt.accessory or [])
        pelt.inventory = list(pelt.accessory)
        pelt.reverse = picked.pelt.reverse
        pelt.tint = picked.pelt.tint if picked.pelt.tint else "none"
        pelt.white_patches_tint = picked.pelt.white_patches_tint if picked.pelt.white_patches_tint else "none"
        # the poses (each pose name ends in its number)
        poses = picked.pelt.cat_sprites
        for age, attr in (("newborn", "newborn_pose"), ("kitten", "kitten_sprite"), ("adolescent", "adolescent_pose"),
                          ("adult", "adult_pose"), ("senior", "elder_pose")):
            pose = str(poses.get(age, ""))
            if pose[-1:].isdigit():
                setattr(self, attr, int(pose[-1]))
        # a tortie (or a chimera with patches) starts with Tortie ticked
        genes = self.base_genes
        patches = genes.tortiepattern.get("0") or (self.base_chimera.chimerapattern if self.base_chimera else None)
        if gene_menus.get_tortie(genes) != "No" or self.base_chimera:
            self.tortie_enabled = True
            marking = str((patches or ["ONE"])[0]).replace("rev", "")
            pelt.name = "Tortie"
            pelt.tortie_base = "single"
            pelt.tortie_pattern = "single"
            pelt.tortie_colour = "GINGER"
            pelt.tortie_marking = marking
            self.base_marking = marking
        self.base_mm = None
        self.gene_edits = {}
        self.white_picks = None

    @staticmethod
    def vitiligo_marks(genes):
        patches = genes.white_pattern
        return [p for p in patches if p in LegacyPelt.vitiligo_markings] if isinstance(patches, list) else []

    def apply_base_genes(self, cat):
        """the picked cat's genes, under the changes made in the cat maker"""
        legacy = cat.legacy_pelt
        genes = deepcopy(self.base_genes)
        cat.phenotype = genes
        cat.pelt.phenotype = genes
        cat.chimerapheno = deepcopy(self.base_chimera)
        gene_menus.set_sex(genes, {"male": "Tom", "tom": "Tom", "female": "Molly", "molly": "Molly"}.get(cat.gender, "Intersex"))
        changed = False
        was_tortie = gene_menus.get_tortie(genes) != "No"
        if self.tortie_enabled:
            if not was_tortie and not cat.chimerapheno:
                gene_menus.set_tortie(genes, "Tortie")
                changed = True
            marking = legacy.tortie_marking
            if marking and marking != self.base_marking:
                # other patches picked
                if cat.chimerapheno:
                    cat.chimerapheno.chimerapattern = [marking]
                else:
                    genes.tortiepattern = {"0": [marking]}
            elif not genes.tortiepattern and not cat.chimerapheno:
                genes.tortiepattern = {"0": [marking or "ONE"]}
        else:
            if was_tortie:
                gene_menus.set_tortie(genes, "No")
                genes.tortiepattern = {}
                changed = True
            cat.chimerapheno = None
        # a different marking was picked (the old one comes off)
        picked_mark = legacy.vitiligo
        if picked_mark != self.base_vitiligo:
            changed = True
            if isinstance(genes.white_pattern, list):
                genes.white_pattern = [p for p in genes.white_pattern if p not in LegacyPelt.vitiligo_markings]
            genes.vitiligo = False
            genes.karp = ["K", "k"] if picked_mark == "KARPATI" else ["k", "k"]
            if picked_mark and picked_mark != "KARPATI":
                # a cat with no white has "No" here, not a list
                if not isinstance(genes.white_pattern, list):
                    genes.white_pattern = []
                genes.white_pattern.insert(0, picked_mark)
                genes.vitiligo = True
        if changed:
            genes.GeneSort()
            genes.PhenotypeOutput(genes.white_pattern)
            genes.SpriteInfo(cat.moons)
        # its fur length, and the poses that go with it
        cat.pelt.length = Pelt(genes).length
        fur = "long" if cat.pelt.length == "long" else "short"
        for age, pose in cat.pelt.cat_sprites.items():
            if isinstance(pose, str):
                cat.pelt.cat_sprites[age] = pose.replace("_long", "_" + fur).replace("_short", "_" + fur)
        cat.pelt.rebuild_sprite = True

    def apply_extra_picks(self, cat):
        """(nothing to do here: there are no extra patterns or traits)"""
        return

    def handle_customize_cat_event(self, event):
        pelt_options = []
        for category in LegacyPelt.pelt_categories:
            if category == "torties":
                continue
            pelt_options += LegacyPelt.pelt_categories[category]
        pelt_options.remove("TwoColour")

        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            # the gene menus at the end of the lists
            if self.handle_gene_click(event.ui_element):
                return
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
                        now = self.picked_conditions[-1] if self.picked_conditions else "None"
                        next_index = (permanent_conditions.index(now) + num) % len(permanent_conditions)
                        self.picked_conditions = []
                        if permanent_conditions[next_index] != "None":
                            self.toggle_condition(permanent_conditions[next_index])
                        else:
                            self.sync_condition_looks()
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

                        if "born without a tail" in self.picked_conditions:
                            for i in Pelt.tail_accessories:
                                if i in new_acc_list:
                                    new_acc_list.remove(i)
                        if "born without a leg" in self.picked_conditions:
                            for i in Pelt.paw_accessories:
                                if i in new_acc_list:
                                    new_acc_list.remove(i)
                        
                        acc = choice(new_acc_list)

                        self.custom_cat.legacy_pelt.accessory = [acc]
                        self.custom_cat.legacy_pelt.inventory = [acc]

                elif self.page == 3:
                    if self.current_selection == "condition":
                        permanent_conditions = ['None', 'born without a leg', 'weak leg', 'twisted leg', 'born without a tail', 'paralyzed', 'raspy lungs', 'wasting disease', 'blind', 'one bad eye', 'failing eyesight', 'partial hearing loss', 'deaf', 'constant joint pain', 'seizure prone', 'allergies', 'persistent headaches']

                        self.picked_conditions = []
                        picked = random.choice(permanent_conditions)
                        if picked != "None":
                            self.toggle_condition(picked)
                        else:
                            self.sync_condition_looks()
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
                self.acc_limit = ACC_PAGE
                self.update_custom_cat_pages()
                self.update_sprite()
                self.update_disabled_buttons()
            if "acc_more" in self.elements and event.ui_element == self.elements["acc_more"]:
                container = self.elements.get("scroll_container")
                bar = getattr(container, "vert_scroll_bar", None)
                where = bar.start_percentage if bar else 0
                self.acc_limit += ACC_PAGE
                self.update_custom_cat_pages()
                self.update_disabled_buttons()
                # stay where the list was, it only got longer
                bar = getattr(self.elements.get("scroll_container"), "vert_scroll_bar", None)
                if bar:
                    try:
                        bar.set_scroll_from_start_percentage(where * (self.acc_limit - ACC_PAGE) / self.acc_limit)
                    except Exception:
                        pass
                return
            if "clear" in self.elements and event.ui_element == self.elements["clear"]:
                self.search_text = ""
                self.previous_search_text = self.search_text
                self.acc_limit = ACC_PAGE
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
                        # fur length comes from the genes (the picked cat's genes would keep
                        # its old length), so this sets the fur length gene
                        self.gene_edits.pop("Fur length", None)
                        self.gene_edits["Fur length"] = i[0].capitalize()
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
                        # kept, so ticking it again brings the same tortie back
                        pelt = self.custom_cat.legacy_pelt
                        self.saved_tortie = {
                            "legacy": (pelt.tortie_colour, pelt.tortie_pattern, pelt.tortie_marking),
                            "genes": {label: self.gene_edits.pop(label) for label in ("Tortie color", "Tortie pattern")
                                      if label in self.gene_edits},
                        }
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
                        self.custom_cat.legacy_pelt.tortie_pattern = self.custom_cat.legacy_pelt.tortie_base
                        self.custom_cat.legacy_pelt.tortie_marking = "ONE"
                        # the tortie it was before it was unticked
                        saved = getattr(self, "saved_tortie", None)
                        if saved:
                            colour, pattern, marking = saved["legacy"]
                            self.custom_cat.legacy_pelt.tortie_colour = colour or "GINGER"
                            self.custom_cat.legacy_pelt.tortie_pattern = pattern or self.custom_cat.legacy_pelt.tortie_base
                            self.custom_cat.legacy_pelt.tortie_marking = marking or "ONE"
                            self.gene_edits.update(saved["genes"])
                    self.update_sprite()
                    self.rebuild_keep_scroll()
                for i in self.pelt_pattern_buttons.items():
                    if event.ui_element == self.pelt_pattern_buttons[i[0]]:
                        # (LifeGen's pelt looks; the gene patterns have their own buttons)
                        self.mm_pattern = i[0][3:] if i[0].startswith("MM:") else None
                        if self.mm_pattern:
                            self.gene_edits.pop("Tabby pattern", None)
                        pelt = "Tabby" if self.mm_pattern else i[0]
                        if self.custom_cat.legacy_pelt.name == "Tortie":
                            self.custom_cat.legacy_pelt.tortie_base = pelt.lower()
                        else:
                            self.custom_cat.legacy_pelt.name = pelt
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
                            # (the conditions that come with those scars go too)
                            self.picked_conditions = [c for c in self.picked_conditions if c not in (
                                "born without a leg", "born without a tail", "blind", "one bad eye")]
                        else:
                            # any number of scars, click again to take one off
                            scars = tuple(self.custom_cat.legacy_pelt.scars or ())
                            if i[0].upper() in scars:
                                self.custom_cat.legacy_pelt.scars = tuple(x for x in scars if x != i[0].upper())
                                lost = {"NOPAW": "born without a leg", "NOTAIL": "born without a tail",
                                        "BOTHBLIND": "blind"}.get(i[0].upper())
                                if lost in self.picked_conditions:
                                    self.picked_conditions.remove(lost)
                                self.update_sprite()
                                self.update_disabled_buttons()
                                self.refresh_scar_checks()
                                return
                            self.custom_cat.legacy_pelt.scars = scars + (i[0].upper(),)
                            comes_with = {"NOPAW": "born without a leg", "NOTAIL": "born without a tail",
                                          "BOTHBLIND": "blind", "RIGHTBLIND": "one bad eye", "LEFTBLIND": "one bad eye",
                                          "BRIGHTHEART": "one bad eye"}.get(i[0])
                            if comes_with and comes_with not in self.picked_conditions:
                                self.toggle_condition(comes_with)
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
                        break
            elif self.page == 3:
                for i in self.condition_buttons.items():
                    if event.ui_element == self.condition_buttons[i[0]]:
                        if i[0] == "None":
                            self.picked_conditions = []
                            self.sync_condition_looks()
                        else:
                            self.toggle_condition(i[0])
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
            elif self.page == 4:
                for category, button in self.mm_category_buttons.items():
                    if event.ui_element == button:
                        self.mm_trait_category = category
                        self.update_custom_cat_pages()
                        self.update_disabled_buttons()
                        return

            for i in self.current_selection_buttons.items():
                if event.ui_element == self.current_selection_buttons[i[0]]:
                    self.current_selection = i[0]
                    self.acc_limit = ACC_PAGE
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

            if event.ui_element == self.elements['right']:
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
                self.your_cat = NewCatFactory.create_cat(rank=CatRank.KITTEN, moons=1, gender=self.custom_cat.gender)
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
                # the same chance rolls as the preview, so your cat looks like the preview
                state = random.getstate()
                random.seed(self.gene_seed)
                new_pelt.apply_to_cat(self.your_cat)
                self.apply_extra_picks(self.your_cat)
                self.apply_gene_edits(self.your_cat)
                random.setstate(state)
                # your cat gets exactly the preview's genes (the genes the lists
                # don't set would otherwise come from a new random cat)
                self.your_cat.phenotype = deepcopy(self.custom_cat.phenotype)
                self.your_cat.chimerapheno = deepcopy(self.custom_cat.chimerapheno)
                self.your_cat.pelt.phenotype = self.your_cat.phenotype
                self.your_cat.pelt.length = self.custom_cat.pelt.length
                self.your_cat.pelt.rebuild_sprite = True
                self.your_cat.gender = self.your_cat.phenotype.sex
                # (the conditions from the new cat's random genes go first)
                self.your_cat.permanent_conditions = []
                self.your_cat.genetic_conditions(False)

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

                for condition in self.picked_conditions:
                    self.give_starting_condition(self.your_cat, condition)
                for scar, condition in (("NOTAIL", "born without a tail"), ("NOPAW", "born without a leg")):
                    if condition in self.picked_conditions and scar not in self.your_cat.pelt.scars:
                        self.your_cat.pelt.scars = (*self.your_cat.pelt.scars, scar)
                self.your_cat.personality = Personality(trait=self.personality, kit_trait=True)
                if self.skill == "Random":
                    self.skill = random.choice(self.skills)
                self.your_cat.skills.primary = Skill.get_skill_from_string(Skill, self.skill, "True")
                self.your_cat.lock_faith = self.faith
                self.clan_info.your_cat = self.your_cat
                self.selected_cat = None
                self.custom_cat = None
                # the rest of the Clan is made here too (not in a new life, the Clan's already there)
                if not switch_get_value(Switch.customise_new_life) and not self.clan_info.leader:
                    self.fill_clan_members(
                        self.get_config_during_creation("clan_creation.ranks_needed.leader"),
                        self.get_config_during_creation("clan_creation.ranks_needed.deputy"),
                        self.get_config_during_creation("clan_creation.ranks_needed.medicine_cat"),
                    )
                self.change_screen(GameScreen.MAKE_CLAN_YOUR_NAME)
            elif event.ui_element == self.elements['previous_step']:
                self.selected_cat = None
                self.custom_cat = None
                self.change_screen(GameScreen.MAKE_CLAN_CHOOSE_CATS)

    def update_disabled_buttons(self):
        if self.page == 4:
            for category, button in self.mm_category_buttons.items():
                if category == self.mm_trait_category:
                    button.disable()
                else:
                    button.enable()
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
                # the length the cat really has (from its genes)
                if self.custom_cat.pelt.length != i:
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
                if self.mm_pattern:
                    pattern = "MM:" + self.mm_pattern
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
                    self.scar_buttons[i[0]].enable()
                if self.custom_cat.legacy_pelt.paralyzed is True:
                    for scar in ["BRIGHTHEART", "LEFTBLIND", "RIGHTBLIND", "BOTHBLIND", "NOPAW", "NOTAIL"]:
                        self.scar_buttons[scar].disable()
            self.refresh_scar_checks()
            for i in self.accessory_buttons.items():
                if i[0] == "None" and not self.custom_cat.legacy_pelt.accessory:
                    self.accessory_buttons[i[0]].disable()
                else:
                    if i[0] not in self.custom_cat.legacy_pelt.accessory:
                        self.accessory_buttons[i[0]].enable()
                    else:
                        self.accessory_buttons[i[0]].disable()
                if "born without a tail" in self.picked_conditions:
                    for acc in Pelt.tail_accessories:
                        if acc in self.accessory_buttons:
                            self.accessory_buttons[acc].disable()
                if "born without a leg" in self.picked_conditions:
                    for acc in Pelt.paw_accessories:
                        if acc in self.accessory_buttons:
                            self.accessory_buttons[acc].disable()

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

                if self.picked_conditions:
                    label = self.picked_conditions[0].capitalize() if len(self.picked_conditions) == 1 \
                        else f"{len(self.picked_conditions)} conditions"
                    self.elements["condition_name"] = pygame_gui.elements.UITextBox(
                        label,
                        ui_scale(pygame.Rect((300, 470), (200, 34))),
                        object_id=get_text_box_theme("#text_box_30_horizcenter"),
                        manager=MANAGER
                    )

            for i in self.condition_buttons.items():
                if i[0] == "None" and not self.picked_conditions:
                    self.condition_buttons[i[0]].disable()
                else:
                    # picked ones stay clickable, that's how they come off
                    self.condition_buttons[i[0]].enable()
                    self.condition_buttons[i[0]].tick(i[0] in self.picked_conditions)

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

        # 2 moons, so the kitten preview shows the real eye color (not blue kitten eyes)
        self.custom_cat.moons = 2
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

        # the sex picked is the cat's genetic sex too (tortie toms keep both X genes)
        gene_menus.set_sex(self.custom_cat.phenotype,
                           {"male": "Tom", "tom": "Tom", "female": "Molly", "molly": "Molly"}.get(self.custom_cat.gender, "Intersex"))
        # the same chance rolls every time, so clicking an option doesn't reroll the eyes or
        # patches (Random cat picks a new seed)
        state = random.getstate()
        random.seed(self.gene_seed)
        new_pelt.apply_to_cat(self.custom_cat)
        if getattr(self, "base_genes", None) is not None:
            self.apply_base_genes(self.custom_cat)
        self.apply_extra_picks(self.custom_cat)
        self.apply_gene_edits(self.custom_cat)
        random.setstate(state)

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
