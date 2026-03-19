#!/bin/sh
# install.sh — Set up the omniscope tool on Linux / macOS
set -e

REQUIRED_MAJOR=3
REQUIRED_MINOR=10

# ── Find Python ───────────────────────────────────────────────────────────────

find_python() {
	for cmd in python3 python; do
		if command -v "$cmd" >/dev/null 2>&1; then
			version=$("$cmd" -c "import sys; print(sys.version_info.major, sys.version_info.minor)")
			major=$(echo "$version" | cut -d' ' -f1)
			minor=$(echo "$version" | cut -d' ' -f2)
			if [ "$major" -ge "$REQUIRED_MAJOR" ] && [ "$minor" -ge "$REQUIRED_MINOR" ]; then
				echo "$cmd"
				return 0
			fi
		fi
	done
	return 1
}

PYTHON=$(find_python) || {
	echo ""
	echo "ERROR: Python $REQUIRED_MAJOR.$REQUIRED_MINOR or newer is required but was not found."
	echo ""
	echo "Install Python:"
	echo "  macOS  : brew install python   (https://brew.sh)"
	echo "  Ubuntu : sudo apt install python3"
	echo "  Fedora : sudo dnf install python3"
	echo ""
	exit 1
}

echo "Using Python: $PYTHON ($(${PYTHON} --version))"

# ── Create virtual environment ────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$SCRIPT_DIR/venv"

if [ ! -d "$VENV" ]; then
	echo "Creating virtual environment..."
	"$PYTHON" -m venv "$VENV"
elif ! "$VENV/bin/pip" --version >/dev/null 2>&1; then
	echo "Virtual environment is broken (stale paths), recreating..."
	rm -rf "$VENV"
	"$PYTHON" -m venv "$VENV"
else
	echo "Virtual environment already exists, skipping creation."
fi

# ── Install package ───────────────────────────────────────────────────────────

echo "Installing omniscope..."
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -e "$SCRIPT_DIR"

# ── Install launchers to ~/.local/bin ────────────────────────────────────────

LOCAL_BIN="$HOME/.local/bin"
mkdir -p "$LOCAL_BIN"
ln -sf "$VENV/bin/omniscope" "$LOCAL_BIN/omniscope"

# ── Install tab completion ────────────────────────────────────────────────────

# bash
BASH_COMP_DIR="$HOME/.local/share/bash-completion/completions"
mkdir -p "$BASH_COMP_DIR"
"$VENV/bin/python" -m shtab -s bash omniscope.cli.get_parser > "$BASH_COMP_DIR/omniscope"
echo "Bash tab completion installed (restart shell or run: exec bash)"

# zsh — try known locations that are in the default fpath without .zshrc changes
ZSH_COMP_FILE=""
for dir in \
    "$HOME/.oh-my-zsh/completions" \
    "/usr/local/share/zsh/site-functions" \
    "/usr/share/zsh/vendor-completions"
do
    if [ -d "$dir" ] && [ -w "$dir" ]; then
        ZSH_COMP_FILE="$dir/_omniscope"
        break
    fi
done

if [ -n "$ZSH_COMP_FILE" ]; then
    "$VENV/bin/python" -m shtab -s zsh omniscope.cli.get_parser > "$ZSH_COMP_FILE"
    echo "Zsh tab completion installed to $ZSH_COMP_FILE"
else
    echo "NOTE: For zsh completion with subcommand descriptions, add to ~/.zshrc:"
    echo "  fpath=(~/.local/share/zsh/site-functions \$fpath) && autoload -Uz compinit && compinit"
    mkdir -p "$HOME/.local/share/zsh/site-functions"
    "$VENV/bin/python" -m shtab -s zsh omniscope.cli.get_parser \
        > "$HOME/.local/share/zsh/site-functions/_omniscope"
fi

echo ""
echo "Installation complete."
echo ""
echo "Usage:"
echo "  omniscope <subcommand> [options]"
echo "  omniscope --help"
echo ""
if ! echo "$PATH" | grep -q "$LOCAL_BIN"; then
	echo "NOTE: Add ~/.local/bin to your PATH if not already present:"
	echo "  export PATH=\"\$PATH:$LOCAL_BIN\""
	echo "(Add that line to ~/.bashrc or ~/.zshrc to make it permanent.)"
	echo ""
fi
