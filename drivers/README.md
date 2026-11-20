# drivers/README.md

## WormDrv â€” Ù‚Ø§Ù„Ø¨ Ø§Ù„Ø¨Ø±Ù†Ø§Ù…Ø¬ Ø§Ù„Ù…ØµØºÙ‘Ø± (kernel driver) Ù„Ù„Ù‚Ø±Ø§Ø¡Ø©/Ø§Ù„ÙƒØªØ§Ø¨Ø© Ù…Ù† Ø§Ù„Ù†ÙˆØ§Ø©

Ù‡Ø°Ø§ Ù‚Ø§Ù„Ø¨ WDM Ù…Ù…ØªØ§Ø² Ù„ØªÙ‚Ø¨Ù„ Ø§Ù„Ù‚Ø±Ø§Ø¡Ø©/Ø§Ù„ÙƒØªØ§Ø¨Ø© ÙÙŠ Ø°Ø§ÙƒØ±Ø© Ø¹Ù…Ù„ÙŠØ© Ø£Ø®Ø±Ù‰ Ø¹Ø¨Ø± `MmCopyVirtualMemory`. 
ØªØ·Ø¨ÙŠÙ‚ ØªØ´ØºÙŠÙ„ÙŠ Ù…Ø­ÙƒÙ… Ø¹Ø¨Ø± ring-0Ù†ÙŠ artifact (Ø¨Ù„Ø§ proc Ù…Ø® Grants). *ÙŠÙØ³ØªÙŽØ®Ø¯ÙŽÙ… ÙÙ‚Ø· Ø¹Ù„Ù‰ Ù†Ø¸Ø§Ù…Ùƒ ÙˆÙ…Ù„ÙØ§ØªÙƒ.*

### Ø§Ù„ØªØ±ÙƒÙŠØ¨

- `wormdrv.c`    â€” Ø´ÙØ±Ù‘Ø© Ø§Ù„ driver (IOCTL: open/read/write/close).
- `py_client.py` â€” Ø¹Ù…ÙŠÙ„ Python Ø¹Ø¨Ø± CreateFileW + DeviceIoControl.
- `build.ps1`    â€” Ø³Ù„Ø³Ù„Ø© Ø§Ù„Ø¨Ù†Ø§Ø¡ Ø¹Ø¨Ø± MSBuild + WDK.

### Ø§Ù„Ù…ØªØ·Ù„Ø¨Ø§Øª

1. Visual Studio 2022 (C++ workload + WDK affinity).
2. Windows Driver Kit (WDK) 10/11.

### Ø§Ù„Ø¨Ù†Ø§Ø¡ ÙˆØ§Ù„ØªØ­Ù…ÙŠÙ„

```powershell
cd 🔥😈 PORT 777 EVIL ☠️🔥👹_Ultra_Singularity\drivers\wormdrv
.\build.ps1              # Ø§Ù„Ù†Ø§ØªØ¬ ÙÙŠ bin\wormdrv.sys

# Ø¥Ø´Ø±Ø§Ùƒ Ø¹Ø¯Ø¯ kernel TestBed mode (SHELL AS ADMIN):
bcdedit /set testsigning on

# ØªØ«Ø¨ÙŠØª Ø§Ù„Ø®Ø¯Ù…Ø©:
sc create WormDrv type= kernel binPath="<full path to bin\wormdrv.sys>"
sc start WormDrv
```

### ØªØ¬Ø±Ø¨Ø© Ø³Ø±ÙŠØ¹Ø©

```powershell
python py_client.py <pid> 0x00007FF600000000
```

### Ø¥ÙŠÙ‚Ø§Ù ÙˆØ¥Ø²Ø§Ù„Ø©

```powershell
sc stop WormDrv
sc delete WormDrv
```

Ù…Ù„Ø§Ø­Ø¸Ø© Ø£Ù…Ù†ÙŠØ©: ÙƒÙ„ Ø§Ø³ØªØ¯Ø¹Ø§Ø¡ ÙŠÙ‚ÙŠÙ‘Ø¯ Ø§Ù„Ø­Ø¬Ù… (128MB) ÙˆÙŠØ­Ø¸Ø± Ø§Ù„Ø¹Ù…Ù„ÙŠØ§Øª Ø§Ù„Ø­Ø³Ø§Ø³Ø© (Protected 
Processes). Ù„Ø§ ØªÙØ³ØªØ®Ø¯ÙŽÙ… Ø¶Ø¯ Ø¨Ø±Ù…Ø¬ÙŠØ§ØªÙ… Ù„Ø§ ØªÙ…Ù„ÙƒÙ‡Ø§ â€” Ø§Ø³ØªØ®Ø¯Ù…Ù‡Ø§ ÙÙŠ Ø¨ÙŠØ¦Ø© Ø§Ø®ØªØ¨Ø§Ø±/ØªØ¹Ù„ÙŠÙ…ÙŠØ©.
