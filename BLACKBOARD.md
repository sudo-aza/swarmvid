# BLACKBOARD — swarmvid Task Board

> **Project**: swarmvid — AI video production pipeline
> **Repo**: `sudo-aza/swarmvid`
> **Current Video**: Die Geschichte Hannovers
> **Language**: German (Deutsch)
> **Last updated**: 2026-06-19

---

## Project Vision

Build an automated video production pipeline where multiple AI agents collaborate via a shared blackboard to produce documentary videos. The current project is a German-language documentary about the history of Hannover, Germany.

---

## Video Specification

- **Topic**: Die Geschichte Hannovers (History of Hannover)
- **Language**: German (Deutsch)
- **TTS Voice**: Qwen 3 — `jam` voice, WAV format
- **Resolution**: 1280x720 (HD)
- **Style**: Animated infographic with gradient backgrounds, floating particles, timeline animations, fact displays
- **Audio**: TTS narration with scene transitions
- **Sources**: Displayed on-screen during relevant scenes
- **Detail Level**: MAXIMUM — every scene must be thorough with specific dates, names, events, and context. No summaries or hand-waving. The narration should feel like a proper German documentary (e.g. ZDF/ARD Historien-Dokumentation).

---

## Scene Breakdown

| Scene | Title | Era | Key Topics to Cover | Target Duration |
|-------|-------|-----|--------------------|-----------------|
| 1 | Gründung und frühe Geschichte | 1100-1300 | Leine crossing, river trade routes, first mention 1150, market rights, early settlement growth, medieval guilds, church construction | ~90s |
| 2 | Die Residenz der Welfen | 14th-17th c. | House of Welf origin, Duke Otto, expansion of residence, castle construction, Leineschloss, court culture, Reformation impact on Hannover | ~120s |
| 3 | Der Dreißigjährige Krieg | 1618-1648 | Hannover's strategic position, occupation phases, Tilly's campaigns, fortification efforts, population losses, post-war recovery, role in Peace of Westphalia | ~100s |
| 4 | Hannovers Goldenes Zeitalter | 17th-18th c. | Ernst August, Personal Union with England, Georg I becomes King of Great Britain 1714, Baroque architecture, Herrenhäuser Gärten, Leineschloss expansion, court culture, scientific/philosophical developments, Göttingen University founding | ~150s |
| 5 | Das Königreich Hannover | 1814-1866 | Congress of Vienna elevation to kingdom, Wilhelm IV, personal union with Britain ends 1837 (Victoria cannot inherit Hannover), Ernst August's reactionary constitution repeal, 1837 revolution, annexation by Prussia 1866 | ~120s |
| 6 | Industrialisierung und Moderne | 1866-1933 | Prussian province era, industrial growth, railway hub, Maschinenfabrik, population boom, WWI impact, Weimar Republic culture, modernist architecture, Hannover Messe trade fair origins | ~120s |
| 7 | Der Zweite Weltkrieg | 1933-1945 | Nazi rise, synagogue destruction 1938, Allied bombing raids, Operation Gomorrah context, 88 air raids, 90% city center destroyed, forced labor camps, liberation April 1945, specific dates and damage statistics | ~120s |
| 8 | Nachkriegszeit und Wiederaufbau | 1945-present | Rubble clearance, reconstruction architecture, EXPO 2000, modern Hannover as tech hub, Leibniz University, cultural institutions, Volkswagen commercial vehicle plant, today's population and economy | ~120s |

**Target total runtime: ~12-15 minutes**

---

## Production Notes

- Each scene requires 3-5 TTS segments (each <1024 characters for TTS API limit)
- 10-12 second delay between TTS API calls to avoid rate limiting
- Audio format must be WAV (not MP3 — ffmpeg compatibility)
- Frame rendering via Python/Pillow → ffmpeg pipe (not moviepy — OOM issues)
- Sources must appear on screen during relevant scenes (URLs or book citations)
- No scripts/, no output/ committed to repo — only BLACKBOARD.md + README.md

---

## TODO

| # | Task | Assigned To | Status | Created |
|---|------|-------------|--------|---------|
| 1 | Research Hannover history — deep dive on all 8 eras, collect specific dates/names/events/sources | Researcher | **pending** | 2026-06-19 |
| 2 | Write detailed German narration script (8 scenes, 3-5 segments each, max detail) | Writer | **pending** | 2026-06-19 |
| 3 | Generate TTS audio for all segments (Qwen 3, jam voice, WAV, 10-12s spacing) | Producer | **pending** | 2026-06-19 |
| 4 | Generate scene illustrations (AI images per scene) | Producer | **pending** | 2026-06-19 |
| 5 | Assemble video (Pillow frame render → ffmpeg pipe, 1280x720) | Producer | **pending** | 2026-06-19 |
| 6 | Final review and upload | — | **pending** | 2026-06-19 |
