---
name: agx-wireless-radio-security
description: "wireless-radio-security"
trigger_when: "wireless-radio-security,wireless,bluetooth,security,skill,coverage,map"
source: antigravity-pentest-skills/
---
---
name: wireless-radio-security
description: >-
  Use this skill when auditing Wi-Fi networks (WPA2/WPA3 Enterprise), analyzing SDR/RF communications, or testing Bluetooth/BLE devices.
  Covers Rogue AP setup, EAP-TLS downgrade, BLE spoofing, Sub-1GHz capturing, and SDR tools (GNU Radio, GQRX).
---

## Wireless, RF & Bluetooth Security Skill

Radio frequency auditing, Wi-Fi Enterprise attacks, SDR signal analysis, and BLE security.

### Coverage Map

| Reference File | Contents |
|---|---|
| [wpa3-enterprise-attacks.md](references/wpa3-enterprise-attacks.md) | EAP-PEAP/EAP-TTLS credential harvesting, Rogue AP with hostapd-mana |
| [ble-sdr-rf-security.md](references/ble-sdr-rf-security.md) | Bluetooth Low Energy GATT manipulation, Sub-1GHz signal replay, HackRF/RTL-SDR |
