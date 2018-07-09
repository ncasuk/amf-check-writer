from __future__ import print_function
import sys
from collections import OrderedDict

from amf_check_writer.cvs.base import BaseCV


class PlatformsCV(BaseCV):
    def parse_tsv(self, reader):
        ns = self.namespace
        cv = {ns: OrderedDict()}
        for row in reader:
            platform_id = row["Platform ID"]
            if platform_id in cv[ns]:
                print("WARNING: Duplicate platform ID '{}'".format(platform_id),
                      file=sys.stderr)
                continue

            cv[ns][platform_id] = {
                "platform_id": platform_id,
                "description": row["Platform Description"]
            }
        return cv
