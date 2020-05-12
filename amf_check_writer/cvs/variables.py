from __future__ import print_function
import sys
from collections import OrderedDict

from amf_check_writer.cvs.base import BaseCV
from amf_check_writer.yaml_check import YamlCheck
from amf_check_writer.exceptions import CVParseError


class VariablesCV(BaseCV, YamlCheck):
    """
    Controlled vocabulary for specifying which variables should be present in
    NetCDF files, and a YAML check for verifying this against actual files.
    """
    # Attributes whose value should be interpreted as a float instead of string
    NUMERIC_TYPES = ("valid_min", "valid_max", "_FillValue")
    TO_IGNORE = ("name",)

    def parse_tsv(self, reader):
        ns = self.namespace
        cv = {ns: OrderedDict()}

        for row in reader:

            if row["Variable"]:
                # Variable names containing ??? cause problems with pyessv,
                # and are probably not correct anyway
                if "?" in row["Variable"]:
                    raise CVParseError("Invalid variable name '{}'"
                                       .format(row["Variable"]))

                current_var = row["Variable"]
                cv[ns][current_var] = OrderedDict()

            elif row["Attribute"] in self.TO_IGNORE:
                continue

            elif row["Attribute"] and row["Value"]:
                attr = row["Attribute"]
                value = row["Value"]
                if attr in self.NUMERIC_TYPES and not value.startswith("<"):
                    value = float(value)
                cv[ns][current_var][attr] = value
        return cv

    def get_yaml_checks(self):
        check_package = "checklib.register.nc_file_checks_register"
        vocab_ref = "ncas:amf"

        for var_name, data in self.cv_dict[self.namespace].items():
            # Variable attributes check
            yield {
                "check_id": "check_{}_variable_attrs".format(var_name),
                "check_name": ("{}.NCVariableMetadataCheck"
                               .format(check_package)),
                "parameters": {
                    "var_id": var_name,
                    "vocabulary_ref": vocab_ref,
                    "pyessv_namespace": self.namespace
                },
                "comments": ("Checks the variable attributes for '{}'"
                             .format(var_name))
            }

            # Variable type check
            try:
                yield {
                    "check_id": "check_{}_variable_type".format(var_name),
                    "check_name": "{}.VariableTypeCheck".format(check_package),
                    "parameters": {
                        "vocabulary_ref": vocab_ref,
                        "var_id": var_name,
                        "dtype": data["type"]
                    },
                    "comments": ("Checks the type of variable '{}'"
                                 .format(var_name))
                }
            except KeyError as ex:
                print("WARNING: Missing value {} in '{}"
                      .format(ex, self.tsv_file.name),
                      file=sys.stderr)
