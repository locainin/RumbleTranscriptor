# main.py
import os
import yt_dlp
import whisper
import json
import tempfile
import subprocess

def download_video(url, output_dir, download_format_details):
    os.makedirs(output_dir, exist_ok=True)
    
    # Base output filename (without extension)
    base_output_filename = os.path.join(output_dir, 'downloaded_media')
    # Expected output extension from the format details
    expected_ext = download_format_details.get("output_ext", "mp3")
    final_output_path = f"{base_output_filename}.{expected_ext}"

    # Clean up any pre-existing file with the same base name and *any* common extension
    # to prevent yt-dlp from creating numbered files like downloaded_media (1).mp3
    for old_ext_to_check in ['mp3', 'm4a', 'mp4', 'mkv', 'webm', 'ogg', 'wav']:
        potential_old_file = f"{base_output_filename}.{old_ext_to_check}"
        if os.path.exists(potential_old_file):
            try:
                os.remove(potential_old_file)
                print(f"Removed existing file: {potential_old_file}")
            except OSError as e:
                print(f"Warning: Could not remove existing file {potential_old_file}: {e}")


    ydl_opts = {
        'outtmpl': f'{base_output_filename}.%(ext)s', # yt-dlp determines extension, then we check/rename if needed
        'verbose': False,
        'ignoreerrors': False,
        'quiet': True,
    }

    format_id = download_format_details.get("format_id")

    if format_id == "mp3_best" or format_id == "m4a_best":
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': download_format_details["preferredcodec"],
            'preferredquality': '192',
        }]
    elif format_id == "mp4_best_video":
        # For MP4, we want yt-dlp to try and get an MP4 container directly if possible.
        # This format string prioritizes mp4 video + m4a audio, then best mp4, then best overall.
        # The audio track will be used by Whisper.
        ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo[ext=mp4]/best[ext=mp4]/best'
        # It's generally better to let yt-dlp handle muxing to mp4 if it chooses a separate video/audio.
        # No specific audio extraction postprocessor needed if we want the video file.
    elif format_id == "mkv_best_video":
        ydl_opts['format'] = 'bestvideo+bestaudio/best' # Best video and audio, often results in MKV
        # No specific audio extraction needed for MKV.
    else: # Default or unknown, fallback to best audio MP3
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
        final_output_path = f"{base_output_filename}.mp3" # Adjust expected path for default

    print(f"yt-dlp options: {ydl_opts}")
    print(f"Expecting final output at: {final_output_path}")

    downloaded_file_actual_path = None
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info_dict = ydl.extract_info(url, download=True)
            # yt-dlp might save with a different extension than `expected_ext` initially based on `%(ext)s`
            # before post-processing. The post-processor (for audio) should rename/create the final preferredcodec file.
            
            # Check if the specifically expected file (e.g., .mp3 from postprocessor) exists
            if os.path.exists(final_output_path):
                downloaded_file_actual_path = final_output_path
            else:
                # If postprocessing was involved (like for mp3/m4a), yt-dlp replaces the original %(ext)s
                # If not, the original %(ext)s is used.
                # Let's find what yt-dlp actually created with 'downloaded_media' base.
                temp_filename = ydl.prepare_filename(info_dict).replace(info_dict['ext'], expected_ext) if info_dict else None
                if temp_filename and os.path.exists(temp_filename) :
                     downloaded_file_actual_path = temp_filename
                else: # Scan directory for the file if specific name not found
                    for f_name in os.listdir(output_dir):
                        if f_name.startswith('downloaded_media.'):
                            downloaded_file_actual_path = os.path.join(output_dir, f_name)
                            # If multiple matches, prefer one with the target extension
                            if f_name.endswith(f".{expected_ext}"):
                                break 
                    print(f"Scan found: {downloaded_file_actual_path}")


        except Exception as e:
            raise RuntimeError(f"yt-dlp download or processing failed: {e}")

    if not downloaded_file_actual_path or not os.path.exists(downloaded_file_actual_path):
        raise FileNotFoundError(f"Downloaded media file not found. Expected near {final_output_path}, found {downloaded_file_actual_path if downloaded_file_actual_path else 'nothing'}.")
    
    # Ensure the file to be returned has the correct expected extension if renaming is implicitly handled by yt-dlp
    # For audio, the postprocessor usually handles this. For video, outtmpl with %(ext)s is usually fine.
    # The key is that `downloaded_file_actual_path` points to the real file.
    print(f"Download successful. Media at: {downloaded_file_actual_path}")
    return downloaded_file_actual_path


def transcribe(audio_path, model_name='medium', lang='English', formats=None,
               verbose_transcription=False, start_time=None, end_time=None):
    if not formats:
        formats = ["txt"]
    
    # This print goes to console. GUI gets updates from WorkerThread.progress
    print(f"Loading Whisper model: '{model_name}' (this may download the model if not present)...")
    try:
        model = whisper.load_model(model_name)
    except Exception as e:
        raise RuntimeError(f"Failed to load Whisper model '{model_name}'. Error: {e}")
    print(f"Model '{model_name}' loaded. Starting transcription for: {audio_path}")

    audio_to_use = audio_path
    temp_segment = None
    if start_time is not None or end_time is not None:
        # extract portion of media using ffmpeg
        start = float(start_time or 0)
        end = float(end_time) if end_time is not None else None
        if end is not None and end <= start:
            raise ValueError("end_time must be greater than start_time")
        suffix = os.path.splitext(audio_path)[1]
        temp_fd, temp_segment = tempfile.mkstemp(suffix=suffix)
        os.close(temp_fd)
        ff_cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            str(start),
            "-i",
            audio_path,
        ]
        if end is not None:
            ff_cmd += ["-t", str(end - start)]
        ff_cmd += ["-c", "copy", temp_segment]
        try:
            subprocess.run(ff_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            audio_to_use = temp_segment
        except subprocess.CalledProcessError as e:
            if temp_segment and os.path.exists(temp_segment):
                os.remove(temp_segment)
            raise RuntimeError(f"Failed to extract media segment: {e}")

    result = model.transcribe(audio_to_use, language=lang, verbose=verbose_transcription)
    segments = result.get('segments', [])
    print("Transcription complete.")

    output_dir = os.path.dirname(audio_path)
    base_filename = os.path.splitext(os.path.basename(audio_path))[0] + "_transcript"
    outputs = []

    if "txt" in formats:
        txt_path = os.path.join(output_dir, base_filename + ".txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(result["text"].strip() + "\n")
        outputs.append(txt_path)
    # ... (rest of the format writing functions remain the same) ...
    if "srt" in formats:
        srt_path = os.path.join(output_dir, base_filename + ".srt")
        write_srt(segments, srt_path)
        outputs.append(srt_path)
    if "vtt" in formats:
        vtt_path = os.path.join(output_dir, base_filename + ".vtt")
        write_vtt(segments, vtt_path)
        outputs.append(vtt_path)
    if "tsv" in formats:
        tsv_path = os.path.join(output_dir, base_filename + ".tsv")
        write_tsv(segments, tsv_path)
        outputs.append(tsv_path)
    if "json" in formats:
        json_path = os.path.join(output_dir, base_filename + ".json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        outputs.append(json_path)
    if temp_segment and os.path.exists(temp_segment):
        os.remove(temp_segment)
    return outputs

def format_timestamp(seconds_float, always_include_hours=False, decimal_marker=','):
    if seconds_float is None: return f"00:00:00{decimal_marker}000"
    try:
        seconds_float = float(seconds_float)
    except (ValueError, TypeError):
        return f"00:00:00{decimal_marker}000"

    milliseconds_total = round(seconds_float * 1000.0)
    hours = milliseconds_total // 3_600_000
    minutes = (milliseconds_total % 3_600_000) // 60_000
    seconds = (milliseconds_total % 60_000) // 1000
    milliseconds = milliseconds_total % 1000

    hours_str = f"{int(hours):02d}:" if always_include_hours or hours > 0 else ""
    return f"{hours_str}{int(minutes):02d}:{int(seconds):02d}{decimal_marker}{int(milliseconds):03d}"

def write_srt(segments, out_path):
    with open(out_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            start_time = seg.get('start', 0.0)
            end_time = seg.get('end', 0.0)
            text = seg.get('text', "").strip()
            f.write(f"{i}\n")
            f.write(f"{format_timestamp(start_time, True, ',')} --> {format_timestamp(end_time, True, ',')}\n")
            f.write(text + "\n\n")

def write_vtt(segments, out_path):
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for seg in segments:
            start_time = seg.get('start', 0.0)
            end_time = seg.get('end', 0.0)
            text = seg.get('text', "").strip()
            f.write(f"{format_timestamp(start_time, False, '.')} --> {format_timestamp(end_time, False, '.')}\n")
            f.write(text + "\n\n")

def write_tsv(segments, out_path):
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("start\tend\ttext\n")
        for seg in segments:
            start_time = seg.get('start', 0.0)
            end_time = seg.get('end', 0.0)
            text = seg.get('text', "").strip().replace('\t', ' ')
            f.write(f"{start_time:.3f}\t{end_time:.3f}\t{text}\n")

def run_main_gui():
    from gui import run_gui_app
    run_gui_app()

if __name__ == "__main__":
    run_main_gui()