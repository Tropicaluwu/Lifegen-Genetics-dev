import os

import pygame
import pygame_gui

from scripts.cat import custom_names
from scripts.cat.names import Name, names
from scripts.game_structure.screen_settings import MANAGER
from scripts.housekeeping.datadir import get_save_dir
from scripts.ui.elements.image_button import UIImageButton
from scripts.ui.elements.modified_scrolling_container import UIModifiedScrollingContainer
from scripts.ui.elements.surface_image_button import UISurfaceImageButton
from scripts.game_structure import constants
from scripts.game_structure.game.settings import game_setting_get
from scripts.ui.generate_button import get_button_dict, ButtonStyles
from scripts.ui.theme import get_text_box_theme
from scripts.ui.scale import ui_scale
from scripts.ui.windows.window_base_class import GameWindow

ALL_SAVES = "All saves"
PAGE_SIZE = 50
# how each list writes its names, like the game's own lists
STYLE = {
    "normal_prefixes": "capital", "normal_suffixes": "lower", "loner_names": "capital",
    "human_names": "capital", "clan_prefixes": "capital", "inappropriate_names": "lower",
}
NOTES = {
    "normal_prefixes": "The first half of a name (Bright-). Cats are mostly named after their looks, so pick how often yours are used below.",
    "normal_suffixes": "The second half of a name (-heart). Cats mostly get suffixes from their looks and personality, so pick how often yours are used below.",
    "special_suffixes": "The endings cats have at some ranks (-kit, -paw, -star). Pick one and type a new ending.",
    "loner_names": "Names for loners and rogues.",
    "human_names": "Names for kittypets.",
    "clan_prefixes": "Names for Clans (Thunder-, River-). Normal prefixes can be Clan names too.",
    "inappropriate_names": "Full names a cat should never get (like brightheart). They're checked without capitals.",
}


def save_names():
    """The saves there are (their folder names)"""
    try:
        files = os.listdir(get_save_dir())
    except OSError:
        return []
    return sorted(name[:-len("clan.json")] for name in files
                  if name.endswith("clan.json") and os.path.isdir(os.path.join(get_save_dir(), name[:-len("clan.json")])))


class NamesEditorWindow(GameWindow):
    """Add and take out names in the game's name lists, for all saves or for one save"""

    def __init__(self, save=None):
        super().__init__(ui_scale(pygame.Rect((60, 50), (680, 600))))
        if game_setting_get("dark mode"):
            # the game's windows are always light: this one follows dark mode
            background = pygame.Surface(self.get_container().get_size())
            background.fill(constants.CONFIG["theme"]["dark_mode_background"])
            pygame_gui.elements.UIImage(
                pygame.Rect((0, 0), background.get_size()),
                background,
                container=self,
                manager=MANAGER,
            )
        self.scope = save if save in save_names() else None
        self.list_name = "Prefixes"
        self.search = ""
        self.page = 0
        self.editing_rank = None
        self.rows = {}
        self.data = custom_names.load(self.scope)

        pygame_gui.elements.UITextBox(
            "Names",
            ui_scale(pygame.Rect((0, 8), (300, 40))),
            object_id=get_text_box_theme("#text_box_34_horizcenter"),
            container=self,
            manager=MANAGER,
            anchors={"centerx": "centerx"},
        )
        pygame_gui.elements.UITextBox(
            "Changes for:",
            ui_scale(pygame.Rect((20, 52), (130, 34))),
            object_id=get_text_box_theme("#text_box_30_horizleft"),
            container=self,
            manager=MANAGER,
        )
        options = [ALL_SAVES] + save_names()
        self.scope_menu = pygame_gui.elements.UIDropDownMenu(
            options,
            self.scope or ALL_SAVES,
            ui_scale(pygame.Rect((150, 52), (240, 34))),
            container=self,
            manager=MANAGER,
        )
        self.scope_note = pygame_gui.elements.UITextBox(
            "",
            ui_scale(pygame.Rect((400, 48), (260, 44))),
            object_id=get_text_box_theme("#text_box_22_horizleft"),
            container=self,
            manager=MANAGER,
        )

        self.list_buttons = {}
        for i, list_name in enumerate(custom_names.LISTS):
            self.list_buttons[list_name] = UISurfaceImageButton(
                ui_scale(pygame.Rect((20, 100 + i * 42), (150, 36))),
                list_name.lower(),
                get_button_dict(ButtonStyles.ROUNDED_RECT, (150, 36)),
                object_id="@buttonstyles_rounded_rect",
                container=self,
                manager=MANAGER,
            )
        self.note = pygame_gui.elements.UITextBox(
            "",
            ui_scale(pygame.Rect((15, 400), (165, 190))),
            object_id=get_text_box_theme("#text_box_22_horizleft"),
            container=self,
            manager=MANAGER,
        )

        self.search_box = pygame_gui.elements.UITextEntryLine(
            ui_scale(pygame.Rect((190, 100), (200, 32))),
            placeholder_text="search",
            container=self,
            manager=MANAGER,
        )
        self.prev_button = UISurfaceImageButton(
            ui_scale(pygame.Rect((400, 99), (34, 34))),
            "<",
            get_button_dict(ButtonStyles.ICON, (34, 34)),
            object_id="@buttonstyles_icon",
            container=self,
            manager=MANAGER,
        )
        self.page_text = pygame_gui.elements.UITextBox(
            "",
            ui_scale(pygame.Rect((436, 100), (180, 34))),
            object_id=get_text_box_theme("#text_box_22_horizcenter"),
            container=self,
            manager=MANAGER,
        )
        self.next_button = UISurfaceImageButton(
            ui_scale(pygame.Rect((618, 99), (34, 34))),
            ">",
            get_button_dict(ButtonStyles.ICON, (34, 34)),
            object_id="@buttonstyles_icon",
            container=self,
            manager=MANAGER,
        )
        self.list_box = None

        self.entry = pygame_gui.elements.UITextEntryLine(
            ui_scale(pygame.Rect((190, 482), (240, 34))),
            placeholder_text="a new name",
            container=self,
            manager=MANAGER,
        )
        self.add_button = UISurfaceImageButton(
            ui_scale(pygame.Rect((436, 481), (90, 36))),
            "add",
            get_button_dict(ButtonStyles.ROUNDED_RECT, (90, 36)),
            object_id="@buttonstyles_rounded_rect",
            container=self,
            manager=MANAGER,
        )
        self.reset_button = UISurfaceImageButton(
            ui_scale(pygame.Rect((532, 481), (125, 36))),
            "reset list",
            get_button_dict(ButtonStyles.ROUNDED_RECT, (125, 36)),
            object_id="@buttonstyles_rounded_rect",
            container=self,
            manager=MANAGER,
            tool_tip_text="Undo every change to this list (for the save picked above)",
        )
        self.only_mine_box = None
        self.share_buttons = {}
        self.option_elements = []
        self.refresh_list()

    # --- what's shown ---------------------------------------------------------------------------

    @property
    def key(self):
        return custom_names.LISTS[self.list_name]

    def base_names(self):
        """The lists before this save's changes: the game's (for all saves), or the game's with the
        all-saves changes (for one save)"""
        if self.scope is None:
            return Name.default_names
        return custom_names.combined(Name.default_names)

    def rows_now(self):
        """(name, what it is) for this list: "added", "in" (one of the lists' names) or "out" """
        base = self.base_names().get(self.key, [])
        if self.key == "special_suffixes":
            endings = dict(base)
            endings.update(self.data["rank_endings"])
            return [(rank, "changed" if rank in self.data["rank_endings"] else "in") for rank in endings]
        changes = custom_names.list_changes(self.data, self.key)
        removed = {name.lower() for name in changes["removed"]}
        rows = [(name, "added") for name in changes["added"]]
        rows += [(name, "out" if (changes["only_mine"] or name.lower() in removed) else "in")
                 for name in base if name not in changes["added"]]
        if self.search:
            rows = [row for row in rows if self.search.lower() in row[0].lower()]
        return rows

    def refresh_list(self):
        """Redraws the list and the options under it"""
        for list_name, button in self.list_buttons.items():
            if list_name == self.list_name:
                button.disable()
            else:
                button.enable()
        self.scope_note.set_text("(every save)" if self.scope is None else "(on top of the all-saves changes)")
        self.note.set_text(NOTES[self.key])
        rows = self.rows_now()
        pages = max(1, (len(rows) + PAGE_SIZE - 1) // PAGE_SIZE)
        self.page = max(0, min(self.page, pages - 1))
        self.page_text.set_text(f"page {self.page + 1} of {pages} ({len(rows)})")
        self.prev_button.enable() if self.page > 0 else self.prev_button.disable()
        self.next_button.enable() if self.page < pages - 1 else self.next_button.disable()

        if self.list_box:
            self.list_box.kill()
        self.rows = {}
        self.list_box = UIModifiedScrollingContainer(
            ui_scale(pygame.Rect((190, 140), (470, 335))),
            container=self,
            manager=MANAGER,
            allow_scroll_x=False,
            allow_scroll_y=True,
        )
        endings = dict(self.base_names().get("special_suffixes", {}))
        endings.update(self.data["rank_endings"])
        for i, (name, state) in enumerate(rows[self.page * PAGE_SIZE:(self.page + 1) * PAGE_SIZE]):
            y = i * 38
            if self.key == "special_suffixes":
                text = f"{name}: -{endings.get(name, '')}" + ("  (changed)" if state == "changed" else "")
                action = "change"
            else:
                text = name + {"added": "  (yours)", "out": "  (taken out)", "in": ""}[state]
                action = {"added": "delete", "out": "bring back", "in": "take out"}[state]
            pygame_gui.elements.UITextBox(
                text,
                ui_scale(pygame.Rect((0, y), (320, 34))),
                object_id=get_text_box_theme("#text_box_30_horizleft"),
                container=self.list_box,
                manager=MANAGER,
            )
            button = UISurfaceImageButton(
                ui_scale(pygame.Rect((322, y + 2), (125, 32))),
                action,
                get_button_dict(ButtonStyles.ROUNDED_RECT, (125, 32)),
                object_id="@buttonstyles_rounded_rect",
                container=self.list_box,
                manager=MANAGER,
            )
            only_mine = self.key != "special_suffixes" and custom_names.list_changes(self.data, self.key)["only_mine"]
            if state == "out" and only_mine:
                button.disable()  # (only your names are used: nothing to bring back one by one)
            self.rows[button] = (name, state)

        self.refresh_options()

    def refresh_options(self):
        """The options under the list: "only my names", how often yours are used"""
        for element in self.option_elements:
            element.kill()
        self.option_elements = []
        self.share_buttons = {}
        self.only_mine_box = None
        self.add_button.set_text("set" if self.key == "special_suffixes" else "add")
        if self.key == "special_suffixes":
            text = f"New ending for {self.editing_rank}:" if self.editing_rank else "Pick a rank to change its ending."
            self.option_elements.append(pygame_gui.elements.UITextBox(
                text, ui_scale(pygame.Rect((190, 522), (470, 34))),
                object_id=get_text_box_theme("#text_box_22_horizleft"), container=self, manager=MANAGER))
            return
        changes = custom_names.list_changes(self.data, self.key)
        self.only_mine_box = UIImageButton(
            ui_scale(pygame.Rect((190, 524), (34, 34))),
            "",
            object_id="@checked_checkbox" if changes["only_mine"] else "@unchecked_checkbox",
            container=self,
            manager=MANAGER,
            tool_tip_text="Leave out all of the game's names in this list",
        )
        self.option_elements.append(self.only_mine_box)
        self.option_elements.append(pygame_gui.elements.UITextBox(
            "only use my names", ui_scale(pygame.Rect((226, 524), (190, 34))),
            object_id=get_text_box_theme("#text_box_22_horizleft"), container=self, manager=MANAGER))
        if self.key in ("normal_prefixes", "normal_suffixes") and not changes["only_mine"]:
            self.option_elements.append(pygame_gui.elements.UITextBox(
                "use mine:", ui_scale(pygame.Rect((190, 560), (90, 30))),
                object_id=get_text_box_theme("#text_box_22_horizleft"), container=self, manager=MANAGER))
            share = changes.get("share")
            if share is None and self.scope is not None:
                # this save hasn't picked one: it follows the all-saves choice
                share = custom_names.list_changes(custom_names.load(), self.key).get("share")
            share = share or custom_names.DEFAULT_SHARE
            for i, option in enumerate(custom_names.SHARES):
                button = UISurfaceImageButton(
                    ui_scale(pygame.Rect((270 + i * 96, 558), (92, 32))),
                    option,
                    get_button_dict(ButtonStyles.ROUNDED_RECT, (92, 32)),
                    object_id="@buttonstyles_rounded_rect",
                    container=self,
                    manager=MANAGER,
                )
                if option == share:
                    button.disable()
                self.share_buttons[button] = option
                self.option_elements.append(button)

    # --- changes --------------------------------------------------------------------------------

    def tidy(self, text):
        text = " ".join(text.split())
        style = STYLE.get(self.key)
        if style == "lower":
            return text.lower()
        if style == "capital" and text:
            return text[0].upper() + text[1:]
        return text

    def save_changes(self):
        custom_names.save(self.data, self.scope)
        # the game uses the new lists straight away
        if Name.current_clan:
            names.load_clan_names(Name.current_clan)
        else:
            Name.names_dict = custom_names.combined(Name.default_names)
            Name.custom = custom_names.merged_info()

    def add_name(self):
        text = self.tidy(self.entry.get_text())
        if not text:
            return
        if self.key == "special_suffixes":
            if self.editing_rank:
                self.data["rank_endings"][self.editing_rank] = text.lower().lstrip("-")
                self.editing_rank = None
        else:
            changes = custom_names.list_changes(self.data, self.key)
            removed = [name for name in changes["removed"] if name.lower() == text.lower()]
            if removed and not changes["only_mine"]:
                # one of the game's names that was taken out: bring it back
                for name in removed:
                    changes["removed"].remove(name)
            elif text not in changes["added"]:
                changes["added"].append(text)
        self.entry.set_text("")
        self.save_changes()
        self.refresh_list()

    def row_action(self, name, state):
        if self.key == "special_suffixes":
            self.editing_rank = name
            endings = dict(self.base_names().get("special_suffixes", {}))
            endings.update(self.data["rank_endings"])
            self.entry.set_text(endings.get(name, ""))
            self.refresh_options()
            return
        changes = custom_names.list_changes(self.data, self.key)
        if state == "added":
            changes["added"].remove(name)
        elif state == "in":
            changes["removed"].append(name)
        else:
            changes["removed"] = [n for n in changes["removed"] if n.lower() != name.lower()]
        self.save_changes()
        self.refresh_list()

    def process_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            element = event.ui_element
            if element in self.list_buttons.values():
                self.list_name = next(n for n, b in self.list_buttons.items() if b == element)
                self.page, self.editing_rank = 0, None
                self.search_box.set_text("")
                self.search = ""
                self.refresh_list()
            elif element == self.add_button:
                self.add_name()
            elif element == self.reset_button:
                if self.key == "special_suffixes":
                    self.data["rank_endings"] = {}
                else:
                    self.data["lists"].pop(self.key, None)
                self.save_changes()
                self.refresh_list()
            elif element == self.prev_button:
                self.page -= 1
                self.refresh_list()
            elif element == self.next_button:
                self.page += 1
                self.refresh_list()
            elif element == self.only_mine_box:
                changes = custom_names.list_changes(self.data, self.key)
                changes["only_mine"] = not changes["only_mine"]
                self.save_changes()
                self.refresh_list()
            elif element in self.share_buttons:
                custom_names.list_changes(self.data, self.key)["share"] = self.share_buttons[element]
                self.save_changes()
                self.refresh_options()
            elif element in self.rows:
                self.row_action(*self.rows[element])
        elif event.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED and event.ui_element == self.scope_menu:
            self.scope = None if event.text == ALL_SAVES else event.text
            self.data = custom_names.load(self.scope)
            self.page, self.editing_rank = 0, None
            self.refresh_list()
        elif event.type == pygame_gui.UI_TEXT_ENTRY_CHANGED and event.ui_element == self.search_box:
            self.search = self.search_box.get_text().strip()
            self.page = 0
            self.refresh_list()
        elif event.type == pygame_gui.UI_TEXT_ENTRY_FINISHED and event.ui_element == self.entry:
            self.add_name()
        return super().process_event(event)
