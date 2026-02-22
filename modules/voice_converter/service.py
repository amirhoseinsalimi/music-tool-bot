import subprocess
from pathlib import Path


def convert_to_voice(input_path: str, output_path: str) -> None:
    """
    Creates a new file with `opus` format using `libopus` plugin. The new file can be recognized as a voice message by
    Telegram.

    :param input_path: str: The path of the input file
    :param output_path: str: The output path of the converted file
    """
    in_path = Path(input_path)
    out_path = Path(output_path)

    if not in_path.exists():
        raise FileNotFoundError(f"Input file not found: {in_path}")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-i",
        str(in_path),

        "-map", "0:a:0",
        "-vn",
        "-sn",
        "-dn",

        "-map_metadata", "-1",

        "-ac", "1",
        "-c:a", "libopus",
        "-b:a", "32k",
        "-vbr", "on",
        "-compression_level", "10",
        "-frame_duration", "60",
        "-application", "voip",

        str(out_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(
            "ffmpeg failed.\n"
            f"Command: {' '.join(cmd)}\n\n"
            f"STDERR:\n{result.stderr}"
        )
