from __future__ import print_function
import sys
from collections import OrderedDict

from amf_check_writer.cvs.base import BaseCV


class GlobalAttributesCV(BaseCV):
    def parse_tsv(self, reader):
        ns = self.namespace
        cv = {ns: OrderedDict()}
        for row in reader:
            name_id = row["Name"]
            if name_id in cv[ns]:
                print("WARNING: Duplicate global attribute '{}'".format(name_id),
                      file=sys.stderr)
                continue

            cv[ns][name_id] = {
                "global_attribute_id": name_id,
                "description": row["Description"],
                "fixed_value": row["Fixed Value"],
                "compliance_checking_rules": row["Compliance checking rules"],
                "convention_providence": row["Convention Providence"]
            }
        return cv
