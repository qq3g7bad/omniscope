"""Rigol oscilloscope driver (DHO800/900 series and compatible)."""

import os
from datetime import datetime

import pyvisa

from omniscope.base import OscilloscopeBase


# Maps measure() param names to Rigol :MEAS:ITEM keywords
_MEASURE_PARAMS = {
    "freq":   "FREQ",
    "period": "PER",
    "vpp":    "VPP",
    "vrms":   "VRMS",
    "vmax":   "VMAX",
    "vmin":   "VMIN",
    "vavg":   "VAVG",
    "rise":   "RISE",
    "fall":   "FALL",
    "duty":   "DUTY",
}

_SLOPE_TO_SCPI = {"rising": "POS", "falling": "NEG", "either": "RFAL"}
_SCPI_TO_SLOPE = {v: k for k, v in _SLOPE_TO_SCPI.items()}


class RigolOscilloscope(OscilloscopeBase):
    """Driver for Rigol DHO800/900 series oscilloscopes.

    Reference: DHO800/900 Programming Guide
    https://download.rigol.com/en/Manual/Digital%20Oscilloscope/DHO800/DHO800900_ProgrammingGuide_EN.pdf
    """

    def __init__(self, inst: pyvisa.resources.MessageBasedResource, idn: str) -> None:
        self._inst = inst
        self._idn = idn

    # ── Identity ──────────────────────────────────────────────────────────────

    def get_idn(self) -> str:
        return self._idn

    # ── Acquisition control ───────────────────────────────────────────────────

    def run(self) -> None:
        self._inst.write(":RUN")

    def stop(self) -> None:
        self._inst.write(":STOP")

    def single(self) -> None:
        self._inst.write(":SINGle")

    # ── Labels ────────────────────────────────────────────────────────────────

    def get_label(self, channel: int) -> str:
        return self._inst.query(f":CHAN{channel}:LAB:CONT?").strip().strip('"')

    def set_label(self, channel: int, label: str) -> None:
        truncated = label[:16]
        if len(label) > 16:
            import warnings
            warnings.warn(f"Label '{label}' truncated to 16 characters: '{truncated}'")
        self._inst.write(f":CHAN{channel}:LAB:CONT {truncated}")
        self._inst.write(f":CHAN{channel}:LAB:SHOW ON")

    # ── Visibility ────────────────────────────────────────────────────────────

    def get_visible(self, channel: int) -> bool:
        resp = self._inst.query(f":CHAN{channel}:DISP?").strip()
        return resp.upper() in ("1", "ON")

    def set_visible(self, channel: int, visible: bool) -> None:
        self._inst.write(f":CHAN{channel}:DISP {'ON' if visible else 'OFF'}")

    # ── Channel settings ──────────────────────────────────────────────────────

    def get_channel(self, channel: int) -> dict:
        coupling = self._inst.query(f":CHAN{channel}:COUP?").strip()
        probe    = float(self._inst.query(f":CHAN{channel}:PROB?").strip())
        bwlimit  = self._inst.query(f":CHAN{channel}:BWL?").strip().upper() in ("1", "ON", "20M", "100M")
        invert   = self._inst.query(f":CHAN{channel}:INV?").strip().upper() in ("1", "ON")
        return {"coupling": coupling, "probe": probe, "bwlimit": bwlimit, "invert": invert}

    def set_channel(
        self,
        channel: int,
        coupling: str | None = None,
        probe: float | None = None,
        bwlimit: bool | None = None,
        invert: bool | None = None,
    ) -> None:
        if coupling is not None:
            self._inst.write(f":CHAN{channel}:COUP {coupling.upper()}")
        if probe is not None:
            self._inst.write(f":CHAN{channel}:PROB {probe}")
        if bwlimit is not None:
            self._inst.write(f":CHAN{channel}:BWL {'20M' if bwlimit else 'OFF'}")
        if invert is not None:
            self._inst.write(f":CHAN{channel}:INV {'ON' if invert else 'OFF'}")

    # ── X-axis (timebase) ─────────────────────────────────────────────────────

    def get_x_axis(self) -> dict:
        scale  = float(self._inst.query(":TIM:SCAL?").strip())
        offset = float(self._inst.query(":TIM:OFFS?").strip())
        return {"scale": scale, "offset": offset}

    def set_x_axis(self, scale: float | None = None, offset: float | None = None) -> None:
        if scale is not None:
            self._inst.write(f":TIM:SCAL {scale}")
        if offset is not None:
            self._inst.write(f":TIM:OFFS {offset}")

    # ── Y-axis (vertical) ─────────────────────────────────────────────────────

    def get_y_axis(self, channel: int) -> dict:
        scale  = float(self._inst.query(f":CHAN{channel}:SCAL?").strip())
        offset = float(self._inst.query(f":CHAN{channel}:OFFS?").strip())
        return {"scale": scale, "offset": offset}

    def set_y_axis(
        self,
        channel: int,
        scale: float | None = None,
        offset: float | None = None,
    ) -> None:
        if scale is not None:
            self._inst.write(f":CHAN{channel}:SCAL {scale}")
        if offset is not None:
            self._inst.write(f":CHAN{channel}:OFFS {offset}")

    # ── Trigger ───────────────────────────────────────────────────────────────

    def get_trigger(self) -> dict:
        mode   = self._inst.query(":TRIG:MODE?").strip().lower()
        sweep  = self._inst.query(":TRIG:SWE?").strip().lower()
        source = self._inst.query(":TRIG:EDGE:SOUR?").strip()
        level  = float(self._inst.query(":TRIG:EDGE:LEV?").strip())
        slope_raw = self._inst.query(":TRIG:EDGE:SLOP?").strip().upper()
        slope  = _SCPI_TO_SLOPE.get(slope_raw, slope_raw.lower())
        return {"source": source, "level": level, "slope": slope, "mode": mode, "sweep": sweep}

    def set_trigger(
        self,
        source: str | None = None,
        level: float | None = None,
        slope: str | None = None,
        mode: str | None = None,
        sweep: str | None = None,
    ) -> None:
        if mode is not None:
            self._inst.write(f":TRIG:MODE {mode.upper()}")
        if sweep is not None:
            self._inst.write(f":TRIG:SWE {sweep.upper()}")
        if source is not None:
            self._inst.write(f":TRIG:EDGE:SOUR {source.upper()}")
        if level is not None:
            self._inst.write(f":TRIG:EDGE:LEV {level}")
        if slope is not None:
            scpi_slope = _SLOPE_TO_SCPI.get(slope.lower(), slope.upper())
            self._inst.write(f":TRIG:EDGE:SLOP {scpi_slope}")

    # ── Measurements ─────────────────────────────────────────────────────────

    def measure_params(self) -> list[str]:
        return list(_MEASURE_PARAMS.keys())

    def measure(self, channel: int, param: str) -> float:
        key = param.lower()
        if key not in _MEASURE_PARAMS:
            raise ValueError(f"Unknown measurement '{param}'. "
                             f"Valid: {', '.join(_MEASURE_PARAMS)}")
        scpi_param = _MEASURE_PARAMS[key]
        self._inst.write(f":MEAS:ITEM {scpi_param},CHAN{channel}")
        result = self._inst.query(f":MEAS:ITEM? {scpi_param},CHAN{channel}").strip()
        return float(result)

    # ── Waveform data ─────────────────────────────────────────────────────────

    def get_waveform(self, channel: int) -> tuple[list[float], list[float]]:
        self._inst.write(":STOP")
        self._inst.write(f":WAV:SOUR CHAN{channel}")
        self._inst.write(":WAV:MODE NORM")
        self._inst.write(":WAV:FORM ASC")

        preamble = self._inst.query(":WAV:PRE?").strip().split(",")
        # Preamble fields: format, type, points, count, x_increment, x_origin,
        #                  x_reference, y_increment, y_origin, y_reference
        if len(preamble) < 6:
            raise RuntimeError(f"Unexpected waveform preamble: {preamble}")
        x_inc = float(preamble[4])
        x_org = float(preamble[5])

        raw = self._inst.query(":WAV:DATA?").strip()
        self._inst.write(":RUN")

        # Response may start with IEEE 488.2 header; strip it if present
        if raw.startswith("#"):
            header_digits = int(raw[1])
            raw = raw[2 + header_digits:]

        samples = [float(v.strip()) for v in raw.split(",") if v.strip()]
        time_s = [x_org + i * x_inc for i in range(len(samples))]
        return time_s, samples

    # ── Screenshot ────────────────────────────────────────────────────────────

    def save_image(self, output_dir: str) -> str:
        self._inst.write(":DISP:DATA?")
        raw = self._inst.read_raw()

        header_digits = raw[1] - ord('0')
        data_offset = 2 + header_digits
        image_size = int(raw[2:data_offset])

        while len(raw) - data_offset < image_size:
            raw += self._inst.read_raw()

        image_data = raw[data_offset:data_offset + image_size]

        filename = _timestamped_path(output_dir, ".png")
        with open(filename, "wb") as f:
            f.write(image_data)
        return filename

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def close(self) -> None:
        self._inst.close()


def _timestamped_path(directory: str, suffix: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(directory, stamp + suffix)
