"""Disclosed local synthetic narration, exact measured chapter durations and subtitles."""
from pathlib import Path
import hashlib
import json
import math
import subprocess
import re
import wave

R = Path(__file__).resolve().parents[1]
O = R / "06_RIG_AND_MEDIA/narration"
O.mkdir(parents=True, exist_ok=True)
source = json.loads((R / "04_PAPER/RIG_VIDEO_STORYBOARD.json").read_text())
chapters = source["chapters"]
# Final audience copy replaces editorial directions without changing scientific claims.
chapters[1]["narration"] = chapters[1]["narration"].replace("The diagram should show both the forward command path and the returning evidence path with their timestamps.", "Timestamps connect the forward command path with the returning evidence path, so discrepancies can be compared over the same interval.")
chapters[3]["narration"] = chapters[3]["narration"].replace("The animation should identify these components without adding a vendor name or an unmeasured performance number.", "The named components show how the proposed drive works, while part selection and measured performance remain for the team to establish.")
chapters[3]["key_points"][0] = "Motor, coupling and lead screw"
chapters[12]["narration"] = "The software study asks whether a more complex monitor improves on a simpler one with the same response authority. Established physiological models provide the experimental setting; they are not new inventions of GECO. Hold the available inputs, tuning opportunities, disturbances and follow-up rules constant. Read excess together with deficit, interruption and recovery. Report failures and uncertainty as well as average effects. The rig diagram explains this experimental logic. It does not predict that the full method will outperform its comparators."
chapters[12]["key_points"] = ["Equal authority and comparable inputs", "Established models, explicit lineage", "Compare complete outcomes"]
chapters[12]["measured_quantity"] = "Matched excess, deficit, interruption and recovery in simulation"
chapters[12]["evidence_status"] = "SIMULATION_METHODS_EXPLANATION"
chapters[7]["visual_focus"] = "temperature"
voice = "Aman"
rate = 155
fps = 24
audio_records, subtitles = [], []
elapsed = 0.0
combined = O / "GECOv6_Rig_Narration.wav"
def timestamp(value):
    n = round(value * 1000)
    return f"{n//3600000:02d}:{n//60000%60:02d}:{n//1000%60:02d},{n%1000:03d}"
with wave.open(str(combined), "wb") as total:
    total.setnchannels(1);total.setsampwidth(2);total.setframerate(48000)
    for chapter in chapters:
        ident = chapter["chapter_id"]
        text_file = O / f"{ident}.txt"
        text_file.write_text(chapter["narration"] + "\n")
        ai = O / f"{ident}.aiff"
        wav = O / f"{ident}.wav"
        subprocess.run(["/usr/bin/say", "-v", voice, "-r", str(rate), "-o", str(ai), "-f", str(text_file)], check=True)
        subprocess.run(["/opt/homebrew/bin/ffmpeg", "-v", "error", "-y", "-i", str(ai), "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(wav)], check=True)
        with wave.open(str(wav), "rb") as audio:
            samples = audio.getnframes()
            spoken_duration = samples / 48000
            duration = math.ceil((spoken_duration + 0.65) * fps) / fps
            pcm = audio.readframes(samples)
        padded_samples = round(duration * 48000)
        total.writeframes(pcm + bytes((padded_samples - samples) * 2))
        chapter.update(id=ident, start_seconds=elapsed, duration=duration, spoken_duration=spoken_duration)
        # Cues follow sentence boundaries with proportional timing, not claimed forced alignment.
        sentences = re.split(r"(?<=[.!?])\s+", chapter["narration"].strip())
        weights = [len(re.findall(r"\S+", x)) for x in sentences]
        pos = elapsed
        for sentence, weight in zip(sentences, weights):
            end = pos + spoken_duration * weight / sum(weights)
            subtitles.append((pos, end, sentence));pos = end
        audio_records.append(dict(chapter=ident, voice=voice, rate_wpm=rate, spoken_seconds=spoken_duration, padded_seconds=duration, text_sha256=hashlib.sha256(text_file.read_bytes()).hexdigest(), audio_sha256=hashlib.sha256(wav.read_bytes()).hexdigest()))
        elapsed += duration
        print(ident, round(duration, 3), flush=True)
        ai.unlink()
(R / "06_RIG_AND_MEDIA/Interactive_Rig/chapters.json").write_text(json.dumps(chapters, indent=2))
(O / "GECOv6_Rig_Explained.srt").write_text("\n\n".join(f"{i}\n{timestamp(start)} --> {timestamp(end)}\n{sentence}" for i, (start, end, sentence) in enumerate(subtitles, 1)) + "\n")
(O / "FINAL_TRANSCRIPT.md").write_text("# GECOv6 rig explained\n\nSynthetic narration: macOS Aman, nominal 155 words/minute. The voice is not a recording of a team member. All physical measurements remain pending.\n\n" + "\n\n".join(f"## {c['id']} {c['title']}\n\n{c['narration']}" for c in chapters) + "\n")
(O / "NARRATION_RECEIPT.json").write_text(json.dumps(dict(voice_source="macOS local speech synthesis",voice=voice,nominal_words_per_minute=rate,provenance="Disclosed synthetic speech; no human voice impersonation",frames_per_second=fps,duration_seconds=elapsed,chapters=audio_records,subtitle_timing="Sentence-weighted approximate cues; audio duration is measured",narration_sha256=hashlib.sha256(combined.read_bytes()).hexdigest(),watermark_claim="No watermark or authorship-detector certification performed"), indent=2))
print("Total", elapsed, flush=True)
