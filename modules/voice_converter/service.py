import subprocess


def convert_to_voice(input_path: str, output_path: str) -> None:
    """
    Creates a new file with `opus` format using `libopus` plugin. The new file can be recognized as a voice message by
    Telegram.

    :param input_path: str: The path of the input file
    :param output_path: str: The output path of the converted file
    """
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", input_path,
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
            output_path,
        ],
        check=True,
    )
