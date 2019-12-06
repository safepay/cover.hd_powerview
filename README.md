![GitHub release (latest by date)](https://img.shields.io/github/v/release/safepay/cover.hd_powerview) ![Maintenance](https://img.shields.io/maintenance/yes/2019.svg)



# Hunter Douglas / Luxaflex Cover for Home Assistant
Home Assistant custom component for controlling [Hunter Douglas](https://www.hunterdouglas.com/operating-systems/motorized/powerview-motorization) / [Luxaflex](https://www.luxaflex.com.au/products/smart-home-automation-and-motorisation/powerview-motorisation/) PowerView Bottom-Up Window Shades.

This does not support Top-Down shades or tilting Venetian blinds.

This will read all the shades from the hub and present them as cover.name in Home Assistant.

You can then make them go up, down, stop or go to a set position via a slider.

Use the entities in automations to take direct control of your window shades.

# Cover
## Installation
Copy all the files to a custom_components/hd_powerview directory in your Home Assistant folder.

## Configuration
```yaml
cover:
  - platform: hd_powerview
    host: your_hub_ip_address
```

### Battery Levels
If your shade has a battery, you can extract the battery_level attribute with a sensor template. For example:
```yaml
sensor:
  - platform: template
    sensors:
      shade_1_battery_level:
        friendly_name: 'Shade 1 Battery Level'
        value_template: '{{state_attr("cover.shade_1", "battery_level")}}'
        unit_of_measurement: "%"
        device_class: battery
```
Replace ```cover.shade_1``` with your cover's entity name and rename the sensor to suit your system.
