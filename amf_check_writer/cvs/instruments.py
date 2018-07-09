from __future__ import print_function
import sys
from collections import OrderedDict

from amf_check_writer.cvs.base import BaseCV


class InstrumentsCV(BaseCV):
    def parse_tsv(self, reader):
        ns = self.namespace
        cv = {ns: OrderedDict()}
        for row in reader:
            instr_id = row["New Instrument Name"]
            if instr_id in cv[ns]:
                print("WARNING: Duplicate instrument name '{}'".format(instr_id),
                      file=sys.stderr)
                continue

            prev_ids = filter(None, map(str.strip,
                                        row["Old Instrument Name"].split(",")))
            cv[ns][instr_id] = {
                "instrument_id": instr_id,
                "previous_instrument_ids": list(prev_ids),
                "description": row["Descriptor"]
            }
        return cv
