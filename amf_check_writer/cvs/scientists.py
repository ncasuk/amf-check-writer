from __future__ import print_function
from collections import OrderedDict

from amf_check_writer.cvs.base import BaseCV


class ScientistsCV(BaseCV):
    def parse_tsv(self, reader):
        ns = self.namespace
        cv = {ns: OrderedDict()}
        for row in reader:
            cv[ns][row["email"]] = {
                "name": row["name"],
                "primary_email": row["email"],
                # Add previous emails for future-proofing purposes
                "previous_emails": [],
                "orcid": row["orcid"] or None
            }
        return cv
