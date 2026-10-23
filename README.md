# LifeGen Genetics

**LifeGen** and **Genemod** (the genetics mod) put together into one game. You play as your own cat like in LifeGen, and every cat has real genes like in Genemod, so kits actually look like their parents.

## Credits

**None of this would exist without these teams. All of the real work is theirs:**

### LifeGen
Made by the **LifeGen team**. LifeGen is the mod where you play as your own cat.
- GitHub: [sedgestripe/clangen](https://github.com/sedgestripe/clangen)
- Website: [mods.clangen.io/LifeGen](https://mods.clangen.io/LifeGen/download)
- Discord: [discord.gg/lifegen](https://discord.gg/lifegen)
- Full list of everyone who worked on it: [LifeGen credits](https://docs.google.com/document/d/1XCm5Eo-y5VA6W9quDMbF3VNyKL7S8_9Tl4c2buuiA8g/edit?usp=sharing)

### Genemod (Genetics mod)
Made by **Chinch-Bug** and contributors. Genemod gives every cat real, inheritable genes.
- GitHub: [Chinch-Bug/clangen-genemod](https://github.com/Chinch-Bug/clangen-genemod)

### ClanGen
The game both mods are built on. Original creator **just-some-cat**, fan edit by **SableSteel** and the ClanGen team.
- GitHub: [ClanGenOfficial/clangen](https://github.com/ClanGenOfficial/clangen)
- Itch.io: [sablesteel.itch.io/clan-gen-fan-edit](https://sablesteel.itch.io/clan-gen-fan-edit)

This is an unofficial combination made for fun. **Please don't take bug reports from it to the LifeGen, Genemod or ClanGen teams**, they didn't make this version and can't help with it.

## What's in it

- Everything from LifeGen: playing as your own cat, talking, patrols, the Dark Forest, shunning, affairs and the rest
- Genemod's genetics: coat colour, patterns, white spotting, eyes, fur types, ear and tail traits, genetic conditions and offspring prediction
- Genemod's multi clan mode (optional, picked when you make a new clan)
- Up to date with ClanGen v0.13.4
- Fixes for crashes that came from putting the two mods together

See [changelog.txt](changelog.txt) for the full list.

## Using a LifeGen save

LifeGen saves work. Copy your clan's folder and its `<Name>clan.json` file (for example a `Leap` folder and `Leapclan.json`) from

`%LOCALAPPDATA%\LifeGen\LifeGen\saves`

into

`%LOCALAPPDATA%\LifeGenGenetics\LifeGenGenetics\saves`

(run the game once first so the folder exists). The first time the save loads, every cat gets genes made from its old pelt. Keep a backup of the original, because once it's saved here it won't load in regular LifeGen anymore.

## Running from source

You need [uv](https://docs.astral.sh/uv/), it installs the right Python by itself.

```
uv sync
uv run main.py
```

When you run from source, saves go in the `saves` folder next to `main.py`.

## Building the exe

```
uv sync --group build
uv run pyinstaller Clangen.spec
```

The game ends up in `dist/LifeGenGenetics`.

## License

Code is under the Mozilla Public License 2.0 and the sprites/art are under CC BY-NC 4.0, same as ClanGen, LifeGen and Genemod. See [LICENSE.md](LICENSE.md).
