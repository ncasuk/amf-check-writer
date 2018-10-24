from collections import OrderedDict

from amf_check_writer.cvs.base import BaseCV
from amf_check_writer.yaml_check import YamlCheck
from amf_check_writer.exceptions import CVParseError, DimensionsSheetNoRowsError


class DimensionsCV(BaseCV, YamlCheck):
    """
    Controlled vocabulary for specifying which dimensions should be present in
    NetCDF files, and a YAML check for verifying this in actual files.
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
            raise DimensionsSheetNoRowsError("No dimensions found for this product. "
                                             "We can safely IGNORE this.")
        return cv

    def get_yaml_checks(self):
        check_package = "checklib.register.nc_file_checks_register"
        vocab_ref = "ncas:amf"

        for dim_name, data in self.cv_dict[self.namespace].items():
            yield {
                "check_id": "check_{}_dimension_attrs".format(dim_name),
                "check_name": "{}.NetCDFDimensionCheck".format(check_package),
                "parameters": {
                    "dim_id": dim_name,
                    "vocabulary_ref": vocab_ref,
                    "pyessv_namespace": self.namespace,
                    "ignore_coord_var_check": ("index" in dim_name)
                },
                "comments": ("Checks the dimension attributes for '{}'"
                             .format(dim_name))
            }
