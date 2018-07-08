from collections import OrderedDict

from amf_check_writer.cvs.base import BaseCV
from amf_check_writer.exceptions import CVParseError


class DimensionsCV(BaseCV):
    """
    Controlled vocabulary for specifying which dimensions should be present in
    NetCDF files
    """
    def parse_tsv(self, reader):
        ns = self.namespace
        cv = {ns: OrderedDict()}
        for row in reader:
            if row["Name"] and row["Length"] and row["units"]:
                cv[ns][row["Name"]] = {
                    "length": row["Length"],
                    "units": row["units"]
                }
        if not cv[ns]:
            raise CVParseError("No dimensions found")
        return cv
