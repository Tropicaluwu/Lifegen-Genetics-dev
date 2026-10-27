from __future__ import annotations

from enum import Enum


class PatrolType(Enum):
    hunting = "hunting"
    herb_gathering = "herb_gathering"
    border = "border"
    training = "training"

    # LG
    lifegen = "lifegen"
    df = "df"
    date = "date"
