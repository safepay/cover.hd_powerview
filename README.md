(https://img.shields.io/github/release/safepay/cover.hd_powerview.svg)](https://github.com/safepay/cover.hd_powerview) ![Maintenance](https://img.shields.io/maintenance/yes/2019.svg)

# cover.hd_powerview
Home Assistant component for controlling Hunter Douglas / Luxaflex PowerView Window Shades.

This will read all the shades from the hub and present them as cover.name in Home Assistant.

You can then make them go up, down, stop or go to a set position via a slider.

# Cover
## Installation
Copy all the files to a custom_components/hd_powerview directory in your Home Assistant folder.

## Configuration
```yaml
cover:
  - platform: hd_powerview
    host: your_hub_ip_address
```
