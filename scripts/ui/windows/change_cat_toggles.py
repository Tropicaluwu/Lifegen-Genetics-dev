import i18n
import pygame
import pygame_gui

from scripts.game_structure import game
from scripts.game_structure.screen_settings import MANAGER
from scripts.ui.elements.image_button import UIImageButton
from scripts.ui.elements.surface_image_button import UISurfaceImageButton
from scripts.ui.generate_button import get_button_dict, ButtonStyles
from scripts.ui.elements.checkbox import UICheckbox
from scripts.screens.enums import GameScreen
from scripts.ui.windows.window_base_class import GameWindow
from scripts.ui.scale import ui_scale


class CatToggleWindow(GameWindow):
    """This window allows the user to edit various cat behavior toggles"""

    cat_toggles = [
        "prevent_fading",
        "prevent_kits",
        "prevent_retirement",
        "prevent_romance",
        # LG
        "no_faith",
    ]

    # LG
    FAITH_LOCK_ORDER = ["flexible", "starclan", "dark forest", "neutral"]

    def __init__(self, cat):
        super().__init__(
            ui_scale(pygame.Rect((300, 200), (400, 280))),
        )
        self.the_cat = cat

        self.checkboxes = {}
        self.textbox = {}
        self.refresh_checkboxes()

        prev_element = None
        for text in self.cat_toggles:
            self.textbox[text] = pygame_gui.elements.UITextBox(
                f"windows.{text}",
                ui_scale(pygame.Rect(55, 0 if prev_element else 26, -1, 34)),
                object_id="#text_box_30_horizleft_pad_0_8",
                container=self,
                anchors={"top_target": prev_element} if prev_element else None,
            )
            prev_element = self.textbox[text]

        # LG
        self.faith_lock_button = UISurfaceImageButton(
            ui_scale(pygame.Rect((22, 205), (356, 30))),
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
        for ele in self.checkboxes:
            self.checkboxes[ele].kill()
        self.checkboxes = {}

        self.checkboxes["prevent_fading"] = UICheckbox(
            (22, 25),
            container=self,
            tool_tip_text=f"windows.prevent_fading_tooltip",
            check=self.the_cat.prevent_fading,
        )
        self.checkboxes["prevent_kits"] = UICheckbox(
            (22, 0),
            container=self,
            anchors={
                "top_target": self.checkboxes["prevent_fading"],
            },
            tool_tip_text=f"windows.prevent_kits_tooltip",
            check=self.the_cat.no_kits,
        )

        self.checkboxes["prevent_retirement"] = UICheckbox(
            (22, 0),
            container=self,
            anchors={
                "top_target": self.checkboxes["prevent_kits"],
            },
            tool_tip_text=f"windows.prevent_retirement_tooltip",
            check=self.the_cat.no_retire,
        )

        self.checkboxes["prevent_romance"] = UICheckbox(
            (22, 0),
            container=self,
            anchors={
                "top_target": self.checkboxes["prevent_retirement"],
            },
            tool_tip_text=f"windows.prevent_romance_tooltip",
            check=self.the_cat.no_mates,
        )

        # LG
        self.checkboxes["no_faith"] = UICheckbox(
            (22, 0),
            container=self,
            anchors={
                "top_target": self.checkboxes["prevent_romance"],
            },
            tool_tip_text="windows.no_faith_tooltip",
            check=self.the_cat.no_faith,
        )

        if self.the_cat in [game.clan.instructor] + [clan.instructor for clan in game.clan.all_other_clans if clan.instructor]:
            self.checkboxes["prevent_fading"].set_tooltip(
                "windows.prevent_fading_tooltip_guide"
            )
            self.checkboxes["prevent_fading"].disable()

    def process_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            if event.ui_element == self.back_button:
                game.all_screens[GameScreen.PROFILE].exit_screen()
                game.all_screens[GameScreen.PROFILE].screen_switches()
            elif event.ui_element == self.checkboxes["prevent_fading"]:
                self.checkboxes["prevent_fading"].toggle()
                self.the_cat.prevent_fading = self.checkboxes["prevent_fading"].checked
            elif event.ui_element == self.checkboxes["prevent_kits"]:
                self.checkboxes["prevent_kits"].toggle()
                self.the_cat.no_kits = self.checkboxes["prevent_kits"].checked
            elif event.ui_element == self.checkboxes["prevent_retirement"]:
                self.checkboxes["prevent_retirement"].toggle()
                self.the_cat.no_retire = self.checkboxes["prevent_retirement"].checked
            elif event.ui_element == self.checkboxes["prevent_romance"]:
                self.checkboxes["prevent_romance"].toggle()
                self.the_cat.no_mates = self.checkboxes["prevent_romance"].checked
            # LG
            elif event.ui_element == self.checkboxes["no_faith"]:
                self.checkboxes["no_faith"].toggle()
                self.the_cat.no_faith = self.checkboxes["no_faith"].checked
            elif event.ui_element == self.faith_lock_button:
                order = CatToggleWindow.FAITH_LOCK_ORDER
                try:
                    idx = order.index(self.the_cat.lock_faith)
                except ValueError:
                    idx = -1
                self.the_cat.lock_faith = order[(idx + 1) % len(order)]
                self.refresh_faith_lock_button()

        return super().process_event(event)
