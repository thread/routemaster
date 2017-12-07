"""Human-readable ParseError handling."""

def _find_line_containing(source, index):
    """Find (line number, line, offset) triple for an index into a string."""
    lines = source.splitlines()
    this_line_start = 0
    for zero_index_line_number, line in enumerate(lines):
        next_line_start = this_line_start + len(line)
        if next_line_start > index:
            return zero_index_line_number + 1, line, index - this_line_start
        this_line_start = next_line_start

    # Must be at the end of file
    return len(lines), lines[-1], len(lines[-1])


def format_parse_error_message(*, source, error):
    error_line_number, error_line, error_offset = _find_line_containing(
        source,
        error.location[0],
    )

    error_length = error.location[1] - error.location[0]

    error_character = "~" if error_length > 1 else "^"

    message_lines = [
        f"Error on line {error_line}: {error.message}",
        error_line,
        " " * error_offset + error_character * error_length,
    ]

    return "\n".join(message_lines)
