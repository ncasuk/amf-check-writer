from __future__ import print_function
import os
import sys
import re

from amf_check_writer.cvs import (BaseCV, YamlCheckCV, VariablesCV, ProductsCV,
                                  InstrumentsCV, DimensionsCV)
from amf_check_writer.exceptions import CVParseError


SPREADSHEET_NAMES = {
    "products_dir": "Product Definition Spreadsheets",
    "common_spreadsheet": "Common.xlsx",
    "vocabs_spreadsheet": "Vocabularies",
    "instruments_worksheet": "Instrument Name & Descriptors.tsv",
    "data_products_worksheet": "Data Products.tsv"
}


class SpreadsheetHandler(object):
    """
    Manage a collection of AMF spreadsheets from which CV files and YAML checks
    can be generated
    """

    def __init__(self, spreadsheets_dir):
        self.path = spreadsheets_dir

    def write_cvs(self, output_dir):
        """
        Write CVs as JSON files
        :param output_dir: directory in which to write output JSON files
        """
        self.write_output_files(self.get_all_cvs(), BaseCV.to_json, output_dir,
                                "json")

    def write_yaml(self, output_dir):
        """
        Write YAML checks for each appropriate CV
        :param output_dir: directory in which to write output YAML files
        """
        self.write_output_files(self.get_all_cvs(base_class=YamlCheckCV),
                                YamlCheckCV.to_yaml_check, output_dir,
                                "yml")

    def write_output_files(self, cvs, callback, output_dir, ext):
        """
        Helper method to call a method on a several CVs and write the output to
        a file
        :param cvs:        iterable of CV objects
        :param callback:   method to call for each CV. It is passed the CV
                           object as its single argument and should return a
                           string
        :param output_dir: directory in which to write output files
        :param ext:        file extension to use
        """
        count = 0
        for cv in cvs:
            fname = cv.get_filename(ext)
            print("Writing {}".format(fname))
            outpath = os.path.join(output_dir, fname)
            with open(outpath, "w") as out_file:
                out_file.write(callback(cv))
                count += 1
        print("{} files written".format(count))

    def get_all_cvs(self, base_class=None):
        """
        Parse CV objects from the spreadsheet files

        :param base_class: if given, only parse CVs that inherit from this
                           class
        :return:           an iterator of instances of subclasses of `BaseCV`
        """
        # Build a list of (cls, tsv_path, facets) for CVs to parse
        to_parse = []

        # TODO: reduce all the duplication in this method and split into
        # smaller functions

        # Get variable/dimension CVs for products
        products_dir = os.path.join(self.path, SPREADSHEET_NAMES["products_dir"])
        if not os.path.isdir(products_dir):
            raise IOError("Could not find product definition spreadsheets at "
                          "'{}'".format(products_dir))

        product_sheet_regex = re.compile(
            r"(?P<name>[a-zA-Z-]+)/(?P=name)\.xlsx/(?P<type>Variables|Dimensions) - Specific.tsv$"
        )
        var_dim_type_mapping = {
            "Variables": {"name": "variable", "cls": VariablesCV},
            "Dimensions": {"name": "dimension", "cls": DimensionsCV},
        }
        for dirpath, dirnames, filenames in os.walk(products_dir):
            for fname in filenames:
                full_path = os.path.join(dirpath, fname)
                match = product_sheet_regex.search(full_path)
                if match:
                    prod_name = match.group("name").replace("-", "_")
                    cv_type = match.group("type")
                    cls = var_dim_type_mapping[cv_type]["cls"]
                    facets = ["product", prod_name, var_dim_type_mapping[cv_type]["name"]]
                    to_parse.append([cls, full_path, facets])

        # Get common variable/dimension CVs
        common_dir = os.path.join(self.path, SPREADSHEET_NAMES["common_spreadsheet"])
        if not os.path.isdir(common_dir):
            raise IOError("Could not find common variables/dimensions "
                          "spreadsheet at '{}'".format(common_dir))

        common_sheet_regex = re.compile(
            r"(?P<type>Variables|Dimensions) - (?P<deployment_mode>[a-zA-Z]+).tsv"
        )
        for entry in os.listdir(common_dir):
            match = common_sheet_regex.match(entry)
            if match:
                cv_type = match.group("type")
                cls = var_dim_type_mapping[cv_type]["cls"]
                facets = ["product", "common",
                          var_dim_type_mapping[cv_type]["name"],
                          match.group("deployment_mode").lower()]
                to_parse.append([cls, os.path.join(common_dir, entry), facets])

        # Get instruments CV
        vocab_sheets_dir = os.path.join(self.path,
                                        SPREADSHEET_NAMES["vocabs_spreadsheet"])
        if not os.path.isdir(vocab_sheets_dir):
            raise IOError("Could not find Vocabularies spreadsheet at '{}'"
                          .format(vocab_sheets_dir))

        instr_sheet = os.path.join(vocab_sheets_dir,
                                   SPREADSHEET_NAMES["instruments_worksheet"])
        if not os.path.isfile(instr_sheet):
            raise IOError("Could not find instrument descriptors worksheet at "
                          "{}".format(instr_sheet))
        to_parse.append([InstrumentsCV, instr_sheet, ["instrument"]])

        # Get list of data products CV
        products_sheet = os.path.join(vocab_sheets_dir,
                                      SPREADSHEET_NAMES["data_products_worksheet"])
        if not os.path.isfile(products_sheet):
            raise IOError("Could not find data products worksheet at {}"
                          .format(products_sheet))
        to_parse.append([ProductsCV, products_sheet, ["product"]])

        # Go through collected files and actually parse them
        for cls, tsv_path, facets in to_parse:
            if base_class and base_class not in cls.__bases__:
                continue

            with open(tsv_path) as tsv_file:
                try:
                    yield cls(tsv_file, facets)
                except CVParseError as ex:
                    print("WARNING: Failed to parse '{}': {}"
                          .format(full_path, ex), file=sys.stderr)
