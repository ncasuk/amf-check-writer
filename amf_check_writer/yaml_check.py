from __future__ import print_function
import sys
import re
from operator import attrgetter
from collections import OrderedDict

import yaml

from amf_check_writer.exceptions import InvalidRowError
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
            "description": "Check '{}' in AMF files".format(" ".join(self.facets)),
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
                attr, regex = GlobalAttrCheck.parse_row(row)
                self.regexes[attr] = regex
            except InvalidRowError:
                pass
            except ValueError as ex:
                print("WARNING: {}".format(ex), file=sys.stderr)

    def get_yaml_checks(self):
        check_name = "checklib.register.nc_file_checks_register.GlobalAttrRegexCheck"
        for attr, regex in self.regexes.items():
            yield {
                "check_id": "check_{}_global_attribute".format(attr),
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
            "Valid URL|N/A": r"(https?://[^\s]+\.[^\s]*[^\s\.](/[^\s]+))|" + _NOT_APPLICABLE_RULES,
            "Match: vN.M": r"v\d\.\d",
            "Match: YYYY-MM-DDThh:mm:ss\.\d+": "\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?",
            "Match: YYYY-MM-DDThh:mm:ss\.\d+|N/A": 
                 "(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?)|" + _NOT_APPLICABLE_RULES,
            "Exact match: <number> m": r"-?\d+(\.\d+)? m",
        }
        # Regexes based on a regex in the rule column
        regex_rules = {
            r"String: min (?P<count>\d+) characters":
                lambda m: r".{" + str(m.group("count")) + r",}"
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
