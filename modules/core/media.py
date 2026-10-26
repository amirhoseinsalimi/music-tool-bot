"""Inspect media streams so output filenames match their actual containers."""
import json
import subprocess


_FORMAT_EXTENSIONS = {
    'mp3': '.mp3',
    'mov': '.m4a',
    'mp4': '.m4a',
    'm4a': '.m4a',
    'aac': '.aac',
    'adts': '.aac',
    'ogg': '.ogg',
    'flac': '.flac',
    'wav': '.wav',
}


def probe_audio_format(file_path: str) -> tuple[str, str]:
    """Return (real extension, audio codec) for the first audio stream."""
    try:
        result = subprocess.run(
            [
                'ffprobe', '-v', 'error', '-select_streams', 'a:0',
                '-show_entries', 'stream=codec_name:format=format_name',
                '-of', 'json', file_path,
            ],
            capture_output=True,
            check=True,
            text=True,
        )
        data = json.loads(result.stdout)
        stream = data['streams'][0]
        format_names = data['format']['format_name'].split(',')
        extension = next((_FORMAT_EXTENSIONS[name] for name in format_names if name in _FORMAT_EXTENSIONS), None)
        if extension is None:
            raise ValueError('Unsupported audio container')
        return extension, stream['codec_name']
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError, KeyError, IndexError) as error:
        raise ValueError('Unable to identify the audio container') from error
