"""LifeGen Genetics: tells the player a new version is out, and how to update without losing
their Clans (when playing from the source code, the saves are inside the game folder)."""
import pygame
import pygame_gui

from scripts.game_structure.screen_settings import MANAGER
from scripts.housekeeping import lgg_update
from scripts.housekeeping.datadir import open_url
from scripts.housekeeping.version import get_version_info
from scripts.ui.elements.surface_image_button import UISurfaceImageButton
from scripts.ui.generate_button import get_button_dict, ButtonStyles
from scripts.ui.scale import ui_scale
from scripts.ui.windows.window_base_class import GameWindow


class LGGUpdateWindow(GameWindow):
    def __init__(self):
        super().__init__(ui_scale(pygame.Rect((150, 150), (500, 400))))

        pygame_gui.elements.UITextBox(
            f"LifeGen Genetics {lgg_update.newer_version} is out!",
            ui_scale(pygame.Rect((0, 10), (500, -1))),
            object_id="#changelog_popup_title",
            container=self,
            manager=MANAGER,
        )
        pygame_gui.elements.UITextBox(
            f"You're playing {get_version_info().version_number}. To update:<br><br>"
            "1. On the download page, click the green <b>Code</b> button, then <b>Download ZIP</b>, and unzip it.<br><br>"
            "2. <b>Copy the saves folder</b> from this game's folder into the new one. "
            "Your Clans are in it, so don't skip this!<br><br>"
            "3. Play from the new folder. Once your Clans show up there, you can delete the old one.",
            ui_scale(pygame.Rect((15, 60), (470, 270))),
            object_id="#text_box_30",
            container=self,
            manager=MANAGER,
        )
        self.download_button = UISurfaceImageButton(
            ui_scale(pygame.Rect((90, 345), (170, 30))),
            "download page",
            get_button_dict(ButtonStyles.SQUOVAL, (170, 30)),
            object_id="@buttonstyles_squoval",
            container=self,
            manager=MANAGER,
        )
        self.later_button = UISurfaceImageButton(
            ui_scale(pygame.Rect((280, 345), (130, 30))),
            "later",
            get_button_dict(ButtonStyles.SQUOVAL, (130, 30)),
            object_id="@buttonstyles_squoval",
            container=self,
            manager=MANAGER,
        )

    def process_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            if event.ui_element == self.download_button:
                open_url(lgg_update.DOWNLOAD_PAGE)
                self.kill()
                return True
            if event.ui_element == self.later_button:
                self.kill()
                return True
        return super().process_event(event)
