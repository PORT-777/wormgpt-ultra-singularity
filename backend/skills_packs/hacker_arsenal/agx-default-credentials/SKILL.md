---
name: agx-default-credentials
description: "default-credentials"
trigger_when: "default-credentials,default,credentials,password,attacks,coverage,map,quick,decision,tree"
source: antigravity-pentest-skills/
---
---
name: default-credentials
description: >-
  Use when performing credential attacks against any service, device, or application.
  Covers default credential lookup for network devices, web applications, databases,
  IoT/cameras, and industrial control systems. Also covers active brute-force with
  Hydra/Medusa, password spraying against Active Directory and cloud (M365/Azure/AWS),
  hash cracking with Hashcat/John, credential stuffing from combo lists, and wordlist
  selection/generation. Invoke whenever a login panel, SSH service, database port, or
  SNMP device is discovered, or when captured hashes need cracking.
---

## Default Credentials & Password Attacks

### Coverage Map

| Reference File | Topics Covered |
|---|---|
| [network-device-creds.md](references/network-device-creds.md) | Cisco, Juniper, Palo Alto, Fortinet, Mikrotik, Ubiquiti, TP-Link, Netgear, D-Link, ASUS default creds |
| [web-application-creds.md](references/web-application-creds.md) | WordPress, Joomla, Jenkins, GitLab, Grafana, Kibana, Tomcat, WebLogic, JBoss, Sonarqube, Portainer |
| [database-creds.md](references/database-creds.md) | MySQL, PostgreSQL, MSSQL, Oracle, MongoDB, Redis, CouchDB, Cassandra, Neo4j, InfluxDB |
| [iot-device-creds.md](references/iot-device-creds.md) | Hikvision, Dahua, AXIS, Foscam, IP cameras, smart home devices |
| [industrial-creds.md](references/industrial-creds.md) | Siemens, Schneider Electric, Rockwell, Honeywell SCADA/ICS/PLCs |
| [hydra-attacks.md](references/hydra-attacks.md) | Hydra brute-force: SSH, FTP, HTTP, SMTP, RDP, SMB, MySQL, VNC, Telnet |
| [wordlists.md](references/wordlists.md) | rockyou, SecLists, fuzzDicts, hashcat rules, crunch, CeWL generation |
| [spray-attacks.md](references/spray-attacks.md) | Kerbrute, Spray, Ruler, MSOLSpray, password spraying methodology |
| [hash-cracking.md](references/hash-cracking.md) | Hashcat modes & rules, John the Ripper, rainbow tables, online crackers |
| [credential-stuffing.md](references/credential-stuffing.md) | Combo lists, stuffing methodology, detection evasion, validation |

### Quick Decision Tree

```
Found a login panel / service?
├── Is it a known product? → Check network-device-creds / web-application-creds / database-creds / iot-device-creds / industrial-creds
├── Need to brute-force?   → hydra-attacks.md
├── Have a username list?  → spray-attacks.md (low-and-slow)
├── Have hashes?           → hash-cracking.md
├── Have combo lists?      → credential-stuffing.md
└── Need wordlists?        → wordlists.md
```

### Universal Default Credential Check (Quick Start)

```bash
## Search ihebski DefaultCreds sheet (CSV)
curl -sL https://raw.githubusercontent.com/ihebski/DefaultCreds-cheat-sheet/main/DefaultCreds-Cheat-Sheet.csv | grep -i "cisco"

## Clone locally
git clone https://github.com/ihebski/DefaultCreds-cheat-sheet
cd DefaultCreds-cheat-sheet
python3 creds.py search cisco
python3 creds.py search tomcat

## cirt.net online lookup
curl -s "https://www.cirt.net/passwords?criteria=cisco" | grep -oP '(?<=<td>)[^<]+' | head -40
```

### Top 20 Universal Defaults to Always Try

| Username | Password | Notes |
|---|---|---|
| admin | admin | Most common |
| admin | password | Very common |
| admin | (blank) | Many devices |
| admin | 1234 | Consumer routers |
| admin | 12345 | Consumer IoT |
| admin | admin123 | Web apps |
| root | root | Linux defaults |
| root | toor | Kali Linux |
| root | (blank) | Many Linux devices |
| administrator | administrator | Windows |
| guest | guest | Guest accounts |
| user | user | Generic |
| test | test | Dev/test |
| demo | demo | Demo accounts |
| support | support | Vendor accounts |
| service | service | Service accounts |
| operator | operator | Industrial |
| cisco | cisco | Cisco IOS |
| enable | cisco | Cisco enable |
| ubnt | ubnt | Ubiquiti |
