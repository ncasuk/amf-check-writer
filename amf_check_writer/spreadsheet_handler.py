from __future__ import print_function
import os
import sys
import re
from collections import namedtuple

from amf_check_writer.cvs import (BaseCV, YamlCheckCV, VariablesCV, ProductsCV,
                                  PlatformsCV, InstrumentsCV, DimensionsCV,
                                  ScientistsCV)
from amf_check_writer.exceptions import CVParseError


SPREADSHEET_NAMES = {
    "products_dir": "Product Definition Spreadsheets",
    "common_spreadsheet": "Common.xlsx",
    "vocabs_spreadsheet": "Vocabularies",
    "instruments_worksheet": "Instrument Name & Descriptors.tsv",
    "data_products_worksheet": "Data Products.tsv",
    "platforms_worksheet": "Platforms.tsv",
    "scientists_worksheet": "Creators.tsv"
}


CVParseInfo = namedtuple("CVParseInfo", ["path", "cls", "facets"])
"""
Tuple containing information required to parse a TSV file
:param path:   path to TSV file, relative to the spreadsheets root directory
:param cls:    CV class to instantiate
:param facets: list of facets for CV namespace
"""


class SpreadsheetHandler(object):
    """
    Manage a collection of AMF spreadsheets from which CV files and YAML checks
    can be generated
    """

    # Mapping from variables/dimensions filename prefix to CV class and name
    # to use in facets
    VAR_DIM_FILENAME_MAPPING = {
        "Variables": {"name": "variable", "cls": VariablesCV},
        "Dimensions": {"name": "dimension", "cls": DimensionsCV},
    }

    def __init__(self, spreadsheets_dir):
        self.path = spreadsheets_dir

    def write_cvs(self, output_dir):
        """
        Write CVs as JSON files
        :param output_dir: directory in which to write output JSON files
        """
        self._write_output_files(self.get_all_cvs(), BaseCV.to_json, output_dir,
                                 "json")

    def write_yaml(self, output_dir):
        """
        Write YAML checks for each appropriate CV
        :param output_dir: directory in which to write output YAML files
        """
        self._write_output_files(self.get_all_cvs(base_class=YamlCheckCV),
                                 YamlCheckCV.to_yaml_check, output_dir,
                                 "yml")

    def _write_output_files(self, cvs, callback, output_dir, ext):
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
        # Static CVs
        def static_path(name):
            return os.path.join(SPREADSHEET_NAMES["vocabs_spreadsheet"],
                                SPREADSHEET_NAMES[name])
        cv_parse_infos = [
            CVParseInfo(
                path=static_path("instruments_worksheet"),
                cls=InstrumentsCV,
                facets=["instrument"]
            ),
            CVParseInfo(
                path=static_path("data_products_worksheet"),
                cls=ProductsCV,
                facets=["product"]
            ),
            CVParseInfo(
                path=static_path("platforms_worksheet"),
                cls=PlatformsCV,
                facets=["platform"]
            ),
            CVParseInfo(
                path=static_path("scientists_worksheet"),
                cls=ScientistsCV,
                facets=["scientist"]
            )
        ]
        cv_parse_infos += self._get_common_var_dim_parse_info()
        per_product_cvs = list(self._get_per_product_parse_info())
        cv_parse_infos += per_product_cvs
        if not per_product_cvs:
            print(
                "WARNING: No product variable/dimension spreadsheets found in {}"
                .format(os.path.join(self.path, SPREADSHEET_NAMES["products_dir"])),
                file=sys.stderr
            )

        for path, cls, facets in cv_parse_infos:
            if base_class and base_class not in cls.__bases__:
                continue

            full_path = os.path.join(self.path, path)
            if not os.path.isfile(full_path):
                print("WARNING: Expected to find file at '{}'".format(full_path),
                      file=sys.stderr)
                continue

            with open(full_path) as tsv_file:
                try:
                    yield cls(tsv_file, facets)
                except CVParseError as ex:
                    print("WARNING: Failed to parse '{}': {}"
                          .format(full_path, ex), file=sys.stderr)

    def _get_per_product_parse_info(self):
        """
        Return iterator of CVParseInfo objects for product variable/dimension
        CVs
        """
        sheet_regex = re.compile(
            r"(?P<name>[a-zA-Z-]+)/(?P=name)\.xlsx/(?P<type>Variables|Dimensions) - Specific.tsv$"
        )
        prods_dir = os.path.join(self.path, SPREADSHEET_NAMES["products_dir"])
        for dirpath, _dirnames, filenames in os.walk(prods_dir):
            for fname in filenames:
                path = os.path.join(dirpath, fname)
                match = sheet_regex.search(path)
                if not match:
                    continue

                prod_name = match.group("name").replace("-", "_")
                cv_type = match.group("type")
                cls = self.VAR_DIM_FILENAME_MAPPING[cv_type]["cls"]
                facets = ["product", prod_name,
                          self.VAR_DIM_FILENAME_MAPPING[cv_type]["name"]]
                yield CVParseInfo(os.path.relpath(path, start=self.path), cls,
                                  facets)

    def _get_common_var_dim_parse_info(self):
        """
        Return iterator of CVParseInfo objects for common variable/dimension
        CVs
        """
        common_dir = os.path.join(self.path, SPREADSHEET_NAMES["common_spreadsheet"])
        deployment_modes = ["Land", "Sea", "Air"]

        for prefix, obj in self.VAR_DIM_FILENAME_MAPPING.items():
            for dep_m in deployment_modes:
                filename = "{type} - {dep_m}.tsv".format(type=prefix, dep_m=dep_m)
                yield CVParseInfo(
                    path=os.path.join(common_dir, filename),
                    cls=obj["cls"],
                    facets=["product", "common", obj["name"], dep_m.lower()]
                )
