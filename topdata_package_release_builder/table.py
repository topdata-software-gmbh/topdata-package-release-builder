"""Table generation module for formatted text output."""

def create_table(data, style="default"):
    """Create a minimal ASCII table with box-drawing characters.

    Args:
        data: List of [key, value] pairs to display
        style: Table style - "default" (with dividers) or "simple" (without dividers)

    Returns:
        str: Formatted table string
    """
    # Find the maximum width for each column
    col_widths = [max(len(str(row[i])) for row in data) for i in range(2)]

    # Create the table string
    lines = []

    if style == "default":
        # Top border
        lines.append(f"┌{'─' * (col_widths[0] + 2)}┬{'─' * (col_widths[1] + 2)}┐")

        # Data rows
        for key, value in data:
            lines.append(f"│ {key:<{col_widths[0]}} │ {value:<{col_widths[1]}} │")

        # Bottom border
        lines.append(f"└{'─' * (col_widths[0] + 2)}┴{'─' * (col_widths[1] + 2)}┘")
    else:  # simple style without vertical dividers
        # Top border
        lines.append(f"┌{'─' * (col_widths[0] + col_widths[1] + 4)}┐")

        # Data rows
        for key, value in data:
            lines.append(f"│ {key:<{col_widths[0]}}  {value:<{col_widths[1]}} │")

        # Bottom border
        lines.append(f"└{'─' * (col_widths[0] + col_widths[1] + 4)}┘")

    return '\n'.join(lines)
