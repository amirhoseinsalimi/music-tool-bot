from pathlib import Path

from utils.logging import run_ffmpeg


def convert_bitrate(input_path: str, output_bitrate: int, output_path: str) -> None:
    """
    Re-encodes audio to the given bitrate while preserving metadata and album art.

    Notes:
    - This keeps tags (`-map_metadata 0`) and attempts to keep embedded cover art by mapping streams.
    - If the input contains multiple audio streams, this keeps the first audio stream.
    - If output is MP3, album art is stored as an attached picture (ID3 APIC) when supported by ffmpeg.

    :param input_path: Path to input audio file
    :param output_bitrate: Target audio bitrate (kbps)
    :param output_path: Path to output audio file
    """
    in_path = Path(input_path)
    out_path = Path(output_path)

    if not in_path.exists():
        raise FileNotFoundError(f"Input file not found: {in_path}")

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-i",
        str(in_path),

        "-map", "0:a:0",
        "-map", "0:v?",

        "-map_metadata", "0",

        "-c:a", "libmp3lame",
        "-b:a", f"{output_bitrate}k",
        "-ac", "2",
        "-ar", "44100",

        "-c:v", "copy",

        "-disposition:v:0", "attached_pic",

        str(out_path),
    ]

    run_ffmpeg(cmd, "change audio bitrate")
