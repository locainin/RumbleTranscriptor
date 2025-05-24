# Rumble Transcriber:

This project provides a graphical user interface (GUI) to download videos from Rumble.com and generate transcripts using OpenAI's powerful Whisper ASR model. If you've ever wanted an easy way to get text from Rumble videos, much like you might for other platforms such as YouTube, this tool is for you.

It leverages [OpenAI's Whisper](https://github.com/openai/whisper) for accurate speech-to-text conversion and `yt-dlp` for downloading the media.

## Features

* **User-Friendly GUI**: Easily paste a Rumble URL, select options, and get your transcript.
* **Powered by Whisper**: Utilizes OpenAI's state-of-the-art speech recognition.
* **Selectable Models**: Choose from various Whisper model sizes (Tiny, Base, Small, Medium, Large variants, to balance transcription speed with accuracy.(Full Details Of Each Model In the URL Above)
* **Multiple Output Formats**: Get transcripts in TXT, SRT, VTT, TSV, and JSON formats.
* **Configurable Download**:
    * Select download format for media (MP3 Audio, M4A Audio, MP4 Video, MKV Video).
    * Option to automatically delete the downloaded media file after transcription or keep it.
* **Custom Output Location**: Choose where your transcript and media files are saved.
* **Settings Menu**: Persistent settings for download format and media file retention.

## Prerequisites

Before you begin, ensure you have the following installed:

1.  **Python 3.7+**
2.  **FFmpeg**: Whisper and `yt-dlp` require FFmpeg for audio processing.
    * **On Ubuntu or Debian:**
        ```bash
        sudo apt update && sudo apt install ffmpeg
        ```
    * **On Arch Linux:**
        ```bash
        sudo pacman -S ffmpeg
        ```
    * **On macOS using Homebrew ([brew.sh](https://brew.sh/)):**
        ```bash
        brew install ffmpeg
        ```
    * **On Windows using Chocolatey ([chocolatey.org](https://chocolatey.org/)):**
        ```bash
        choco install ffmpeg
        ```
    * **On Windows using Scoop ([scoop.sh](https://scoop.sh/)):**
        ```bash
        scoop install ffmpeg
        ```
3.  **yt-dlp**: While listed in `requirements.txt`, you can also install/update it globally if preferred.

## Installation

1.  **Get the Code**:
    Ensure you have the project files (`gui.py`, `main.py`, `requirements.txt`) in a local directory.
     ```bash
    git clone https://github.com/locainin/RumbleTranscriptor
    cd RumbleTranscriptor
    ```

3.  **Install FFmpeg**:
    Follow the instructions in the "Prerequisites" section for your operating system if you haven't already.

4.  **Install Python Dependencies**:
    Navigate to the project directory in your terminal and install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```
    This will install `PyQt5`, `yt-dlp`, and `openai-whisper` (including its dependencies like PyTorch).
    * **Note on PyTorch**: The Whisper package attempts to install an appropriate version of PyTorch. If you have specific CUDA requirements for GPU acceleration, you might need to install PyTorch manually *before* running the command above, following instructions from the [official PyTorch website](https://pytorch.org/get-started/locally/).

## Usage

1.  **Run the Application**:
    Open your terminal, navigate to the project directory, and run:
    ```bash
    python main.py
    ```
2.  **Enter Rumble URL**:
    Paste the full URL of the Rumble video you want to transcribe into the designated field.
3.  **Select Output Folder**:
    Click "Select Output Folder" to choose where the downloaded media and transcript files will be saved.
4.  **Choose Whisper Model**:
    Select a Whisper model from the dropdown. Smaller models are faster but less accurate; larger models are more accurate but slower and require more resources (RAM/VRAM). The selected model will be downloaded automatically by Whisper on its first use if not already present.
5.  **Select Output Formats**:
    Check the boxes for the desired transcript file formats (e.g., TXT, SRT).
6.  **Configure Settings (Optional)**:
    * Go to `Settings > Configure Application...` from the menu bar.
    * **Keep downloaded file**: Check this box if you want to keep the downloaded media file (MP3, MP4, etc.) after transcription. Uncheck to delete it automatically.
    * **Download Format**: Choose your preferred format for the media download (e.g., "Audio: MP3", "Video: MP4"). The audio from this file will be used for transcription.
    * Click "Save & Close" to apply settings.
7.  **Start Transcription**:
    Click the "Extract & Transcribe" button.
8.  **Monitor Progress**:
    The GUI will display status messages and a progress bar. yt-dlp download progress and Whisper model loading/transcription messages may also appear in the console.
9.  **Access Transcripts**:
    Once complete, your transcript files will be available in the output folder you selected. Downloaded media (if kept) will also be in this folder, typically named `downloaded_media.[ext]`.

## How It Works

* **`yt-dlp`**: Downloads the video/audio content from the provided Rumble URL based on your selected format.
* **OpenAI Whisper**: The downloaded audio is processed by the selected Whisper model to generate the transcript.
* **PyQt5**: Provides the graphical user interface.

---

