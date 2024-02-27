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
from amf_check_writer.workflow_docs import read_workflow_data
from amf_check_writer.pyessv_writer import PyessvWriter
from amf_check_writer.exceptions import CVParseError, DimensionsSheetNoRowsError


# Load information about which spreadsheets/worksheets are expected
workflow_data = {k: v for k,v in read_workflow_data().items()}


class DeploymentModes(Enum):
    """
    Enumeration of valid deployment modes
    """
    LAND = "land"
    SEA = "sea"
    AIR = "air"
    TRAJECTORY = "trajectory"


SPREADSHEET_NAMES = {
    "common_spreadsheet": "_common",
    "vocabs_spreadsheet": "_vocabularies",
    "platform_vocabs_spreadsheet": "_platform_vocabs",
    "instrument_vocabs_spreadsheet": "_instrument_vocabs",
    "global_attrs_worksheet": "global-attributes.tsv",
    "platform_worksheet": "platforms.tsv",
    "ncas_instruments_worksheet": "ncas-instrument-name-and-descriptors.tsv",
    "community_instruments_worksheet": "community-instrument-name-and-descriptors.tsv",
    "data_products_worksheet": "data-products.tsv",
    "platforms_worksheet": "platforms.tsv",
    "scientists_worksheet": "creators.tsv"
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

    def __init__(self, version_dir, version_or_vocab):
        self.path = version_dir
        self.version_or_vocab = version_or_vocab

    def write_cvs(self, output_dir, write_pyessv=True, pyessv_root=None):
        """
        Write CVs as JSON files
        :param output_dir:   directory in which to write output JSON files
        :param write_pyessv: boolean indicating whether to write CVs to pyessv archive
        :param pyessv_root:  directory to use as pyessv archive
        """
        cvs = list(self.get_all_cvs())
        #if "/vocabs/" in output_dir:
        #    version_number = "vocabs"
        #else:
        if self.version_or_vocab == "version":
            version_number = self._find_version_number(output_dir)
        else:
            version_number = "vocabs"
        self._write_output_files(cvs, BaseCV.to_json, output_dir, "json", version_number)
        
        # Check that correct CVs were written
        json_files = {cv.get_filename("json") for cv in cvs}

        cv_wf_data = workflow_data["json-cvs"]
        expected_common_files = {json for json in cv_wf_data["common"]}
        per_product_templates = cv_wf_data["per-product"]
        optional_product_files = set()

        for product_name in self.product_names:
            for tmpl in per_product_templates:

                json_file = tmpl.format(product=product_name)
                if "*" not in json_file:
                    expected_common_files.add(json_file)
                else:
                    optional_product_files.add(json_file.replace("*", ""))

        if not expected_common_files.issubset(json_files):
            diff = expected_common_files.difference(json_files)
            if not version_number == "vocabs":
                if float(version_number[1:]) <= 2.0 or not diff == set(('AMF_ncas_instrument.json', 'AMF_community_instrument.json')):
                    raise ValueError(f"[ERROR] The following expected JSON controlled "
                                 f"vocabulary JSON files were not created: {diff}.")

        product_ga_and_dim_files = {json for json in json_files 
            if json.startswith("AMF_product_") and "common" not in json and
               ("dimension" in json or "global-attributes" in json)}

        if not product_ga_and_dim_files.issubset(optional_product_files):
            diff = product_ga_and_dim_files.difference(optional_product_files)
            raise ValueError(f"[ERROR] The following expected JSON controlled "
                             f"vocabulary JSON files were not created: {diff}.")
        
        # Write as PYESSV format if required
        if write_pyessv:
            writer = PyessvWriter(pyessv_root=pyessv_root)
            writer.write_cvs(cvs)

            # Check the pyessv files were written correctly
            if len(writer._written) != len(cvs):
                diff = set(writer._written).difference({cv.get_identifier() for cv in cvs})
                raise ValueError(f"[ERROR] The following expected PYESSV controlled "
                                 f"vocabulary JSON files were not created: {diff}.")

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
            self.path, 'product-definitions/tsv', SPREADSHEET_NAMES["common_spreadsheet"],
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
        version_number = self._find_version_number(output_dir)

        # Create a top-level YAML check for each product/deployment-mode
        # combination
        product_names = set()

        for prod_name, prod_cvs in product_cvs.items():
            product_names.add(prod_name)

            for mode in DeploymentModes:
                dep_m = mode.value.lower()
                facets = ["product", prod_name, dep_m]
                child_checks = global_checks + prod_cvs + common_cvs.get(dep_m, [])
                all_checks.append(WrapperYamlCheck(child_checks, facets))

        # Check that the required checks were created
        all_check_files = {check.get_filename("yml") for check in all_checks}

        yaml_checks_wf_data = workflow_data["yaml_checks"]
        expected_product_checks = {check for check in yaml_checks_wf_data["common"]}
        optional_product_checks = set()

        product_check_templates = [tmpl for tmpl in yaml_checks_wf_data["per-product"]
                                   if "*" not in tmpl]
        optional_check_templates = [tmpl for tmpl in yaml_checks_wf_data["per-product"]
                                    if "*" in tmpl]

        for product_name in product_names:
            for tmpl in product_check_templates:
                expected_product_checks.add(tmpl.format(product=product_name))         

            for tmpl in optional_check_templates:
                optional_product_checks.add(tmpl.format(product=product_name).replace("*", "")) 

        if not all_check_files.issubset(expected_product_checks):
            diff = all_check_files.difference(expected_product_checks)

            if not diff.issubset(optional_product_checks): 
                raise ValueError(f"[ERROR] The following expected checks were not created: "
                                 f"{diff}.")

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
   
            print(f"[INFO] Wrote: {outpath}")

        print(f"[INFO] {count} files written")

    def get_all_cvs(self, base_class=None):
        """
        Parse CV objects from the spreadsheet files

        :param base_class: if given, only parse CVs that inherit from this
                           class
        :return:           an iterator of instances of subclasses of `BaseCV`
        """
        # Static CVs
        def static_path(name, vocabs=None):
            if vocabs:
                return os.path.join('product-definitions/tsv', SPREADSHEET_NAMES[vocabs], SPREADSHEET_NAMES[name])
            else:
                return os.path.join('product-definitions/tsv', SPREADSHEET_NAMES["vocabs_spreadsheet"],
                                    SPREADSHEET_NAMES[name])
        
        if self.version_or_vocab == "version":
            cv_parse_infos = [
                CVParseInfo(
                    path=static_path("ncas_instruments_worksheet"),
                    cls=InstrumentsCV,
                    facets=["ncas_instrument"]
                ),
                CVParseInfo(
                    path=static_path("community_instruments_worksheet"),
                    cls=InstrumentsCV,
                    facets=["community_instrument"]
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
                print(f"[WARNING] No product variable/dimension spreadsheets found in {self.path}",
                    file=sys.stderr
                )

        elif self.version_or_vocab == "instruments":
            cv_parse_infos = [
                CVParseInfo(
                    path=static_path("ncas_instruments_worksheet", vocabs="instrument_vocabs_spreadsheet"),
                    cls=InstrumentsCV,
                    facets=["ncas_instrument"]
                ),
                CVParseInfo(
                    path=static_path("community_instruments_worksheet", vocabs="instrument_vocabs_spreadsheet"),
                    cls=InstrumentsCV,
                    facets=["community_instrument"]
                ),
            ]
            self.product_names = []

        elif self.version_or_vocab == "platforms":
            cv_parse_infos = [
                CVParseInfo(
                    path=static_path("platform_worksheet", vocabs="platform_vocabs_spreadsheet"),
                    cls=PlatformsCV,
                    facets=["platform"]
                ),
            ]
            self.product_names = []
        
        else:
            raise ValueError(f"Vocab {self.version_or_vocab} doesn't exist (how did we get here?)")


        for count, (path, cls, facets) in enumerate(cv_parse_infos):
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
                    print(f"[WARNING] Failed to parse '{full_path}': {ex}",
                          file=sys.stderr)

        print(f'[INFO] Read input from {count} TSV files')

    def _get_per_product_parse_info(self):
        """
        Return iterator of CVParseInfo objects for product variable/dimension
        CVs
        """
        # Record products in an instance variable (for use during integrity-checking)
        self.product_names = set()

        sheet_regex = re.compile(
            r"/tsv/(?P<name>[a-zA-Z0-9-]+)/(?P<type>variables|dimensions|global-attributes)-specific\.tsv$"
        )
        ignore_match = re.compile(r"/(_common|_vocabularies|_instrument_vocabs)/")

        prods_dir = os.path.join(self.path, 'product-definitions/tsv')

        for dirpath, _dirnames, filenames in os.walk(prods_dir):
            for fname in filenames:

                path = os.path.join(dirpath, fname)
                match = sheet_regex.search(path)

                if ignore_match.search(path):
                    # Ignore silently if not products
                    continue
                elif not match:
                    print("[WARNING] No match for '{}'".format(path))
                    continue

                print('[INFO] Working on: {}'.format(path))
                prod_name = match.group("name")
                self.product_names.add(prod_name)

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
        common_dir = os.path.join('product-definitions/tsv', SPREADSHEET_NAMES["common_spreadsheet"])

        for prefix, obj in self.VAR_DIM_FILENAME_MAPPING.items():

            for mode in DeploymentModes:
                dep_m = mode.value
                if prefix == 'global-attributes':
                    filename = f"{prefix}.tsv"
                    print("NOTE: Global attributes are the same for all deployment modes.")
                else:
                    filename = f"{prefix}-{dep_m}.tsv"

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
            print(f"[WARNING] Expected to find file at '{path}'", file=sys.stderr)

        return isfile

    def _find_version_number(self, s):

        """
        Finds the version number from the tsv_file path from a path/string.

        Return: version number (string)
        """
        version_regex = re.compile(r"\/v\d+\.\d+")
        match_ver = version_regex.search(s)
        match = match_ver.group()
        return match[1:]
