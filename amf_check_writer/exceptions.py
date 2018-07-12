class CVParseError(Exception):
    """
    Failed to parse a CV from a TSV file
    """

class InvalidRowError(Exception):
    """
    A single row in a spreadsheet could not be parsed
    """
