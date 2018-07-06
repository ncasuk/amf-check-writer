"""
Classes for handling generation of CVs
"""
from __future__ import print_function
import os
import sys
import re
import json
from collections import OrderedDict
from csv import DictReader

import yaml


class BaseCvHandler:
    """
    Base class for operations involving controlled vocabularies.
    Subclass this class for each CV type and define the properties and methods
    below
    """
    # String that is prefixed to TSV filenames for this type of CV
    tsv_filename_prefix = None

    # Name to use for this CV type in namespace
    cv_type_name = None

    def __init__(self, tsv_file, product_name, category):
        """
        :param tsv_file:     file object for input TSV file
        :param product_name: the product the TSV file corresponds to
                             (e.g. 'mean winds')
        :param category:     category within the CV type (e.g. 'Air', 'Land',
                             'Sea' or 'Specific')
        """
        self.tsv_file = tsv_file
        self.product_name = product_name

        # namespace for this CV needs to be unique across all products, so
        # include product name, category name (if not the default 'specific')
        # and CV type name
        ns = "product_{prod}_{type}".format(prod=self.product_name,
                                            type=self.cv_type_name)
        category = category.lower()
        if category != "specific":
            ns += "_" + category
        self.namespace = ns

        reader = DictReader(self.tsv_file, delimiter="\t")
        self.cv = self.tsv_to_json(reader)

    def write_json_cv(self, outdir):
        """
        Use `tsv_to_json` to write JSON CV to a file

        :param outdir: directory in which to create the CV file
        """
        fname = "AMF_{}.json".format(self.namespace)
        outpath = os.path.join(outdir, fname)
        print("Writing {}".format(outpath))
        with open(outpath, "w") as json_file:
            json.dump(self.cv, json_file, indent=4)

    def write_yaml_checks(self, outdir):
        """
        Use `get_yaml_checks` to write a YAML check suite for use with
        cc-yaml

        :param outdir: directory in which to create the YAML file
        """
        yml = {
            "suite_name": "{}_checks".format(self.namespace),
            "checks": list(self.get_yaml_checks(self.cv))
        }
        outpath = os.path.join(outdir, "amf_{}.yml".format(self.namespace))
        print("Writing {}".format(outpath))
        with open(outpath, "w") as yml_file:
            yaml.dump(yml, yml_file)

    def tsv_to_json(self, reader):
        """
        Convert the TSV file to a dictionary in the controlled vocab format.
        Must be implemented in child classes.

        :param reader: csv.DictReader instance for the TSV file
        :return:       dict containing data in JSON controlled vocab format
        """
        raise NotImplementedError

    def get_yaml_checks(self, json_cv):
        """
        Return an iterable of check dictionaries for use with cc-yaml check
        suite. Must be implemented in child classes.

        :param json_cv: controlled vocab dictionary
        :return:        iterable of check dictionaries
        """
        raise NotImplementedError


class VariableHandler(BaseCvHandler):
    tsv_filename_prefix = "Variables"
    cv_type_name = "variable"

    # Attributes whose value should be interpreted as a float instead of string
    numeric_types = ("valid_min", "valid_max")

    def tsv_to_json(self, reader):
        ns = self.namespace
        cv = {ns: OrderedDict()}
        for row in reader:
            if row["Variable"]:
                # Variable names containing ??? cause problems with pyessv,
                # and are probably not correct anyway
                if row["Variable"].endswith("???"):
                    raise ValueError("Invalid variable name '{}'"
                                     .format(row["Variable"]))

                current_var = row["Variable"]
                cv[ns][current_var] = OrderedDict()

            elif row["Attribute"] and row["Value"]:
                attr = row["Attribute"]
                # Some of the sheets have extraneous whitespace...
                value = row["Value"].strip()
                if attr in self.numeric_types and not value.startswith("<"):
                    value = float(value)
                cv[ns][current_var][attr] = value
        return cv

    def get_yaml_checks(self, cv):
        check_package = "checklib.register.nc_file_checks_register"
        vocab_ref = "ncas:amf"

        for var_name, data in cv[self.namespace].items():
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
                print("Error in product {}, file '{}': Missing value {}"
                      .format(self.product_name,
                              os.path.basename(self.tsv_file.name), ex),
                      file=sys.stderr)


class DimensionHandler(BaseCvHandler):
    tsv_filename_prefix = "Dimensions"
    cv_type_name = "dimension"

    def tsv_to_json(self, reader):
        ns = self.namespace
        cv = {ns: OrderedDict()}
        for row in reader:
            if row["Name"] and row["Length"] and row["units"]:
                name, length, units = (row[x].strip()
                                       for x in ("Name", "Length", "units"))
                cv[ns][name] = {
                    "length": length,
                    "units": units
                }
        if not cv[ns]:
            raise ValueError("No dimensions found")
        return cv


class BatchTsvProcessor:
    """
    Scan a directory and create JSON CVs from TSV files
    """
    @classmethod
    def write_cvs(cls, indir, outdir):
        cls.process(indir, outdir, "write_json_cv")

    @classmethod
    def write_yaml(cls, indir, outdir):
        cls.process(indir, outdir, "write_yaml_checks")

    @classmethod
    def process(cls, indir, outdir, method_name):
        handler_mapping = {cls.tsv_filename_prefix: cls
                           for cls in (VariableHandler, DimensionHandler)}

        # Build a regex to figure out with generator class to use for a given
        # file
        prefixes = "|".join(handler_mapping.keys())
        regex = re.compile(
            r"(?P<prefix>{prefixes}) - (?P<category>[a-zA-Z]*).tsv"
            .format(prefixes=prefixes)
        )

        count = 0
        for dirpath, dirnames, filenames in os.walk(indir):
            for fname in filenames:
                match = regex.match(fname)
                if not match:
                    continue

                category = match.group("category")
                # Product name is the name of the spreadsheet, which is the
                # parent directory of the tsv file
                product_name = (os.path.split(dirpath)[-1].lower()
                                .replace("-", "_"))
                if product_name.endswith(".xlsx"):
                    product_name = product_name[:-5]

                handler_cls = handler_mapping[match.group("prefix")]
                with open(os.path.join(dirpath, fname)) as tsv_file:
                    try:
                        handler = handler_cls(tsv_file, product_name, category)
                    except ValueError as ex:
                        err = ("Error in product {prod}, file '{file}': {err}"
                               .format(prod=product_name, file=fname, err=ex))
                        print(err, file=sys.stderr)
                        continue

                    method = getattr(handler, method_name)
                    try:
                        method(outdir)
                    except NotImplementedError:
                        continue
                    count += 1

        print("{} files written".format(count))
