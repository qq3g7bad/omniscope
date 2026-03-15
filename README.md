# omniscope

A unified CLI tool for controlling oscilloscopes from the terminal.

Abstracts manufacturer-specific differences that VISA/SCPI alone does not cover, providing a unified command set across supported instruments. All commands produce structured, machine-readable output — suitable for scripting and AI-assisted workflows.

## Supported instruments

| Manufacturer | Series |
|---|---|
| Rigol | DHO800, DHO900 |

Adding support for a new manufacturer requires implementing one Python class. See [Contributing](#contributing).

## Requirements

- Python 3.10 or newer
- Oscilloscope connected via USB or LAN

### Linux

USB instruments require the kernel `usbtmc` driver (included in all mainstream distributions) and read/write access to `/dev/usbtmc*`. If you get a permission error, create a udev rule:

```sh
sudo tee /etc/udev/rules.d/60-usbtmc.rules << 'EOF'
SUBSYSTEM=="usb", ATTRS{idVendor}=="1ab1", MODE="0664", GROUP="plugdev"
KERNEL=="usbtmc*", ATTRS{idVendor}=="1ab1", MODE="0664", GROUP="plugdev"
EOF
sudo udevadm control --reload-rules && sudo udevadm trigger
```

Replace `1ab1` with your instrument's USB vendor ID if not Rigol. Your user must be in the `plugdev` group (`groups` to check).

### Windows

LAN connections work out of the box. For USB, Windows has no built-in USBTMC driver — install one of the following:

| Option                                                                           | Notes                                                                                  |
| -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| [NI-VISA](https://www.ni.com/en/support/downloads/drivers/download.ni-visa.html) | Recommended. Free, installs USB drivers automatically.                                 |
| libusb + [Zadig](https://zadig.akeo.ie/)                                         | No extra software, but requires manually replacing the USB driver for each instrument. |

NI-VISA is automatically preferred over pyvisa-py when installed — no configuration needed.

## Installation

### Linux / macOS

```sh
sh install.sh
```

### Windows

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

The install script will:
1. Check that Python 3.10+ is available and print instructions if not
2. Create a local virtual environment (`venv/`)
3. Install the package and its dependencies
4. **Linux/macOS**: create an `omniscope` symlink in `~/.local/bin/`

If Python is not installed:

- **macOS**: `brew install python` — [Homebrew](https://brew.sh)
- **Linux**: `sudo apt install python3` / `sudo dnf install python3`
- **Windows**: [python.org/downloads](https://www.python.org/downloads/) — check *Add Python to PATH* during setup, or run `winget install Python.Python.3.12`

## Uninstallation

### Linux / macOS

```sh
rm ~/.local/bin/omniscope
rm -rf venv/
```

### Windows

```powershell
Remove-Item -Force "$env:USERPROFILE\.local\bin\omniscope.bat"
Remove-Item -Recurse -Force venv
```

## Usage

| Platform | Command |
|---|---|
| Linux / macOS | `omniscope <subcommand> [options]` |
| Windows | `omniscope <subcommand> [options]` |

The examples below use `omniscope` for brevity.

---

### Labels

```sh
# Get labels for all channels
omniscope get-label

# Get label for channel 1 only
omniscope get-label --ch1

# Set labels
omniscope set-label --ch1 SDA --ch2 SCL
```

### Visibility

```sh
# Get visibility of all channels
omniscope get-visible

# Show channel 1, hide channel 2
omniscope set-visible --ch1 on --ch2 off
```

### Time axis

```sh
# Get current timebase
omniscope get-x-axis

# Set scale to 1 ms/div, offset to 0
omniscope set-x-axis --scale 0.001 --offset 0
```

### Voltage axis

```sh
# Get vertical settings for channels 1 and 2
omniscope get-y-axis --ch1 --ch2

# Set channel 1 to 1 V/div
omniscope set-y-axis --ch1 --scale 1.0

# Set channels 1 and 2 together
omniscope set-y-axis --ch1 --ch2 --scale 0.5 --offset 0
```

### Saving data

```sh
# Save a screenshot to the current directory
omniscope save-image

# Save screenshot to a specific directory
omniscope save-image -o ./captures

# Save waveform CSV for channels 1 and 2
omniscope save-csv --ch1 --ch2

# Save screenshot + CSV for all currently visible channels
omniscope save

# Save screenshot + CSV for specific channels
omniscope save --ch1 --ch2 -o ./captures
```

Output files are timestamped: `20240315_123456.png`, `20240315_123456_ch1.csv`.

### JSON output

All `get-*` commands support `--json` for structured output:

```sh
omniscope get-label --json
```

```json
{
  "ch1": "SDA",
  "ch2": "SCL",
  "ch3": "CH3",
  "ch4": "CH4"
}
```

```sh
omniscope get-x-axis --json
```

```json
{
  "scale": 0.001,
  "offset": 0.0
}
```

## Contributing

### Adding a new instrument driver

1. Create `omniscope/drivers/<manufacturer>.py` and implement `OscilloscopeBase` (defined in `omniscope/base.py`).
2. Register the driver in `omniscope/drivers/registry.py` by adding an entry to `_DRIVER_MAP`:

```python
(r"KEYSIGHT", KeysightOscilloscope),
```

The auto-detect logic queries `*IDN?` and matches the response against these patterns.

### Project structure

```
omniscope/
  base.py          # abstract interface — defines all supported operations
  cli.py           # subcommand definitions and argument parsing
  drivers/
    registry.py    # auto-detection via *IDN?
    rigol.py       # Rigol implementation
```

## License

MIT
