"""CLI entry point for the omniscope tool."""

import argparse
import json
import os
import sys

from omniscope._help import ColorFormatter, print_main_help
from omniscope.base import MEASURE_PARAMS
from omniscope.drivers.registry import detect


# ── Argument type parsers ─────────────────────────────────────────────────────

_TIME_UNITS = {"ns": 1e-9, "us": 1e-6, "µs": 1e-6, "ms": 1e-3, "s": 1.0}

def parse_time(value: str) -> float:
    """Parse a time string with optional unit suffix to seconds.
    Examples: '1ms' -> 0.001, '500us' -> 0.0005, '2s' -> 2.0, '0.001' -> 0.001
    """
    value = value.strip()
    for unit, factor in sorted(_TIME_UNITS.items(), key=lambda x: -len(x[0])):
        if value.lower().endswith(unit):
            try:
                return float(value[:-len(unit)]) * factor
            except ValueError:
                break
    try:
        return float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"invalid time value '{value}' — use a number with optional unit: ns, us, ms, s"
        )

def _parse_div_or(value: str, fallback):
    """If value ends with 'div', return a callable(scale)->float.
    Otherwise delegate to fallback parser.
    """
    if value.strip().lower().endswith("div"):
        try:
            n = float(value.strip()[:-3])
            return lambda scale: n * scale
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"invalid division value '{value}' — expected e.g. -2div, 0.5div"
            )
    return fallback(value)

def parse_x_offset(value: str):
    """X-axis offset: time value (e.g. -1ms) or divisions (e.g. -2div)."""
    return _parse_div_or(value, parse_time)

def parse_y_offset(value: str):
    """Y-axis offset: voltage as float (e.g. -1.5) or divisions (e.g. -2div)."""
    def _float(v):
        try:
            return float(v)
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"invalid voltage value '{v}' — expected a number (volts) or e.g. -2div"
            )
    return _parse_div_or(value, _float)


def parse_trigger_source(value: str) -> str:
    """Normalize trigger source to canonical UI values: CH1..CH4, EXT."""
    v = value.strip().upper()
    alias = {
        "CHAN1": "CH1",
        "CHAN2": "CH2",
        "CHAN3": "CH3",
        "CHAN4": "CH4",
        "EXTERNAL": "EXT",
    }
    v = alias.get(v, v)
    if v in {"CH1", "CH2", "CH3", "CH4", "EXT"}:
        return v
    raise argparse.ArgumentTypeError(
        f"invalid trigger source '{value}' — expected CH1, CH2, CH3, CH4, or EXT"
    )


# ── Output helpers ────────────────────────────────────────────────────────────

def _invert_png(black_path: str) -> str:
    """Invert a PNG image (white background) and return the new file path."""
    from PIL import Image, ImageOps
    img = Image.open(black_path).convert("RGB")
    white_path = black_path[:-4] + "_white.png"
    ImageOps.invert(img).save(white_path)
    return white_path


def _print(data: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, indent=2))
    else:
        for k, v in data.items():
            print(f"{k}: {v}")


def _channels_from_args(args: argparse.Namespace, all_channels: list[int]) -> list[int]:
    """Return channels selected by --ch1/--ch2/... flags.
    Falls back to *all_channels* if none are specified."""
    selected = [ch for ch in all_channels if getattr(args, f"ch{ch}", False)]
    return selected if selected else all_channels


# ── Subcommand handlers ───────────────────────────────────────────────────────

def cmd_run(osc, args):
    osc.run()
    print("running")


def cmd_stop(osc, args):
    osc.stop()
    print("stopped")


def cmd_single(osc, args):
    osc.single()
    print("single acquisition armed")


def cmd_get_label(osc, args):
    channels = _channels_from_args(args, [1, 2, 3, 4])
    result = {f"ch{ch}": osc.get_label(ch) for ch in channels}
    _print(result, args.json)


def cmd_set_label(osc, args):
    for ch in [1, 2, 3, 4]:
        label = getattr(args, f"ch{ch}", None)
        if label is not None:
            osc.set_label(ch, label)
            print(f"ch{ch}: label set to '{label}'")


def cmd_get_visible(osc, args):
    channels = _channels_from_args(args, [1, 2, 3, 4])
    result = {f"ch{ch}": osc.get_visible(ch) for ch in channels}
    _print(result, args.json)


def cmd_set_visible(osc, args):
    for ch in [1, 2, 3, 4]:
        val = getattr(args, f"ch{ch}", None)
        if val is not None:
            visible = val.lower() in ("on", "1", "true", "yes")
            osc.set_visible(ch, visible)
            print(f"ch{ch}: {'visible' if visible else 'hidden'}")


def cmd_get_channel(osc, args):
    channels = _channels_from_args(args, [1, 2, 3, 4])
    result = {f"ch{ch}": osc.get_channel(ch) for ch in channels}
    _print(result, args.json)


def cmd_set_channel(osc, args):
    channels = [ch for ch in [1, 2, 3, 4] if getattr(args, f"ch{ch}", False)]
    if not channels:
        print("Error: specify at least one channel (--ch1 / --ch2 / ...)", file=sys.stderr)
        sys.exit(1)
    bwlimit = None
    if args.bwlimit is not None:
        bwlimit = args.bwlimit.lower() in ("on", "1", "true", "yes")
    invert = None
    if args.invert is not None:
        invert = args.invert.lower() in ("on", "1", "true", "yes")
    for ch in channels:
        osc.set_channel(ch, coupling=args.coupling, probe=args.probe,
                        bwlimit=bwlimit, invert=invert)
        print(f"ch{ch}: updated")


def cmd_get_x_axis(osc, args):
    result = osc.get_x_axis()
    _print(result, args.json)


def cmd_set_x_axis(osc, args):
    offset = args.offset
    if callable(offset):
        scale = args.scale if args.scale is not None else osc.get_x_axis()["scale"]
        offset = offset(scale)
    osc.set_x_axis(scale=args.scale, offset=offset)
    print("x-axis updated")


def cmd_get_y_axis(osc, args):
    channels = _channels_from_args(args, [1, 2, 3, 4])
    result = {f"ch{ch}": osc.get_y_axis(ch) for ch in channels}
    _print(result, args.json)


def cmd_set_y_axis(osc, args):
    channels = [ch for ch in [1, 2, 3, 4] if getattr(args, f"ch{ch}", False)]
    if not channels:
        print("Error: specify at least one channel (--ch1 / --ch2 / ...)", file=sys.stderr)
        sys.exit(1)
    if args.scale is None and args.offset is None:
        print("Error: specify --scale and/or --offset", file=sys.stderr)
        sys.exit(1)
    for ch in channels:
        offset = args.offset
        if callable(offset):
            scale = args.scale if args.scale is not None else osc.get_y_axis(ch)["scale"]
            offset = offset(scale)
        osc.set_y_axis(ch, scale=args.scale, offset=offset)
        print(f"ch{ch}: y-axis updated")


def cmd_get_trigger(osc, args):
    result = osc.get_trigger()
    _print(result, args.json)


def cmd_set_trigger(osc, args):
    if all(v is None for v in [args.source, args.level, args.slope, args.mode, args.sweep]):
        print("Error: specify at least one trigger parameter", file=sys.stderr)
        sys.exit(1)
    osc.set_trigger(source=args.source, level=args.level, slope=args.slope,
                    mode=args.mode, sweep=args.sweep)
    print("trigger updated")


def cmd_list_measures(osc, args):
    params = osc.measure_params()
    if args.json:
        print(json.dumps(params))
    else:
        for p in params:
            print(p)


def cmd_measure(osc, args):
    channels = _channels_from_args(args, [1, 2, 3, 4])
    result = {f"ch{ch}": osc.measure(ch, args.param) for ch in channels}
    _print(result, args.json)


def cmd_save_image(osc, args):
    path = osc.save_image(args.output or os.getcwd())
    bg = args.bg
    if bg == "black":
        print(f"saved: {path}")
    elif bg == "white":
        white_path = _invert_png(path)
        os.remove(path)
        print(f"saved: {white_path}")
    else:  # both
        white_path = _invert_png(path)
        print(f"saved: {path}")
        print(f"saved (white): {white_path}")


def cmd_save_csv(osc, args):
    output = args.output or os.getcwd()
    channels = _channels_from_args(args, [1, 2, 3, 4])
    for ch in channels:
        path = osc.save_csv(ch, output)
        print(f"ch{ch} saved: {path}")


def cmd_save(osc, args):
    output = args.output or os.getcwd()
    bg = args.bg
    img = osc.save_image(output)
    if bg == "black":
        print(f"image saved: {img}")
    elif bg == "white":
        white_path = _invert_png(img)
        os.remove(img)
        print(f"image saved: {white_path}")
    else:  # both
        white_path = _invert_png(img)
        print(f"image saved: {img}")
        print(f"image saved (white): {white_path}")
    channels = _channels_from_args(args, [1, 2, 3, 4])
    for ch in channels:
        if osc.get_visible(ch) or getattr(args, f"ch{ch}", False):
            path = osc.save_csv(ch, output)
            print(f"ch{ch} csv saved: {path}")


# ── Parser helpers ────────────────────────────────────────────────────────────

def _add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="Output as JSON")


def _add_channel_flags(parser: argparse.ArgumentParser, with_value: bool = False) -> None:
    for ch in [1, 2, 3, 4]:
        if with_value:
            parser.add_argument(f"--ch{ch}", metavar="VALUE", default=None,
                                help=f"Apply to channel {ch}")
        else:
            parser.add_argument(f"--ch{ch}", action="store_true", default=False,
                                help=f"Include channel {ch} (default: all channels)")


def _add_output_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-o", "--output", default=None, metavar="DIR",
                        help="Directory to save files (default: current directory)")


def _add_image_output_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-o", "--output", default=None, metavar="PATH",
                        help="Directory or .png file path (default: current directory)")


def _sub(subparsers, name: str, help: str, epilog: str) -> argparse.ArgumentParser:
    """Add a subparser with ColorFormatter and a pre-formatted epilog."""
    return subparsers.add_parser(
        name,
        help=help,
        description=help,
        formatter_class=ColorFormatter,
        epilog=epilog,
    )


# ── Custom --help action for the main parser ──────────────────────────────────

class _HelpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        print_main_help()
        parser.exit()


# ── Parser construction ───────────────────────────────────────────────────────

def build_parser() -> tuple[argparse.ArgumentParser, dict[str, argparse.ArgumentParser]]:
    parser = argparse.ArgumentParser(
        prog="omniscope",
        add_help=False,
    )
    parser.add_argument("-h", "--help", nargs=0, action=_HelpAction,
                        help="Show help for omniscope")

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers: dict[str, argparse.ArgumentParser] = {}

    # ── Acquisition ──────────────────────────────────────────────────────────

    _sub(sub, "run", "Start continuous acquisition",
         "examples:\n  omniscope run")

    _sub(sub, "stop", "Stop acquisition and hold waveform",
         "examples:\n  omniscope stop")

    _sub(sub, "single", "Arm for a single acquisition then stop",
         "examples:\n  omniscope single")

    # ── Channel display ──────────────────────────────────────────────────────

    p = _sub(sub, "get-label", "Get channel display labels",
             "examples:\n"
             "  omniscope get-label\n"
             "  omniscope get-label --ch1 --ch2\n"
             "  omniscope get-label --json")
    _add_channel_flags(p)
    _add_json_flag(p)

    p = _sub(sub, "set-label", "Set channel display labels",
             "examples:\n"
             "  omniscope set-label --ch1 VCC --ch2 GND\n"
             "  omniscope set-label --ch1 SDA --ch2 SCL")
    _add_channel_flags(p, with_value=True)

    p = _sub(sub, "get-visible", "Get channel visibility",
             "examples:\n"
             "  omniscope get-visible\n"
             "  omniscope get-visible --ch1 --json")
    _add_channel_flags(p)
    _add_json_flag(p)

    p = _sub(sub, "set-visible", "Set channel visibility (on/off)",
             "note:\n"
             "  VALUE accepts: on, off, 1, 0, true, false, yes, no\n"
             "\n"
             "examples:\n"
             "  omniscope set-visible --ch1 on --ch2 off\n"
             "  omniscope set-visible --ch3 off")
    _add_channel_flags(p, with_value=True)

    # ── Channel settings ─────────────────────────────────────────────────────

    p = _sub(sub, "get-channel",
             "Get channel settings (coupling, probe, bwlimit, invert)",
             "examples:\n"
             "  omniscope get-channel\n"
             "  omniscope get-channel --ch1 --json")
    _add_channel_flags(p)
    _add_json_flag(p)

    p = _sub(sub, "set-channel", "Set channel settings",
             "examples:\n"
             "  omniscope set-channel --ch1 --coupling DC --probe 10\n"
             "  omniscope set-channel --ch1 --ch2 --bwlimit on\n"
             "  omniscope set-channel --ch1 --invert on")
    _add_channel_flags(p)
    p.add_argument("--coupling", choices=["DC", "AC", "GND"], metavar="DC|AC|GND",
                   help="Input coupling")
    p.add_argument("--probe",    type=float, metavar="RATIO",
                   help="Probe attenuation ratio (e.g. 10 for 10×)")
    p.add_argument("--bwlimit",  choices=["on", "off"], metavar="on|off",
                   help="Bandwidth limit (20 MHz)")
    p.add_argument("--invert",   choices=["on", "off"], metavar="on|off",
                   help="Invert channel signal")

    # ── Timebase ─────────────────────────────────────────────────────────────

    p = _sub(sub, "get-x-axis", "Get timebase settings",
             "examples:\n"
             "  omniscope get-x-axis\n"
             "  omniscope get-x-axis --json")
    _add_json_flag(p)

    p = _sub(sub, "set-x-axis", "Set timebase settings",
             "examples:\n"
             "  omniscope set-x-axis --scale 1ms\n"
             "  omniscope set-x-axis --scale 500us --offset -2div\n"
             "  omniscope set-x-axis --offset 1ms\n"
             "  omniscope set-x-axis --scale 0.001")
    p.add_argument("--scale",  type=parse_time,     metavar="TIME",
                   help="Time per division (e.g. 1ms, 500us, 2s)")
    p.add_argument("--offset", type=parse_x_offset, metavar="TIME|DIV",
                   help="Horizontal offset as time (e.g. -1ms) or divisions (e.g. -2div)")

    # ── Vertical ─────────────────────────────────────────────────────────────

    p = _sub(sub, "get-y-axis", "Get vertical axis settings",
             "examples:\n"
             "  omniscope get-y-axis\n"
             "  omniscope get-y-axis --ch1 --ch2 --json")
    _add_channel_flags(p)
    _add_json_flag(p)

    p = _sub(sub, "set-y-axis", "Set vertical axis settings",
             "examples:\n"
             "  omniscope set-y-axis --ch1 --scale 0.5\n"
             "  omniscope set-y-axis --ch1 --ch2 --scale 1.0 --offset 0\n"
             "  omniscope set-y-axis --ch1 --offset -2div\n"
             "  omniscope set-y-axis --ch1 --scale 0.5 --offset 1div")
    _add_channel_flags(p)
    p.add_argument("--scale",  type=float,        metavar="V/DIV", help="Volts per division")
    p.add_argument("--offset", type=parse_y_offset, metavar="V|DIV",
                   help="Vertical offset as voltage (e.g. -1.5) or divisions (e.g. -2div)")

    # ── Trigger ──────────────────────────────────────────────────────────────

    p = _sub(sub, "get-trigger", "Get trigger settings",
             "examples:\n"
             "  omniscope get-trigger\n"
             "  omniscope get-trigger --json")
    _add_json_flag(p)

    p = _sub(sub, "set-trigger", "Set trigger settings",
             "examples:\n"
             "  omniscope set-trigger --source CH1 --level 1.0 --slope rising\n"
             "  omniscope set-trigger --sweep normal\n"
             "  omniscope set-trigger --mode edge --sweep auto")
    p.add_argument("--source", type=parse_trigger_source, metavar="CH1|CH2|CH3|CH4|EXT",
                   help="Trigger source")
    p.add_argument("--level",  type=float, metavar="V", help="Trigger level (volts)")
    p.add_argument("--slope",  choices=["rising", "falling", "either"],
                   metavar="rising|falling|either", help="Edge slope")
    p.add_argument("--mode",   metavar="edge|pulse|...", help="Trigger mode")
    p.add_argument("--sweep",  choices=["auto", "normal", "single"],
                   metavar="auto|normal|single", help="Sweep mode")

    # ── Measurement ──────────────────────────────────────────────────────────

    p = _sub(sub, "list-measures", "List measurement parameters supported by the connected scope",
             "examples:\n"
             "  omniscope list-measures\n"
             "  omniscope list-measures --json")
    _add_json_flag(p)

    p = _sub(sub, "measure", "Read an automatic measurement",
             "examples:\n"
             "  omniscope measure --ch1 --param vpp\n"
             "  omniscope measure --ch1 --ch2 --param freq\n"
             "  omniscope measure --ch1 --param vrms --json")
    _add_channel_flags(p)
    p.add_argument("--param", required=True, choices=MEASURE_PARAMS, metavar="PARAM",
                   help="  ".join(MEASURE_PARAMS))
    _add_json_flag(p)

    # ── Data ─────────────────────────────────────────────────────────────────

    p = _sub(sub, "save-image", "Capture and save a screenshot",
             "examples:\n"
              "  omniscope save-image\n"
              "  omniscope save-image --bg white\n"
             "  omniscope save-image --bg both -o ./captures\n"
             "  omniscope save-image -o ./captures/shot.png")
    _add_image_output_flag(p)
    p.add_argument("--bg", choices=["black", "white", "both"], default="black",
                   metavar="black|white|both",
                   help="Background color: black (default), white, both")

    p = _sub(sub, "save-csv", "Download and save waveform data as CSV",
             "examples:\n"
             "  omniscope save-csv\n"
             "  omniscope save-csv --ch1 --ch2 -o ./data")
    _add_channel_flags(p)
    _add_output_flag(p)

    p = _sub(sub, "save", "Save screenshot and CSV for visible channels",
             "examples:\n"
             "  omniscope save\n"
             "  omniscope save --bg white -o ./out\n"
             "  omniscope save --bg both --ch1 --ch2 -o ./out")
    _add_channel_flags(p)
    _add_output_flag(p)
    p.add_argument("--bg", choices=["black", "white", "both"], default="black",
                   metavar="black|white|both",
                   help="Background color: black (default), white, both")

    return parser, sub._name_parser_map


def get_parser() -> argparse.ArgumentParser:
    """Return just the top-level parser (used by shtab to generate completions)."""
    parser, _ = build_parser()
    return parser


# ── Pre-connect validators ────────────────────────────────────────────────────
# Return an error string if args are insufficient; None if OK.
# These run before the oscilloscope connection is attempted.

def _any_channel_value(args):
    return any(getattr(args, f"ch{ch}", None) is not None for ch in [1, 2, 3, 4])

def _any_channel_flag(args):
    return any(getattr(args, f"ch{ch}", False) for ch in [1, 2, 3, 4])

PRE_VALIDATORS = {
    "set-label":   lambda a: None if _any_channel_value(a)
                             else "specify at least one channel value (--ch1 LABEL ...)",
    "set-visible": lambda a: None if _any_channel_value(a)
                             else "specify at least one channel value (--ch1 on/off ...)",
    "set-channel": lambda a: None if (_any_channel_flag(a) and
                                      any(v is not None for v in [a.coupling, a.probe, a.bwlimit, a.invert]))
                             else "specify at least one channel (--ch1 ...) and one setting",
    "set-x-axis":  lambda a: None if (a.scale is not None or a.offset is not None)
                             else "specify --scale and/or --offset",
    "set-y-axis":  lambda a: None if (_any_channel_flag(a) and
                                      (a.scale is not None or a.offset is not None))
                             else "specify at least one channel (--ch1 ...) and --scale and/or --offset",
    "set-trigger": lambda a: None if any(v is not None for v in [a.source, a.level, a.slope, a.mode, a.sweep])
                             else "specify at least one trigger parameter",
}


# ── Entry point ───────────────────────────────────────────────────────────────

HANDLERS = {
    "run":         cmd_run,
    "stop":        cmd_stop,
    "single":      cmd_single,
    "get-label":   cmd_get_label,
    "set-label":   cmd_set_label,
    "get-visible": cmd_get_visible,
    "set-visible": cmd_set_visible,
    "get-channel": cmd_get_channel,
    "set-channel": cmd_set_channel,
    "get-x-axis":  cmd_get_x_axis,
    "set-x-axis":  cmd_set_x_axis,
    "get-y-axis":  cmd_get_y_axis,
    "set-y-axis":  cmd_set_y_axis,
    "get-trigger": cmd_get_trigger,
    "set-trigger": cmd_set_trigger,
    "list-measures": cmd_list_measures,
    "measure":     cmd_measure,
    "save-image":  cmd_save_image,
    "save-csv":    cmd_save_csv,
    "save":        cmd_save,
}


def main() -> None:
    parser, subparsers = build_parser()
    args = parser.parse_args()

    if args.command is None:
        print_main_help()
        sys.exit(0)

    validator = PRE_VALIDATORS.get(args.command)
    if validator:
        error = validator(args)
        if error:
            print(f"Error: {error}\n", file=sys.stderr)
            subparsers[args.command].print_help()
            sys.exit(1)

    try:
        osc = detect()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        HANDLERS[args.command](osc, args)
    finally:
        osc.close()


if __name__ == "__main__":
    main()
