---
name: builder-game
description: "Build playable HTML5-canvas or Python games end-to-end: loop, input, states, difficulty curve."
trigger_when:
  - game
  - play
  - canvas
  - arcade
  - لعبة
  - العاب
  - جمس
---

# Shipping a playable game

WORKFLOW:
1. One-line design: core loop + win/lose + one twist. Small scope FIRST,
   polish after it plays.
2. ProjectForge kind=game → a working brick-breaker skeleton (canvas,
   rAF loop, keyboard input, score, respawn). For 2-player/other genres,
   keep the same loop skeleton and swap entities.
3. Extend to the requested genre ONLY while the game REMAINS RUNNABLE
   after each edit. State machine: menu → play → win/lose → restart.
4. VERIFY by reading the loop: every frame must (a) update, (b) draw,
   (c) handle edges (pause/resume on blur, dt clamp so tab-switching
   does not teleport the ball).
5. SHIP one self-contained html (embedded style+script) unless bigger.

RULES:
- 60fps discipline: no allocation inside the hot loop; reuse objects.
- Input: keyboard + mouse + touch (pointer events); preventDefault.
- Juice (cheap, big effect): screen shake on hit, hit flash, easing on
  UI tweens, one sound via WebAudio oscillator (no external files).
- Difficulty curve: first 30 seconds easy, ramps after; never random-
  spike. Deterministic seeds when the task says "fair".
- Python games (pygame) only when asked: same loop rules apply.
