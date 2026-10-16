import i18n
import pygame
import pygame_gui

from scripts.game_structure import game
from scripts.game_structure.screen_settings import MANAGER
from scripts.ui.elements.image_button import UIImageButton
from scripts.ui.elements.surface_image_button import UISurfaceImageButton
from scripts.ui.generate_button import get_button_dict, ButtonStyles
from scripts.screens.enums import GameScreen
from scripts.ui.windows.window_base_class import GameWindow
from scripts.ui.scale import ui_scale


class CatToggleWindow(GameWindow):
    """This window allows the user to edit various cat behavior toggles"""

    FAITH_LOCK_ORDER = ["flexible", "starclan", "dark forest", "neutral"]

    def __init__(self, cat):
        super().__init__(
            ui_scale(pygame.Rect((300, 200), (400, 240))),
        )
        self.the_cat = cat

        self.checkboxes = {}
        self.refresh_checkboxes()

        # Text
        self.text_1 = pygame_gui.elements.UITextBox(
            "windows.prevent_fading",
            ui_scale(pygame.Rect(55, 25, -1, 32)),
            object_id="#text_box_30_horizleft_pad_0_8",
            container=self,
        )

        self.text_2 = pygame_gui.elements.UITextBox(
            "windows.prevent_kits",
            ui_scale(pygame.Rect(55, 50, -1, 32)),
            object_id="#text_box_30_horizleft_pad_0_8",
            container=self,
        )

        self.text_3 = pygame_gui.elements.UITextBox(
            "windows.prevent_retirement",
            ui_scale(pygame.Rect(55, 75, -1, 32)),
            object_id="#text_box_30_horizleft_pad_0_8",
            container=self,
        )

        self.text_4 = pygame_gui.elements.UITextBox(
            "windows.prevent_romance",
            ui_scale(pygame.Rect(55, 100, -1, 32)),
            object_id="#text_box_30_horizleft_pad_0_8",
            container=self,
        )

        self.text_5 = pygame_gui.elements.UITextBox(
            "windows.no_faith",
            ui_scale(pygame.Rect(55, 125, -1, 32)),
            object_id="#text_box_30_horizleft_pad_0_8",
            container=self,
        )

        self.faith_lock_button = UISurfaceImageButton(
            ui_scale(pygame.Rect((22, 160), (356, 30))),
            "windows.faith_lock",
            get_button_dict(ButtonStyles.SQUOVAL, (356, 30)),
            object_id="@buttonstyles_squoval",
            text_kwargs=self.faith_lock_kwargs(),
            tool_tip_text="windows.faith_lock_tooltip",
            manager=MANAGER,
            container=self,
        )

    def faith_lock_kwargs(self):
        lock_key = self.the_cat.lock_faith.replace(" ", "_")
        return {"lock": i18n.t(f"windows.faith_lock_{lock_key}")}

    def refresh_faith_lock_button(self):
        self.faith_lock_button.set_text(
            "windows.faith_lock", text_kwargs=self.faith_lock_kwargs()
        )

    def refresh_checkboxes(self):
        for x in self.checkboxes.values():
            x.kill()
        self.checkboxes = {}

        # Prevent Fading
        if self.the_cat in [game.clan.instructor] + [clan.instructor for clan in game.clan.all_other_clans if clan.instructor]:
            box_type = "@checked_checkbox"
            tool_tip = "windows.prevent_fading_tooltip_guide"
        elif self.the_cat.prevent_fading:
            box_type = "@checked_checkbox"
            tool_tip = "windows.prevent_fading_tooltip"
        else:
            box_type = "@unchecked_checkbox"
            tool_tip = "windows.prevent_fading_tooltip"

        # Fading
        self.checkboxes["prevent_fading"] = UIImageButton(
            ui_scale(pygame.Rect((22, 25), (34, 34))),
            "",
            container=self,
            object_id=box_type,
            tool_tip_text=tool_tip,
        )

        if self.the_cat == game.clan.instructor:
            self.checkboxes["prevent_fading"].disable()

        # No Kits
        self.checkboxes["prevent_kits"] = UIImageButton(
            ui_scale(pygame.Rect((22, 50), (34, 34))),
            "",
            container=self,
            object_id=(
                "@checked_checkbox" if self.the_cat.no_kits else "@unchecked_checkbox"
            ),
            tool_tip_text="windows.prevent_kits_tooltip",
        )

        # No Retire
        self.checkboxes["prevent_retire"] = UIImageButton(
            ui_scale(pygame.Rect((22, 75), (34, 34))),
            "",
            container=self,
            object_id=(
                "@checked_checkbox" if self.the_cat.no_retire else "@unchecked_checkbox"
            ),
            tool_tip_text=(
                "windows.prevent_retirement_tooltip_yes"
                if self.the_cat.no_retire
                else "windows.prevent_retirement_tooltip_no"
            ),
        )

        # No mates
        self.checkboxes["prevent_mates"] = UIImageButton(
            ui_scale(pygame.Rect((22, 100), (34, 34))),
            "",
            container=self,
            object_id=(
                "@checked_checkbox" if self.the_cat.no_mates else "@unchecked_checkbox"
            ),
            tool_tip_text="windows.prevent_romance_tooltip",
        )

        # No faith
        self.checkboxes["no_faith"] = UIImageButton(
            ui_scale(pygame.Rect((22, 125), (34, 34))),
            "",
            container=self,
            object_id=(
                "@checked_checkbox" if self.the_cat.no_faith else "@unchecked_checkbox"
            ),
            tool_tip_text="windows.no_faith_tooltip",
        )

    def process_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            if event.ui_element == self.back_button:
                game.all_screens[GameScreen.PROFILE].exit_screen()
                game.all_screens[GameScreen.PROFILE].screen_switches()
            elif event.ui_element == self.checkboxes["prevent_fading"]:
                self.the_cat.prevent_fading = not self.the_cat.prevent_fading
                self.refresh_checkboxes()
                self.the_cat.pelt.rebuild_sprite = True
            elif event.ui_element == self.checkboxes["prevent_kits"]:
                self.the_cat.no_kits = not self.the_cat.no_kits
                self.refresh_checkboxes()
            elif event.ui_element == self.checkboxes["prevent_retire"]:
                self.the_cat.no_retire = not self.the_cat.no_retire
                self.refresh_checkboxes()
            elif event.ui_element == self.checkboxes["prevent_mates"]:
                self.the_cat.no_mates = not self.the_cat.no_mates
                self.refresh_checkboxes()
            elif event.ui_element == self.checkboxes["no_faith"]:
                self.the_cat.no_faith = not self.the_cat.no_faith
                self.refresh_checkboxes()
            elif event.ui_element == self.faith_lock_button:
                order = CatToggleWindow.FAITH_LOCK_ORDER
                try:
                    idx = order.index(self.the_cat.lock_faith)
                except ValueError:
                    idx = -1
                self.the_cat.lock_faith = order[(idx + 1) % len(order)]
                self.refresh_faith_lock_button()

        return super().process_event(event)
