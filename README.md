# cover.hd_powerview
Home Assistant component for controlling Hunter Douglas / Luxaflex PowerView Window Shades

This will read all the shades from the hub and present them as cover.name in Home Assistant.

You can then make them go up, down, stop or go to a set position via a slider.

```yaml
cover:
  - platform: hd_powerview
    host: your_hub_ip_address
```
