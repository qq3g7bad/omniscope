"""Auto-detect the connected oscilloscope and return the appropriate driver."""

import re
import warnings
import pyvisa

from omniscope.base import OscilloscopeBase
from omniscope.drivers.rigol import RigolOscilloscope


# Maps IDN substring patterns (case-insensitive) to driver classes.
_DRIVER_MAP: list[tuple[str, type[OscilloscopeBase]]] = [
    (r"RIGOL", RigolOscilloscope),
]


def detect() -> OscilloscopeBase:
    """Open the first supported oscilloscope found via VISA and return its driver."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rm = pyvisa.ResourceManager()
        resources = rm.list_resources()
    if not resources:
        raise RuntimeError("No VISA resources found. Is the oscilloscope connected?")

    errors: list[str] = []
    for resource in resources:
        try:
            inst = rm.open_resource(resource)
            inst.timeout = 10000
            idn = inst.query("*IDN?").strip()
        except Exception as e:
            errors.append(f"{resource}: {e}")
            continue

        for pattern, cls in _DRIVER_MAP:
            if re.search(pattern, idn, re.IGNORECASE):
                return cls(inst, idn)

        inst.close()

    tried = "; ".join(errors) if errors else "none responded"
    raise RuntimeError(
        f"No supported oscilloscope found. Resources tried: {list(resources)}. Errors: {tried}"
    )
