#!/usr/bin/env python3
"""Quick test: generate TTS for scene 1 seg 0 only."""
import json, os, time, soundfile as sf, torch, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qwen_tts import Qwen3TTSModel

SCENE_JSON = sys.argv[1] if len(sys.argv) > 1 else "output/scenes/scene_01.json"

print("Loading model...", flush=True)
t0 = time.time()
model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
    device_map=None, dtype=torch.float32, attn_implementation=None,
)
print(f"Model loaded: {time.time()-t0:.0f}s", flush=True)

with open(SCENE_JSON) as f:
    scene = json.load(f)

seg_dir = os.path.join("output/audio", f"scene_{scene['scene_num']:02d}")
os.makedirs(seg_dir, exist_ok=True)

total_cpu = 0
total_audio = 0
for i, seg in enumerate(scene["segments"]):
    text = seg["text"]
    out = os.path.join(seg_dir, f"seg_{i:02d}.wav")
    
    if os.path.isfile(out) and os.path.getsize(out) > 1000:
        import subprocess
        r = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", out], capture_output=True, text=True)
        dur = float(r.stdout.strip())
        print(f"  Seg {i}: exists {dur:.1f}s")
        total_audio += dur
        continue
    
    print(f"  Seg {i} ({len(text)} chars)...", end=" ", flush=True)
    t1 = time.time()
    wavs, sr = model.generate_custom_voice(text=text, language="German", speaker="ryan")
    elapsed = time.time() - t1
    dur = len(wavs[0]) / sr
    sf.write(out, wavs[0], sr)
    total_cpu += elapsed
    total_audio += dur
    print(f"OK audio={dur:.1f}s cpu={elapsed:.0f}s")

print(f"\nTotal: audio={total_audio:.1f}s, cpu={total_cpu:.0f}s, ratio={total_cpu/max(total_audio,1):.1f}x")
