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
                print(f"[WARNING] Duplicate instrument name '{insr_id}'", file=sys.stderr)
                continue

            prev_ids = row["Old Instrument Name"] or []
            if prev_ids:
                prev_ids = [iname.strip() for iname in prev_ids.split(",")]

            cv[ns][instr_id] = {
                "instrument_id": instr_id,
                "previous_instrument_ids": prev_ids,
                "description": row["Descriptor"]
            }
        return cv
