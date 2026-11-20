---
name: montage-lite
description: "Video/gamified-content rules (OpenMontage lite): StoryForge first as the production contract, hook-weighted timing, fill every slot, never free-style a deliverable."
trigger_when:
  - video
  - script
  - reels
  - shorts
  - tiktok
  - youtube
  - montage
  - scene
  - shot
  - فيديو
  - سكريبت
  - ريلز
  - شورتس
  - تيك توك
  - مونتاج
  - مشهد
  - قصة
---

# Montage-lite (OpenMontage port)

PRE-PRODUCTION IS THE CONTRACT:

1. ANY video ask (Shorts, Reels, TikTok, YouTube) starts with the
   StoryForge tool — title + platform + scenes + duration. It computes
   the timing math, platform spec and slot structure. YOU do not
   invent timings by hand; the tool's math is ground truth.
2. Fill EVERY slot in story_board.md: visual, VO line, on-screen
   text, b-roll, audio cue, transition OUT. An empty slot = a hole in
   the final cut. Keep the timing exactly as generated.
3. VO discipline: <= 3 words/second. Arabic on-screen text must
   respect RTL mirroring (no clipped words at edges).
4. Appeals on delivery.md platform section: aspect, max duration,
   safe zones (app UI overlaps), -14 LUFS audio. Never ship outside
   these rails.

VOICE/SCRIPT quality bar:
- Hook scene answers the question "why should I watch 10 more
  seconds?" — no greeting, no intro music, no "كزيدي يا جماعة".
- One idea per scene. Concrete nouns, real numbers, no vague hype.
- Payoff scene: the answer + one-line takeaway + minimal CTA.

RENDER + VOICE PHASE (offline, no cloud):
- VisualForge BEFORE rendering: 'sheet' attaches real stock
  backgrounds per scene (Openverse cc0/pdm, license-ledgered in
  visual_sheet.md, budget-metered). RenderForge picks them up
  automatically and burns captions on top (darkened 58%).

- RenderForge turns the package into a real MP4 (scene cards,
  burned-in shaped-Arabic captions, exact durations). peek first,
  render after slots are filled.
- VoiceForge narrates the VO slots with Windows TTS: 'narrate'
  builds narration.wav synced to the exact scene timing; 'mux'
  combines it with render.mp4 into final.mp4. No Arabic SAPI voice
  installed? state it once and deliver the file anyway.

RENDER PHASE (later waves): the shot list is render-ready input —
scene, shot type, move, duration, sfx. Until a render engine is
wired, the deliverable is the export per delivery.md (editor-ready
bundle, e.g. CapCut/Resolve import sheet).
