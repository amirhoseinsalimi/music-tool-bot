from pathlib import Path

from modules.core.media import probe_audio_format
from utils.logging import run_ffmpeg


def cut(input_path: str, beginning_sec: int, duration: int, output_path: str) -> None:
    """
    Cuts a segment while preserving metadata and album art when possible.

    - Copies MP3 audio; converts other supported codecs to MP3.
    - Copies any attached picture streams (album art).
    - Copies container/global metadata.

    Note: Stream copy + cutting can be inaccurate for some formats unless the cut starts on keyframes.
    For MP3/AAC this is usually fine but not always sample-exact.

    :param input_path: str: The path of the input file
    :param beginning_sec: int: The starting point of the cut
    :param duration: int: Duration of the cut
    :param output_path: str: The path of the output file
    """
    in_path = Path(input_path)
    out_path = Path(output_path)

    if not in_path.exists():
        raise FileNotFoundError(f"Input file not found: {in_path}")

    if beginning_sec < 0:
        raise ValueError("beginning_sec must be >= 0")

    if duration <= 0:
        raise ValueError("duration must be > 0")

    _extension, audio_codec = probe_audio_format(str(in_path))
    copy_audio = audio_codec == 'mp3'

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-ss", str(beginning_sec),
        "-t", str(duration),
        "-i", str(in_path),
        "-map", "0:a:0",
        "-map", "0:v?",
        "-map_metadata", "0",
    ]

    if copy_audio:
        cmd.extend(["-c", "copy"])
    else:
        cmd.extend(["-c:a", "libmp3lame", "-q:a", "0", "-c:v", "copy"])
    cmd.extend(["-disposition:v:0", "attached_pic", str(out_path)])

    run_ffmpeg(cmd, "cut audio")
