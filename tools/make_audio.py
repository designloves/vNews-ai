#!/usr/bin/env python3
"""Turn each edition's spoken brief into an MP3 with Piper (a local, open-source neural voice).

Runs in GitHub Actions (see .github/workflows/audio.yml). For every editions/YYYY-MM-DD.json that has a
"brief", it writes editions/YYYY-MM-DD.mp3 and records it in editions/audio.json, which the page reads to
know which editions have audio. An edition is only re-recorded when its spoken text (or the voice) changes.
"""
import datetime, glob, hashlib, json, os, re, subprocess, sys, tempfile

VOICE = os.environ.get("PIPER_VOICE", "voices/en_GB-cori-high.onnx")
MANIFEST = "editions/audio.json"


def spoken_text(date, edition):
    d = datetime.date.fromisoformat(date)
    long_date = f"{d.strftime('%A')} {d.day} {d.strftime('%B')} {d.year}"
    text = f"Vertical News. {long_date}. {edition['brief'].strip()} That's the brief. The full stories are on the page."
    text = re.sub(r"(\d)\s*[–-]\s*(\d)", r"\1 to \2", text)   # 21–22 -> 21 to 22
    text = text.replace(" · ", ", ").replace("—", ", ").replace("–", ", ")
    return re.sub(r"\s+", " ", text).strip()


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout.strip()
    return round(float(out), 1)


def main():
    manifest = {}
    if os.path.exists(MANIFEST):
        with open(MANIFEST) as f:
            manifest = json.load(f)
    changed = False
    for path in sorted(glob.glob("editions/????-??-??.json")):
        date = os.path.basename(path)[:-5]
        with open(path) as f:
            edition = json.load(f)
        if not str(edition.get("brief", "")).strip():
            print(f"{date}: no brief, skipped")
            continue
        text = spoken_text(date, edition)
        sha = hashlib.sha1((os.path.basename(VOICE) + "\n" + text).encode()).hexdigest()[:12]
        mp3 = f"editions/{date}.mp3"
        if manifest.get(date, {}).get("sha") == sha and os.path.exists(mp3):
            continue
        print(f"{date}: recording {len(text.split())} words")
        with tempfile.TemporaryDirectory() as tmp:
            wav = os.path.join(tmp, "brief.wav")
            subprocess.run([sys.executable, "-m", "piper", "--model", VOICE, "--output_file", wav,
                            "--sentence_silence", "0.35"], input=text.encode(), check=True)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-ac", "1", "-codec:a", "libmp3lame",
                            "-b:a", "64k", "-metadata", f"title=Vertical News, {date}", "-metadata", "artist=Vertical News",
                            mp3], check=True)
        manifest[date] = {"file": f"{date}.mp3", "sha": sha, "duration": duration(mp3)}
        changed = True
    if changed:
        with open(MANIFEST, "w") as f:
            json.dump(dict(sorted(manifest.items())), f, indent=2)
            f.write("\n")
    print("done" + (" (manifest updated)" if changed else " (nothing new)"))


if __name__ == "__main__":
    main()
