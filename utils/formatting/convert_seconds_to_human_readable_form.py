def convert_seconds_to_human_readable_form(seconds: int) -> str:
    """Convert seconds to human-readable time format, e.g. 02:30

    **Keyword arguments:**
     - seconds (int) -- Seconds to convert

    **Returns:**
     Formatted string
    """
    if seconds <= 0:
        return "00:00"

    minutes = int(seconds / 60)
    remainder = seconds % 60

    minutes_formatted = str(minutes) if minutes >= 10 else "0" + str(minutes)
    seconds_formatted = str(remainder) if remainder >= 10 else "0" + str(remainder)

    return f"{minutes_formatted}:{seconds_formatted}"