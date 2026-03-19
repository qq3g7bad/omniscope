#!/bin/sh
# uninstall.sh — Remove omniscope and its shell integration
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

LAUNCHER="$HOME/.local/bin/omniscope"
VENV="$SCRIPT_DIR/venv"

remove() {
    if [ -e "$1" ] || [ -L "$1" ]; then
        rm -rf "$1"
        echo "Removed: $1"
    fi
}

remove "$LAUNCHER"
remove "$VENV"

# Remove bash completion
remove "$HOME/.local/share/bash-completion/completions/omniscope"

# Remove zsh completion from all locations where install.sh may have written it
for f in \
    "$HOME/.oh-my-zsh/completions/_omniscope" \
    "/usr/local/share/zsh/site-functions/_omniscope" \
    "/usr/share/zsh/vendor-completions/_omniscope" \
    "$HOME/.local/share/zsh/site-functions/_omniscope"
do
    remove "$f"
done

echo ""
echo "omniscope uninstalled."
echo ""
