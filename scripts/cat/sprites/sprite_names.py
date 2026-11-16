"""LG: the sprite names in a sprite data file's "sprite_list", for both layouts."""


def sprite_names(sprite_list):
    """Every name in the list. Split sheets (like patches_tortie0 and 1) keep one list of rows per sheet."""
    sheets = sprite_list.values() if isinstance(sprite_list, dict) else [sprite_list]
    return [name for rows in sheets for row in rows for name in row if name]
