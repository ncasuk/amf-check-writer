from collections import OrderedDict

from amf_check_writer.cvs.base import BaseCV


class InstrumentsCV(BaseCV):
    def parse_tsv(self, reader):
        ns = self.namespace
        cv = {ns: OrderedDict()}
        for row in reader:
            new_instr_name = row["New Instrument Name"]
            prev_ids = filter(None, map(str.strip,
                                        row["Old Instrument Name"].split(",")))
            cv[ns][new_instr_name] = {
                "instrument_id": new_instr_name,
                "previous_instrument_ids": list(prev_ids),
                "description": row["Descriptor"]
            }
        return cv
