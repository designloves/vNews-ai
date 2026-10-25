#!/usr/bin/env python3
"""Record one edition's brief in several Kokoro voices (plus the current Piper recording) so they can be
compared by ear on samples/index.html. Runs in GitHub Actions (.github/workflows/voice-samples.yml)."""
import json, os, re, shutil, subprocess, sys, tempfile
import numpy as np, soundfile as sf
from kokoro import KPipeline

sys.path.insert(0, os.path.dirname(__file__))
from make_audio import spoken_text  # same words as the daily recording

DATE = sys.argv[1] if len(sys.argv) > 1 else "2026-10-23"
VOICES = [  # (voice id, label)
    ("bf_emma", "Kokoro · Emma (British, female)"),
    ("bf_isabella", "Kokoro · Isabella (British, female)"),
    ("bm_george", "Kokoro · George (British, male)"),
    ("bm_fable", "Kokoro · Fable (British, male)"),
    ("af_heart", "Kokoro · Heart (American, female)"),
    ("af_bella", "Kokoro · Bella (American, female)"),
    ("am_michael", "Kokoro · Michael (American, male)"),
]
RATE = 24000
pipes = {}


def kokoro(text, voice, wav):
    lang = voice[0]  # 'b' British, 'a' American
    pipe = pipes.get(lang) or pipes.setdefault(lang, KPipeline(lang_code=lang, repo_id="hexgrad/Kokoro-82M"))
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    gap = np.zeros(int(RATE * 0.16), dtype=np.float32)
    parts = []
    for _, _, audio in pipe("\n".join(sentences), voice=voice, speed=1.0, split_pattern=r"\n+"):
        a = audio.numpy() if hasattr(audio, "numpy") else np.asarray(audio)
        parts += [a.astype(np.float32), gap]
    sf.write(wav, np.concatenate(parts), RATE)


def to_mp3(wav, mp3):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                    "-ac", "1", "-ar", "24000", "-codec:a", "libmp3lame", "-b:a", "64k", mp3], check=True)


def main():
    with open(f"editions/{DATE}.json") as f:
        text = spoken_text(DATE, json.load(f))
    os.makedirs("samples", exist_ok=True)
    items = []
    if os.path.exists(f"editions/{DATE}.mp3"):
        shutil.copy(f"editions/{DATE}.mp3", "samples/piper-cori.mp3")
        items.append(("piper-cori.mp3", "Piper · Cori (British, female) — current voice"))
    for voice, label in VOICES:
        with tempfile.TemporaryDirectory() as tmp:
            wav = os.path.join(tmp, "a.wav")
            print("recording", voice, flush=True)
            kokoro(text, voice, wav)
            to_mp3(wav, f"samples/{voice}.mp3")
        items.append((f"{voice}.mp3", label))
    rows = "\n".join(f'<li><p>{label}</p><audio controls preload="none" src="{f}"></audio></li>' for f, label in items)
    with open("samples/index.html", "w") as f:
        f.write(f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Voice samples</title>
<style>:root{{color-scheme:light dark}}body{{margin:0;padding:24px 16px 48px;font:17px/1.5 Georgia,serif;background:#eeeadf;color:#2f2d28}}
@media (prefers-color-scheme:dark){{body{{background:#1f1e1b;color:#d6d1c4}}}}
main{{max-width:560px;margin:0 auto}}h1{{font-size:24px;margin:0 0 4px}}.lead{{margin:0 0 20px;opacity:.75}}
ul{{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:18px}}li p{{margin:0 0 6px;font-weight:600}}audio{{width:100%}}</style>
</head><body><main><h1>Voice samples</h1><p class="lead">The brief for {DATE}, read by each candidate voice.</p><ul>
{rows}
</ul></main></body></html>
""")


if __name__ == "__main__":
    main()
