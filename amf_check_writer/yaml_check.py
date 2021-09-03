from __future__ import print_function
import sys
import re
from operator import attrgetter
from collections import OrderedDict

import yaml

from amf_check_writer.exceptions import InvalidRowError
from amf_check_writer.base_file import AmfFile
from amf_check_writer.cvs.base import StripWhitespaceReader


class CustomDumper(yaml.SafeDumper):
    # Inserts blank lines between top-level objects: inspired by https://stackoverflow.com/a/44284819/3786245"
    # Preserve the mapping key order. See https://stackoverflow.com/a/52621703/1497385"

    def write_line_break(self, data=None):
        super().write_line_break(data)
        if len(self.indents) in (1,2):
            super().write_line_break()

    def represent_dict_preserve_order(self, data):
        return self.represent_dict(data.items())

CustomDumper.add_representer(OrderedDict, CustomDumper.represent_dict_preserve_order)


class YamlCheck(AmfFile):
    """
    A YAML file that can be used with cc-yaml to run a suite of checks
    """
    def to_yaml_check(self, version):
        """
        Use `get_yaml_checks` to write a YAML check suite for use with cc-yaml
        :return: the YAML document as a string
        """
        d = OrderedDict()

        d["suite_name"] = f"{self.namespace}_checks:{version}"
        d["description"] = "Check '{}' in AMF files".format(" ".join(self.facets))
        d["checks"] = list(self.get_yaml_checks())

        return yaml.dump(d, Dumper=CustomDumper)

    def get_yaml_checks(self):
        """
        Return an iterable of check dictionaries for use with cc-yaml check
        suite. Must be implemented in child classes.
        """
        raise NotImplementedError


class WrapperYamlCheck(YamlCheck):
    """
    Wrapper check that just includes checks from other files
    """
    def __init__(self, child_checks, *args, **kwargs):
        self.child_checks = child_checks
        super(WrapperYamlCheck, self).__init__(*args, **kwargs)

    def get_yaml_checks(self):
        for check in sorted(self.child_checks, key=attrgetter("namespace")):
            yield {"__INCLUDE__": check.get_filename("yml")}


class FileInfoCheck(YamlCheck):
    """
    Checks for general properties of files. Note that this is entirely static
    and does not depend on any data from the spreadsheets
    """
    def get_yaml_checks(self):
        check_package = "checklib.register.file_checks_register"

        size_checks = [
            ("soft", 2, "LOW"),
            ("hard", 4, "HIGH")
        ]
        for strictness, limit, level in size_checks:
            yield {
                "check_id": "check_{}_file_size_limit".format(strictness),
                "check_name": "{}.FileSizeCheck".format(check_package),
                "check_level": level,
                "parameters": {"strictness": strictness, "threshold": limit}
            }

        yield {
            "check_id": "check_filename_structure",
            "check_name": "{}.FileNameStructureCheck".format(check_package),
            "check_level": "HIGH",
            "parameters": {"delimiter": "_", "extension": ".nc"}
        }


class FileStructureCheck(YamlCheck):
    """
    Check a dataset is a valid NetCDF4 file. Note that this is entirely static
    and does not depend on any data from the spreadsheets
    """
    def get_yaml_checks(self):
        yield {
            "check_id": "check_valid_netcdf4_file",
            "check_name": "checklib.register.nc_file_checks_register.NetCDFFormatCheck",
            "parameters": {"format": "NETCDF4_CLASSIC"}
        }


class GlobalAttrCheck(YamlCheck):
    """
    Check that value of global attributes match given regular expressions
    """
    def __init__(self, tsv_file, facets):
        """
        Parse TSV file and construct regexes
        :param tsv_file: file object for the input TSV file
        :param facets:   filename facets
        """
        super(GlobalAttrCheck, self).__init__(facets)
        reader = StripWhitespaceReader(tsv_file, delimiter="\t")

        self.regexes = OrderedDict()

        ns = self.namespace
        cv = {ns: OrderedDict()}
        for row in reader:
            name_id = row["Name"]
            if name_id in cv[ns]:
                print(f"[WARNING] Duplicate global attribute '{name_id}'",
                      file=sys.stderr)
                continue

            cv[ns][name_id] = {
                "global_attribute_id": name_id,
                "description": row["Description"],
                "fixed_value": row["Fixed Value"],
                "compliance_checking_rules": row["Compliance checking rules"],
                "convention_providence": row["Convention Providence"]
            }

            try:
                attr, regex = GlobalAttrCheck.parse_row(row)
                self.regexes[attr] = regex
            except InvalidRowError:
                print(f"[WARNING]: Invalid row in spreadsheet/TSV ({tsv_file.name}): {row}",
                      file=sys.stderr)
            except ValueError as ex:
                print(f"[WARNING]: Cannot parse row in spreadsheet/TSV ({tsv_file.name}): "
                      f"{row} : Exception: {ex}", file=sys.stderr)

        self.cv_dict = cv

    def get_yaml_checks(self):
        check_name = "checklib.register.nc_file_checks_register.GlobalAttrRegexCheck"
        for attr, regex in self.regexes.items():
            yield {
                "check_id": f"check_{attr}_global_attribute",
                "check_name": check_name,
                "parameters": {"attribute": attr, "regex": regex}
            }

    @classmethod
    def parse_row(cls, row):
        """
        Parse a row of the spreadsheet to get the attribute name and a regex to
        check the attribute value

        :param row: Row from spreadsheet as a dict indexed by column name
        :return:    A tuple (attr, regex) where regex is a python regex as a
                    string

        :raises ValueError:      if compliance checking rule is not recognised
        :raises InvalidRowError: if the row could not be parsed
        """
        try:
            attr = row["Name"]
            rule = row["Compliance checking rules"]
            assert attr and rule
        except (KeyError, AssertionError):
            raise InvalidRowError()

        # Regexes for exact matches in the rule column
        _NOT_APPLICABLE_RULES = "(N/A)|(NA)|(N A)|(n/a)|(na)|(n a)|" \
                 "(Not Applicable)|(Not applicable)|(Not available)|(Not Available)|" \
                 "(not applicable)|(not available)"

        static_rules = {
            "Integer": r"-?\d+",
            "Valid email": r"[^@\s]+@[^@\s]+\.[^\s@]+",
            "Valid URL": r"https?://[^\s]+\.[^\s]*[^\s\.](/[^\s]+)?",
            "Valid URL _or_ N/A": r"(https?://[^\s]+\.[^\s]*[^\s\.](/[^\s]+))|" + _NOT_APPLICABLE_RULES,
            "Match: vN.M": r"v\d\.\d",
            "Match: YYYY-MM-DDThh:mm:ss\.\d+": "\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?",
            "Match: YYYY-MM-DDThh:mm:ss\.\d+ _or_ N/A": 
                 "(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?)|" + _NOT_APPLICABLE_RULES,
            "Exact match: <number> m": r"-?\d+(\.\d+)? m"
        }
        # Regexes based on a regex in the rule column
        regex_rules = {
            r"String: min (?P<count>\d+) characters?":
                lambda m: r".{" + str(m.group("count")) + r",}",
            r"One of:\s+(?P<choices>.+)":
                lambda m: r"(" + "|".join([i.strip() for i in m.group("choices").split(",")]) + r")"
        }

        regex = None
        try:
            regex = static_rules[rule]
        except KeyError:
            for rule_regex, func in regex_rules.items():

                match = re.match(rule_regex, rule)

                if match:
                    regex = func(match)
                    break

        if regex is None:
            # Handle 'exact match' case where need to look at other columns
            fixed_val_col = "Fixed Value"
            if (fixed_val_col in row
                and rule.lower() in ("exact match", "exact match of text to the left")):

                regex = re.escape(row["Fixed Value"])
            else:
                raise ValueError(
                    "Unrecognised global attribute check rule: {}".format(rule)
                )

        return attr, regex
