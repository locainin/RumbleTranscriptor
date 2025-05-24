# main.py
import os
import yt_dlp
import whisper

def download_video(url, output_dir):
    ydl_opts = {
        'format': 'best',
        'outtmpl': os.path.join(output_dir, 'video.%(ext)s'),
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    for ext in ['mp4', 'webm', 'mkv']:
        path = os.path.join(output_dir, f"video.{ext}")
        if os.path.exists(path):
            return path
    raise FileNotFoundError("Video not found after download.")

def transcribe(video_path, model_name='medium', lang='English', formats=None):
    if not formats:
        formats = ["txt"]
    model = whisper.load_model(model_name)
    result = model.transcribe(video_path, language=lang, verbose=True)
    segments = result.get('segments', [])

    base = os.path.splitext(video_path)[0]
    outputs = []

    if "txt" in formats:
        txt_path = base + ".txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(result["text"].strip() + "\n")
        outputs.append(txt_path)
    if "srt" in formats:
        srt_path = base + ".srt"
        write_srt(segments, srt_path)
        outputs.append(srt_path)
    if "vtt" in formats:
        vtt_path = base + ".vtt"
        write_vtt(segments, vtt_path)
        outputs.append(vtt_path)
    if "tsv" in formats:
        tsv_path = base + ".tsv"
        write_tsv(segments, tsv_path)
        outputs.append(tsv_path)
    if "json" in formats:
        import json
        json_path = base + ".json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        outputs.append(json_path)

    return outputs

def format_timestamp(seconds, always_include_hours=False, decimal_marker=','):
    milliseconds = round(seconds * 1000.0)
    hours = milliseconds // 3_600_000
    minutes = (milliseconds % 3_600_000) // 60_000
    seconds = (milliseconds % 60_000) // 1000
    milliseconds = milliseconds % 1000

    hours_marker = f"{hours:02d}:" if always_include_hours or hours > 0 else ""
    return f"{hours_marker}{minutes:02d}:{seconds:02d}{decimal_marker}{milliseconds:03d}"

def write_srt(segments, out_path):
    with open(out_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            f.write(f"{i}\n")
            start = format_timestamp(seg['start'], always_include_hours=True, decimal_marker=',')
            end = format_timestamp(seg['end'], always_include_hours=True, decimal_marker=',')
            f.write(f"{start} --> {end}\n")
            f.write(seg['text'].strip() + "\n\n")

def write_vtt(segments, out_path):
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for seg in segments:
            start = format_timestamp(seg['start'], always_include_hours=True, decimal_marker='.')
            end = format_timestamp(seg['end'], always_include_hours=True, decimal_marker='.')
            f.write(f"{start} --> {end}\n")
            f.write(seg['text'].strip() + "\n\n")

def write_tsv(segments, out_path):
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("start\tend\ttext\n")
        for seg in segments:
            f.write(f"{seg['start']}\t{seg['end']}\t{seg['text'].strip()}\n")

def run_gui():
    from gui import run_gui
    run_gui()

if __name__ == "__main__":
    run_gui()
