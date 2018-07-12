from __future__ import print_function
import sys
import re
from operator import attrgetter
from collections import OrderedDict

import yaml

from amf_check_writer.base_file import AmfFile
from amf_check_writer.cvs.base import StripWhitespaceReader


class YamlCheck(AmfFile):
    """
    A YAML file that can be used with cc-yaml to run a suite of checks
    """
    def to_yaml_check(self):
        """
        Use `get_yaml_checks` to write a YAML check suite for use with cc-yaml
        :return: the YAML document as a string
        """
        return yaml.dump({
            "suite_name": "{}_checks".format(self.namespace),
            "checks": list(self.get_yaml_checks())
        })

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
        for row in reader:
            try:
                attr = row["Name"]
                rule = row["Compliance checking rules"]
                assert attr and rule
            except (KeyError, AssertionError):
                continue

            try:
                regex = GlobalAttrCheck.spreadsheet_value_to_regex(rule)
                self.regexes[attr] = regex
            except ValueError as ex:
                print("WARNING: {}".format(ex), file=sys.stderr)

    def get_yaml_checks(self):
        check_name = "checklib.register.nc_file_checks_register.GlobalAttrRegexCheck"
        for attr, regex in self.regexes.items():
            yield {
                "check_id": "check_{}_global_attribute",
                "check_name": check_name,
                "parameters": {"attribute": attr, "regex": regex}
            }

    @classmethod
    def spreadsheet_value_to_regex(cls, value):
        """
        Create a regex from the 'Compliance checking rules' column of the
        spreadsheet

        :param value: String from spreadsheet describing a compliance check rule
        :return:      A python regex as a string
        """
        spreadsheet_regex_mapping = {
            "Integer": r"-?\d+",
            "Valid email": r"[^@\s]+@[^@\s]+\.[^\s@]+",
            "Match: vN.M": r"v\d\.\d",
            "Match: YYYY-MM-DDThh:mm:ss.*": "\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.*",
        }

        # Try to find value in above dict
        for rule, regex in spreadsheet_regex_mapping.items():
            if value == rule:
                attr_regex = regex
                break
        else:
            # Handle n character string rule separately -- build regex from
            # a match against spreadsheet value
            match = re.match(r"String: min (?P<count>\d+) characters", value)
            if match:
                n = match.group("count")
                # Use the form a{n,} to match n or more 'a's
                attr_regex = r".{" + str(n) + r",}"
            else:
                raise ValueError("Unrecognised global attribute check rule: {}".format(value))

        return "^{}$".format(attr_regex)
