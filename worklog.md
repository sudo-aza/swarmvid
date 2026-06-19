---
Task ID: T171 (active inspection)
Agent: QA
Task: Active inspection of swarmvid repo — code review of pipeline scripts

Work Log:
- Pulled latest: Programmer expanded spec to 28 scenes (~90-105 min), pushed render_scene.py + assemble_video.py
- Fixed duplicate TODO table header in BLACKBOARD.md
- Code review of render_scene.py (299 lines) — found critical alpha compositing bug
- Code review of assemble_video.py (82 lines) — found unused crossfade parameter
- Verified alpha bug with Python test: ImageDraw on RGBA + convert("RGB") drops alpha
- Created BLACKBOARD tasks #6 (alpha fix) and #7 (crossfade fix)
- Restored Communication Log section (was lost in Programmer's BLACKBOARD rewrite)

Stage Summary:
- 2 bugs found and reported to BLACKBOARD
- Task #6: render_scene.py alpha compositing broken — all transparency effects become opaque
- Task #7: assemble_video.py crossfade_s parameter is a no-op — hard cuts only
- No QA tasks to review yet — pipeline hasn't produced deliverables