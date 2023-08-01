import re


def parse_bitrate_number(input_string: str) -> int | None:
    pattern = r'^\d+'

    matches = re.findall(pattern, input_string)

    if matches:
        return int(matches[0])
    else:
        return None
