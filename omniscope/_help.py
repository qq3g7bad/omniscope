"""Colored, glab-style help formatting for the omniscope CLI."""

import argparse
import os
import re
import sys

# ── Color support ──────────────────────────────────────────────────────────────

_USE_COLOR = (
    hasattr(sys.stdout, "isatty")
    and sys.stdout.isatty()
    and "NO_COLOR" not in os.environ
    and os.environ.get("TERM", "") != "dumb"
)

def _e(code: str) -> str:
    return code if _USE_COLOR else ""

RST = _e("\033[0m")    # reset
BLD = _e("\033[1m")    # bold
DIM = _e("\033[2m")    # dim
CYN = _e("\033[36m")   # cyan  — section headers
GRN = _e("\033[32m")   # green — $ prompt in examples


# ── Command groups (main help page) ───────────────────────────────────────────

_GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    ("ACQUISITION COMMANDS", [
        ("run",    "Start continuous acquisition"),
        ("stop",   "Stop acquisition and hold waveform"),
        ("single", "Arm for a single acquisition then stop"),
    ]),
    ("CHANNEL COMMANDS", [
        ("get-label",   "Get channel display labels"),
        ("set-label",   "Set channel display labels"),
        ("get-visible", "Get channel visibility"),
        ("set-visible", "Set channel visibility (on/off)"),
        ("get-channel", "Get channel settings (coupling, probe, bwlimit, invert)"),
        ("set-channel", "Set channel settings"),
        ("get-y-axis",  "Get vertical axis settings"),
        ("set-y-axis",  "Set vertical axis settings"),
    ]),
    ("TIMEBASE COMMANDS", [
        ("get-x-axis", "Get timebase settings"),
        ("set-x-axis", "Set timebase settings"),
    ]),
    ("TRIGGER COMMANDS", [
        ("get-trigger", "Get trigger settings"),
        ("set-trigger", "Set trigger settings"),
    ]),
    ("MEASUREMENT COMMANDS", [
        ("list-measures", "List measurement parameters supported by the connected scope"),
        ("measure",       "Read an automatic measurement"),
    ]),
    ("DATA COMMANDS", [
        ("save-image", "Capture and save a screenshot"),
        ("save-csv",   "Download and save waveform data as CSV"),
        ("save",       "Save screenshot and CSV for visible channels"),
    ]),
]


def print_main_help() -> None:
    """Print the colored, glab-style top-level help page."""
    all_names = [name for _, cmds in _GROUPS for name, _ in cmds]
    col = max(len(n) for n in all_names) + 4

    lines: list[str] = []
    lines.append(f"  {DIM}CLI tool for oscilloscope control via VISA/SCPI.{RST}")
    lines.append("")
    lines.append(f"  {BLD}{CYN}USAGE{RST}")
    lines.append("")
    lines.append(f"    omniscope <subcommand> [flags]")

    for group, cmds in _GROUPS:
        lines.append("")
        lines.append(f"  {BLD}{CYN}{group}{RST}")
        lines.append("")
        for name, desc in cmds:
            pad = " " * (col - len(name))
            lines.append(f"    {BLD}{name}{RST}{pad}{desc}")

    lines.append("")
    lines.append(f"  {BLD}{CYN}FLAGS{RST}")
    lines.append("")
    lines.append(f"    {BLD}-h, --help{RST}   Show help for omniscope")
    lines.append("")
    lines.append(f"  {DIM}Use 'omniscope <command> --help' for more information about a command.{RST}")
    lines.append("")

    print("\n".join(lines))


# ── Subcommand help formatter ──────────────────────────────────────────────────

class ColorFormatter(argparse.RawDescriptionHelpFormatter):
    """Applies glab-style color and layout to argparse subcommand help."""

    def format_help(self) -> str:
        return _colorize(super().format_help())


def _colorize(text: str) -> str:
    """Post-process argparse help text to add ANSI color and glab layout."""
    lines = text.splitlines()
    out: list[str] = [""]  # leading blank line

    for line in lines:

        # ── "usage: osc foo [...]" → bold USAGE section ────────────────────
        m = re.match(r"^usage:\s*(.*)", line, re.IGNORECASE)
        if m:
            out.append(f"  {BLD}{CYN}USAGE{RST}")
            out.append("")
            out.append(f"    {m.group(1)}")
            continue

        # ── Argparse section headers: "options:", "positional arguments:" ──
        if re.match(r"^[a-z][\w ]+:$", line):
            heading = line.rstrip(":").upper()
            out.append("")
            out.append(f"  {BLD}{CYN}{heading}{RST}")
            out.append("")
            continue

        # ── Flag lines: "  --foo BAR   desc" or "  -f, --foo BAR  desc" ───
        m = re.match(r"^(  )((-[\w-]+(?:,\s*)?)+)(.*)", line)
        if m:
            _, flags_raw, _, rest = m.groups()
            colored = re.sub(r"(-[\w-]+)", f"{BLD}\\1{RST}", flags_raw.rstrip())
            out.append(f"    {colored}{rest}")
            continue

        # ── Continuation lines for long flag descriptions ──────────────────
        if re.match(r"^ {10,}\S", line):
            out.append(f"        {line.lstrip()}")
            continue

        # ── Epilog "examples:" header ──────────────────────────────────────
        if re.match(r"^examples:$", line, re.IGNORECASE):
            out.append(f"  {BLD}{CYN}EXAMPLES{RST}")
            out.append("")
            continue

        # ── Epilog "note:" header ──────────────────────────────────────────
        if re.match(r"^note:$", line, re.IGNORECASE):
            out.append(f"  {BLD}{CYN}NOTE{RST}")
            out.append("")
            continue

        # ── Example lines: "  omniscope <command>" → "    $ omniscope <command>" ──
        m = re.match(r"^  (omniscope\b.*)", line)
        if m:
            out.append(f"    {GRN}${RST} {m.group(1)}")
            continue

        # ── Blank lines ────────────────────────────────────────────────────
        if not line.strip():
            out.append("")
            continue

        # ── Description text, note body, everything else ───────────────────
        out.append(f"  {line}")

    out.append("")  # trailing blank line
    return "\n".join(out)
