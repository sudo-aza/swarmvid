#!/usr/bin/env python3
"""generate_tts_chunk.py — Generate a single TTS chunk as a subprocess.

This script is called by generate_tts_batch.py for each chunk to ensure
complete memory isolation between chunks (no OOM accumulation).

Usage:
  python generate_tts_chunk.py "text" output.wav [--speaker ryan]
"""

import argparse
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("text", type=str, help="Text to synthesize")
    parser.add_argument("output", type=str, help="Output WAV path")
    parser.add_argument("--speaker", type=str, default="ryan")
    parser.add_argument("--language", type=str, default="German")
    parser.add_argument("--model", type=str, default="Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice")
    args = parser.parse_args()

    import gc
    import os

    t0 = time.time()

    # Suppress warnings
    import warnings
    warnings.filterwarnings("ignore")

    import torch
    from qwen_tts import Qwen3TTSModel
    import soundfile as sf

    # Load model
    model = Qwen3TTSModel.from_pretrained(
        args.model,
        device_map=None,
        dtype=torch.float32,
        attn_implementation=None,
    )

    # Generate
    wavs, sr = model.generate_custom_voice(
        text=args.text,
        language=args.language,
        speaker=args.speaker,
        instruct="",
    )

    # Write immediately
    audio_dur = len(wavs[0]) / sr
    wav_arr = wavs[0].numpy() if hasattr(wavs[0], 'numpy') else wavs[0]
    sf.write(args.output, wav_arr, sr)

    cpu_time = time.time() - t0
    # Output result as JSON for parent to parse
    print(f'{{"audio_dur": {audio_dur:.2f}, "cpu_time": {cpu_time:.1f}}}')


if __name__ == "__main__":
    main()
