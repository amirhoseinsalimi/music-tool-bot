import re


def parse_cutting_range(text: str) -> (int, int):
    text = re.sub(' ', '', text)
    beginning, _, ending = text.partition('-')

    if '-' not in text:
        raise ValueError('Malformed music range')

    if ':' in text:
        beginning_sec = int(beginning.partition(':')[0].lstrip('0') if
                            beginning.partition(':')[0].lstrip('0') else 0) * 60 \
                        + int(beginning.partition(':')[2].lstrip('0') if
                              beginning.partition(':')[2].lstrip('0') else 0)

        ending_sec = int(ending.partition(':')[0].lstrip('0') if
                         ending.partition(':')[0].lstrip('0') else 0) * 60 \
                     + int(ending.partition(':')[2].lstrip('0') if
                           ending.partition(':')[2].lstrip('0') else 0)
    else:
        beginning_sec = int(beginning)
        ending_sec = int(ending)

    return beginning_sec, ending_sec