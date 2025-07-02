#  BLE Asys pool Management Systems for Home Assistant


[![HACS][install-shield]](https://hacs.xyz/docs/use/)

This integration allows to monitor Bluetooth Low Energy (BLE) like asys precise'o+ systemsfrom within [Home Assistant](https://www.home-assistant.io/). After installation, no configuration is required. You can use the [ESPHome Bluetooth proxy][btproxy-url] to extend the bluetooth coverage range.

![dashboard](https://github.com/user-attachments/assets/76d722d7-45da-44a7-927a-eff7f493be9d)



* [Features](#features)
* [Installation](#installation)
* [Removing the Integration](#removing-the-integration)
* [Troubleshooting](#troubleshooting)
    * [Known Issues](#known-issues)
* [FAQ](FAQ)
* [Thanks to](#thanks-to)
* [References](#references)

## Features


### Supported Devices
- ASYS precise'o+
### Provided Information


## Installation


## Removing the Integration
This integration follows standard integration removal. No extra steps are required.
<details><summary>To remove an integration instance from Home Assistant</summary>

1. Go to <a href="https://my.home-assistant.io/redirect/integrations">Settings > Devices & services</a> and select the integration card.
1. From the list of devices, select the integration instance you want to remove.
1. Next to the entry, select the three-dot menu. Then, select Delete.
</details>

## Troubleshooting

> [!NOTE]
> A lot of transient issues are due to problems with Bluetooth adapters. Most prominent example is the performance limitation of the [internal Raspberry Pi BT adapter](https://www.home-assistant.io/integrations/bluetooth/#cypress-based-adapters), resulting in, e.g., sometimes wrong data, when you have multiple devices. Please check the Home Assistant [Bluetooth integration](https://www.home-assistant.io/integrations/bluetooth/) page for known issues and consider using a [recommended high-performance adapter](https://www.home-assistant.io/integrations/bluetooth/#known-working-high-performance-adapters).

### Known Issues



### In case you have troubles you'd like to have help with

- please [enable the debug protocol](https://www.home-assistant.io/docs/configuration/troubleshooting/#debug-logs-and-diagnostics),
- restart Home Assistant, wait till it is fully started up,
- reproduce the issue,
- disable the log (Home Assistant will prompt you to download the log), and finally
- [open an issue](https://github.com/tom42530/asys_ble_ha/issues/new?assignees=&labels=question&projects=&template=support.yml) with a good description of what your question/issue is and attach the log, or
- [open a bug](https://github.com/tom42530/asys_ble_ha/issues/new?assignees=&labels=Bug&projects=&template=bug.yml) if you think the behaviour you see is caused by the integration, including a good description of what happened, your expectations, and attach the log.


## FAQ
### light control is grayed out
It meens that ble device is not well paired.Some characteristics can't be read if authentification is not done.Please presse pairing button on device



## Thanks to


## References
