def pretty_print_size(number_of_bytes: float) -> str:
    """Pretty print file sizes


    **Keyword arguments:**
     - number_of_bytes (float) -- Number of bytes to convert

    **Returns:**
     A human-readable file size
    """
    units = [
        (1 << 50, ' PB'),
        (1 << 40, ' TB'),
        (1 << 30, ' GB'),
        (1 << 20, ' MB'),
        (1 << 10, ' KB'),
        (1, (' byte', ' bytes')),
    ]

    for factor, suffix in units:
        if number_of_bytes >= factor:
            break

    amount = int(number_of_bytes / factor)

    if isinstance(suffix, tuple):
        singular, multiple = suffix

        if amount == 1:
            suffix = singular
        else:
            suffix = multiple

    return str(amount) + suffix
