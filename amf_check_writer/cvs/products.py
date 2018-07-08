from collections import OrderedDict

from amf_check_writer.cvs.base import BaseCV


class ProductsCV(BaseCV):
    def parse_tsv(self, reader):
        ns = self.namespace
        cv = {ns: []}
        for row in reader:
            cv[ns].append(row["Data Product"])
        return cv
