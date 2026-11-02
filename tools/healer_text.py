"""Players only ever read "healer", never "medicine cat". Rerun after every upstream merge.

Only displayed words change. Rank filters, tags, ids, file names and JSON keys stay, the
game logic reads those. The credits stay too, they name people's work.

Run from the game folder: python tools/healer_text.py [--check]
--check only lists what would change.
"""
import json
import os
import re
import sys

TEXT_ROOTS = ("resources/lang/en",)

# values under these keys are read by the game, not by players
DATA_KEYS = {
    "rank",
    "status",
    "your_status",
    "victim_status",
    "new_status",
    "tags",
    "event_id",
    "patrol_art",
    "patrol_art_clean",
    "patrol_id",
    "id",
}
# a whole value like this is a rank filter wherever it is
RANK_VALUE = re.compile(
    r"^-?(clan:|any:)?(medicine cat|medicine cat apprentice|medicine_cat|medicine_cat_apprentice)$"
)
# text the code writes itself, (file, part of the line)
CODE_LINES = (
    ("scripts/cat/cats.py", "has forfeit the role of a medicine cat"),
    ("scripts/screens/MurderScreen.py", "assigned counseling by the Clan's medicine cat"),
    ("scripts/ui/windows/pick_path.py", 'tool_tip_text="Choose to become a medicine cat apprentice"'),
)

WORDS = re.compile(
    r"(?P<keep>%?\{[^{}]*\})"  # placeholders like %{medcats} are read by the code
    r"|\b(?P<typo>[Aa] medicine cats)\b"
    r"|\b(?P<den>medicine(?:[ -]cat)? den)\b"
    r"|\b(?P<role>medicine[ -]cat|med[ -]?cat)(?P<plural>s?)\b"
    r"|\b(?P<app>medicine) (?=apprentice)",
    re.IGNORECASE,
)
STRING = re.compile(r'"(?:[^"\\]|\\.)*"|[{}\[\]:]')


def match_case(found, new):
    if found.isupper():
        return new.upper()
    if found[0].isupper():
        return new.capitalize()
    return new


def healer_words(text):
    def swap(m):
        if m["keep"]:
            return m["keep"]
        if m["typo"]:
            return m["typo"][0] + " healer"
        if m["den"]:
            return match_case(m["den"], "healer den")
        if m["role"]:
            return match_case(m["role"], "healer") + m["plural"]
        return match_case(m["app"], "healer") + " "

    return WORDS.sub(swap, text)


def convert_json(source):
    """Goes through the file's tokens so everything but the changed words stays byte for byte."""
    out = []
    last = 0
    stack = []
    pending_key = None
    tokens = list(STRING.finditer(source))
    changed = 0
    for i, token in enumerate(tokens):
        raw = token.group()
        if raw == "{" or raw == "[":
            stack.append((raw, pending_key))
            pending_key = None
        elif raw == "}" or raw == "]":
            stack.pop()
            pending_key = None
        elif raw == ":":
            continue
        else:
            is_key = i + 1 < len(tokens) and tokens[i + 1].group() == ":" and stack[-1][0] == "{"
            if is_key:
                pending_key = json.loads(raw)
                continue
            key = pending_key
            if key is None:
                key = next((k for _, k in reversed(stack) if k is not None), None)
            pending_key = None
            value = json.loads(raw)
            if key in DATA_KEYS or RANK_VALUE.match(value):
                continue
            new = healer_words(raw)
            if new != raw:
                out.append(source[last : token.start()])
                out.append(new)
                last = token.end()
                changed += 1
    out.append(source[last:])
    return "".join(out), changed


def main():
    check = "--check" in sys.argv
    paths = []
    for root in TEXT_ROOTS:
        for folder, _, files in os.walk(root):
            paths += [os.path.join(folder, f) for f in files if f.endswith(".json")]

    total = files_changed = 0
    for path in sorted(paths):
        with open(path, "r", encoding="utf-8", newline="") as read_file:
            source = read_file.read()
        new, changed = convert_json(source)
        if not changed:
            continue
        json.loads(new)  # it has to stay valid
        total += changed
        files_changed += 1
        if not check:
            with open(path, "w", encoding="utf-8", newline="") as write_file:
                write_file.write(new)

    code_changed = 0
    for path, anchor in CODE_LINES:
        with open(path, "r", encoding="utf-8", newline="") as read_file:
            lines = read_file.read().split("\n")
        hits = [i for i, line in enumerate(lines) if anchor in line]
        for i in hits:
            lines[i] = healer_words(lines[i])
        code_changed += len(hits)
        if hits and not check:
            with open(path, "w", encoding="utf-8", newline="") as write_file:
                write_file.write("\n".join(lines))

    print(f"{total} strings in {files_changed} files, {code_changed} code lines")


if __name__ == "__main__":
    main()
