class CVParseError(Exception):
    """
    Failed to parse a CV from a TSV file
    """

class InvalidRowError(Exception):
    """
    A single row in a spreadsheet could not be parsed
    """

class DimensionsSheetNoRowsError(Exception):
    """
    The Dimensions Sheet has no data rows. This is acceptable
    so we defined this exception to safely catch this error and
    ignore.
    """
    
class GlobalAttributesSheetNoRowsError(Exception):
    """
    The Specific Global Attributes Sheet has no data rows.
    This is acceptable so we defined this exception to safely
    catch this error and ignore.
    """

