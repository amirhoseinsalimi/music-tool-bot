from pathlib import Path

from utils.logging import run_ffmpeg


def convert_m4a_to_mp3(input_path: str, output_path: str) -> None:
    in_path = Path(input_path)
    out_path = Path(output_path)

    if not in_path.exists():
        raise FileNotFoundError(f"Input file not found: {in_path}")

    if in_path.suffix.lower() != ".m4a":
        raise ValueError(f"Input file must be an .m4a file: {in_path}")

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-i", str(in_path),

        "-map", "0:a:0",
        "-map", "0:v?",

        "-map_metadata", "0",

        "-c:a", "libmp3lame",
        "-q:a", "2",

        "-c:v", "copy",
        "-disposition:v:0", "attached_pic",

        "-id3v2_version", "3",

        str(out_path),
    ]

    run_ffmpeg(cmd, "convert m4a to mp3")
