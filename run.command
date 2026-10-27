#!/usr/bin/env bash
# Mac: double-click this file to play (the first time, see "How to play" in README.md).

# cd into this file's folder
cd "$(dirname "$0")"

# where the uv installer puts uv, in case Terminal hasn't picked it up yet
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

if ! command -v uv > /dev/null; then
    echo "uv isn't installed yet. See \"How to play\" in README.md (Mac, step 1), then try again."
    read -n 1 -s -r -p "Press any key to close."
    exit 1
fi

uv sync && uv run main.py || read -n 1 -s -r -p "Something went wrong (see above). Press any key to close."
