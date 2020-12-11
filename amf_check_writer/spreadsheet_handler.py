from __future__ import print_function
import os
import sys
import re
from collections import namedtuple

from enum import Enum

from amf_check_writer.cvs import (BaseCV, VariablesCV, ProductsCV, PlatformsCV,
                                  InstrumentsCV, DimensionsCV, ScientistsCV)
from amf_check_writer.yaml_check import (YamlCheck, WrapperYamlCheck,
                                         FileInfoCheck, FileStructureCheck,
                                         GlobalAttrCheck)
from amf_check_writer.pyessv_writer import PyessvWriter
from amf_check_writer.exceptions import CVParseError, DimensionsSheetNoRowsError


class DeploymentModes(Enum):
    """
    Enumeration of valid deployment modes
    """
    LAND = "land"
    SEA = "sea"
    AIR = "air"


SPREADSHEET_NAMES = {
#    "products_dir": "product-definitions",
    "common_spreadsheet": "_common",
    "vocabs_spreadsheet": "_vocabularies",
    "global_attrs_worksheet": "global-attributes.tsv",
    "ncas_instruments_worksheet": "ncas-instrument-name-and-descriptors",
    "community_instruments_worksheet": "community-instrument-name-and-descriptors",
    "data_products_worksheet": "data-products",
    "platforms_worksheet": "platforms",
    "scientists_worksheet": "creators"
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
        "variables": {"name": "variable", "cls": VariablesCV},
        "dimensions": {"name": "dimension", "cls": DimensionsCV},
        "global-attributes": {"name": "global-attributes", "cls": GlobalAttrCheck}
    }

    def __init__(self, spreadsheets_dir):
        self.path = spreadsheets_dir

    def write_cvs(self, output_dir, write_pyessv=False, pyessv_root=None):
        """
        Write CVs as JSON files
        :param output_dir:   directory in which to write output JSON files
        :param write_pyessv: boolean indicating whether to write CVs to pyessv
                             archive
        :param pyessv_root:  directory to use as pyessv archive
        """
        cvs = list(self.get_all_cvs())
        self._write_output_files(cvs, BaseCV.to_json, output_dir, "json")
        if write_pyessv:
            writer = PyessvWriter(pyessv_root=pyessv_root)
            writer.write_cvs(cvs)

    def write_yaml(self, output_dir):
        """
        Write YAML checks for each appropriate CV
        :param output_dir: directory in which to write output YAML files
        """
        # Find CVs that are also YAML checks
        cvs = list(self.get_all_cvs(base_class=YamlCheck))
        all_checks = []
        all_checks += cvs

        # Add global checks
        global_checks = [
            FileInfoCheck(["file_info"]),
            FileStructureCheck(["file_structure"]),
        ]
        global_attrs_path = os.path.join(
            self.path, 'tsv', SPREADSHEET_NAMES["common_spreadsheet"],
            SPREADSHEET_NAMES["global_attrs_worksheet"]
        )
        if self._isfile(global_attrs_path):
            with open(global_attrs_path) as tsv_file:
                global_checks.append(GlobalAttrCheck(tsv_file, ["global_attrs"]))

        all_checks += global_checks

        # Group product CVs by name, and common product CVs by deployment mode
        product_cvs = {}
        common_cvs = {}
        for cv in cvs:
            if len(cv.facets) > 2 and cv.facets[0] == "product":
                prod_name = cv.facets[1]
                if prod_name == "common":
                    dep_m = cv.facets[-1]
                    if dep_m not in common_cvs:
                        common_cvs[dep_m] = []
                    common_cvs[dep_m].append(cv)
                else:
                    if prod_name not in product_cvs:
                        product_cvs[prod_name] = []
                    product_cvs[prod_name].append(cv)

        # Find version number of the checks by looking for regex in output_dir
        version_regex = re.compile(r"v\d\.\d")
        match_ver = version_regex.search(tsv_file.name)
        version_number = match_ver.group()[1:]

        # Create a top-level YAML check for each product/deployment-mode
        # combination
        for prod_name, prod_cvs in product_cvs.items():
            for mode in DeploymentModes:
                dep_m = mode.value.lower()
                facets = ["product", prod_name, dep_m]
                child_checks = global_checks + prod_cvs + common_cvs.get(dep_m, [])
                all_checks.append(WrapperYamlCheck(child_checks, facets))

        self._write_output_files(all_checks, YamlCheck.to_yaml_check,
                                 output_dir, "yml", version_number)

    def _write_output_files(self, files, callback, output_dir, ext, version):
        """
        Helper method to call a method on a several AmfFile objects and write
        the output to a file
        :param files:      iterable of AmfFile objects
        :param callback:   method to call for each object. It is passed the
                           object as its single argument and should return a
                           string
        :param output_dir: directory in which to write output files
        :param ext:        file extension to use
        """
        count = 0

        for f in files:

            fname = f.get_filename(ext)
            outpath = os.path.join(output_dir, fname)

            with open(outpath, "w") as out_file:
                out_file.write(callback(f,version))
                count += 1
   
            print('[INFO] Wrote: {}'.format(outpath))

        print("[INFO] {} files written".format(count))

    def get_all_cvs(self, base_class=None):
        """
        Parse CV objects from the spreadsheet files

        :param base_class: if given, only parse CVs that inherit from this
                           class
        :return:           an iterator of instances of subclasses of `BaseCV`
        """
        # Static CVs
        def static_path(name):
            return os.path.join('tsv',SPREADSHEET_NAMES["vocabs_spreadsheet"],
                                SPREADSHEET_NAMES[name])
        cv_parse_infos = [
            CVParseInfo(
                path=static_path("ncas_instruments_worksheet"),
                cls=InstrumentsCV,
                facets=["instrument"]
            ),
            CVParseInfo(
                path=static_path("community_instruments_worksheet"),
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
                "[WARNING] No product variable/dimension spreadsheets found in {}"
                .format(self.path),
                file=sys.stderr
            )

        for path, cls, facets in cv_parse_infos:
            if base_class and base_class not in cls.__bases__:
                continue

            full_path = os.path.join(self.path, path)
            if not self._isfile(full_path):
                continue

            print('[INFO] Extracting content from: {}'.format(full_path))

            with open(full_path) as tsv_file:
                try:
                    yield cls(tsv_file, facets)
                except DimensionsSheetNoRowsError as ex:
                    # Ignore if there is no data in the Dimensions worksheet
                    pass
                except CVParseError as ex:
                    print("WARNING: Failed to parse '{}': {}"
                          .format(full_path, ex), file=sys.stderr)

    def _get_per_product_parse_info(self):
        """
        Return iterator of CVParseInfo objects for product variable/dimension
        CVs
        """
        sheet_regex = re.compile(
            r"/tsv/(?P<name>[a-zA-Z0-9-]+)/(?P<type>variables|dimensions|global-attributes)-specific\.tsv$"
#            r"(?P<name>[a-zA-Z0-9-]+)/(?P=name)\.xlsx/(?P<type>Variables|Dimensions) - Specific.tsv$"
        )
        ignore_match = re.compile(r"/(_common|_vocabularies)/")

        prods_dir = os.path.join(self.path, 'tsv')
#        prods_dir = os.path.join(self.path, SPREADSHEET_NAMES["products_dir"], 'tsv')

        for dirpath, _dirnames, filenames in os.walk(prods_dir):
            for fname in filenames:

                path = os.path.join(dirpath, fname)
                match = sheet_regex.search(path)

                if ignore_match.search(path):
                    # Ignore silently if not products
                    continue
                elif not match:
                    print("WARNING: No match for '{}'".format(path))
                    continue

                print('[INFO] Working on: {}'.format(path))
                prod_name = match.group("name")
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
        common_dir = os.path.join(self.path, 'tsv', SPREADSHEET_NAMES["common_spreadsheet"])

        for prefix, obj in self.VAR_DIM_FILENAME_MAPPING.items():

            for mode in DeploymentModes:
                dep_m = mode.value
                filename = "{type}-{dep_m}.tsv".format(type=prefix, dep_m=dep_m)

                yield CVParseInfo(
                    path=os.path.join(common_dir, filename),
                    cls=obj["cls"],
                    facets=["product", "common", obj["name"], dep_m.lower()]
                )

    def _isfile(self, path):
        """
        Wrapper around os.path.isfile that prints a warning message if path is
        not a file
        :param path: filepath to check
        :return:     boolean (True is path is a file)
        """
        isfile = os.path.isfile(path)
        if not isfile:
            print("WARNING: Expected to find file at '{}'".format(path),
                  file=sys.stderr)
        return isfile
