import csv
import os
from abc import ABC, abstractmethod
from datetime import datetime

MEASURE_PARAMS: tuple[str, ...] = (
    "freq", "period", "vpp", "vrms", "vmax", "vmin", "vavg", "rise", "fall", "duty",
)


class OscilloscopeBase(ABC):
    """Abstract base class defining the common oscilloscope interface."""

    # ── Identity ──────────────────────────────────────────────────────────────

    @abstractmethod
    def get_idn(self) -> str:
        """Return instrument identification string."""

    # ── Acquisition control ───────────────────────────────────────────────────

    @abstractmethod
    def run(self) -> None:
        """Start continuous acquisition."""

    @abstractmethod
    def stop(self) -> None:
        """Stop acquisition and hold the current waveform."""

    @abstractmethod
    def single(self) -> None:
        """Arm for a single acquisition then stop."""

    # ── Labels ────────────────────────────────────────────────────────────────

    @abstractmethod
    def get_label(self, channel: int) -> str:
        """Return the display label for *channel* (1-based)."""

    @abstractmethod
    def set_label(self, channel: int, label: str) -> None:
        """Set the display label for *channel* (1-based)."""

    # ── Visibility ────────────────────────────────────────────────────────────

    @abstractmethod
    def get_visible(self, channel: int) -> bool:
        """Return True if *channel* is currently displayed."""

    @abstractmethod
    def set_visible(self, channel: int, visible: bool) -> None:
        """Show or hide *channel*."""

    # ── Channel settings ──────────────────────────────────────────────────────

    @abstractmethod
    def get_channel(self, channel: int) -> dict:
        """Return channel settings.

        Returns a dict with keys:
          coupling  – 'DC' | 'AC' | 'GND'
          probe     – probe attenuation ratio (e.g. 10.0 for 10×)
          bwlimit   – True if bandwidth limit is enabled
          invert    – True if channel is inverted
        """

    @abstractmethod
    def set_channel(
        self,
        channel: int,
        coupling: str | None = None,
        probe: float | None = None,
        bwlimit: bool | None = None,
        invert: bool | None = None,
    ) -> None:
        """Set one or more channel settings for *channel*."""

    # ── X-axis (timebase) ─────────────────────────────────────────────────────

    @abstractmethod
    def get_x_axis(self) -> dict:
        """Return timebase settings as {'scale': float, 'offset': float} (seconds)."""

    @abstractmethod
    def set_x_axis(self, scale: float | None = None, offset: float | None = None) -> None:
        """Set timebase scale (s/div) and/or offset (s)."""

    # ── Y-axis (vertical) ─────────────────────────────────────────────────────

    @abstractmethod
    def get_y_axis(self, channel: int) -> dict:
        """Return vertical settings as {'scale': float, 'offset': float} (volts)."""

    @abstractmethod
    def set_y_axis(
        self,
        channel: int,
        scale: float | None = None,
        offset: float | None = None,
    ) -> None:
        """Set vertical scale (V/div) and/or offset (V) for *channel*."""

    # ── Trigger ───────────────────────────────────────────────────────────────

    @abstractmethod
    def get_trigger(self) -> dict:
        """Return trigger settings.

        Returns a dict with keys:
          source  – e.g. 'CH1', 'CH2', 'EXT'
          level   – trigger level in volts
          slope   – 'rising' | 'falling' | 'either'
          mode    – 'edge' | 'pulse' | 'video' | ...  (instrument-specific)
          sweep   – 'auto' | 'normal' | 'single'
        """

    @abstractmethod
    def set_trigger(
        self,
        source: str | None = None,
        level: float | None = None,
        slope: str | None = None,
        mode: str | None = None,
        sweep: str | None = None,
    ) -> None:
        """Set one or more trigger parameters."""

    # ── Measurements ─────────────────────────────────────────────────────────

    @abstractmethod
    def measure_params(self) -> list[str]:
        """Return the list of measurement parameter names supported by this driver."""

    @abstractmethod
    def measure(self, channel: int, param: str) -> float:
        """Return a single automatic measurement for *channel*.

        *param* is one of the strings returned by measure_params().
        """

    # ── Waveform data ─────────────────────────────────────────────────────────

    @abstractmethod
    def get_waveform(self, channel: int) -> tuple[list[float], list[float]]:
        """Return waveform data for *channel* as (time_s, voltage_v) arrays."""

    # ── Screenshot ────────────────────────────────────────────────────────────

    @abstractmethod
    def save_image(self, output_dir: str) -> str:
        """Capture a screenshot and write it to *output_dir*. Returns the file path."""

    # ── CSV (built on get_waveform — no driver override needed) ──────────────

    def save_csv(self, channel: int, output_dir: str) -> str:
        """Download waveform data for *channel* and write a CSV to *output_dir*.
        Returns the file path."""
        time_s, voltage_v = self.get_waveform(channel)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(output_dir, f"{stamp}_ch{channel}.csv")
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["time_s", "voltage_v"])
            writer.writerows(zip(time_s, voltage_v))
        return path

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def close(self) -> None:
        """Release the instrument resource. Override if needed."""
