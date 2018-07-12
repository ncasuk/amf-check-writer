"""
Tests to add:
- CVParseError raised when dimensions sheet is empty, invalid var name
"""
import os
import re
import sys
import json
import yaml
from StringIO import StringIO

import pytest

from amf_check_writer.spreadsheet_handler import SpreadsheetHandler
from amf_check_writer.exceptions import CVParseError
from amf_check_writer.cvs import VariablesCV
from amf_check_writer.yaml_check import GlobalAttrCheck


class BaseTest(object):
    @pytest.fixture
    def spreadsheets_dir(self, tmpdir):
        s = tmpdir.mkdir("spreadsheets")
        s.mkdir("Common.xlsx")
        s.mkdir("Product Definition Spreadsheets")
        vars_sheet = s.mkdir("Vocabularies")
        return s


class TestVariablesAndDimensionsGeneration(BaseTest):
    def get_var_inner_cv(self, s_dir, tsv):
        """
        Create a TSV from the given list of lists of columns, and process it
        as a variable TSV file. Return the inner dictionary of the generated
        JSON CV
        """
        prod_dir = (s_dir.join("Product Definition Spreadsheets")
                         .mkdir("wind-speed").mkdir("wind-speed.xlsx"))
        var_sheet = prod_dir.join("Variables - Specific.tsv")
        var_sheet.write(
            "\n".join(("\t".join(x for x in row)) for row in tsv)
        )
        output = s_dir.mkdir("../output")
        sh = SpreadsheetHandler(str(s_dir))
        sh.write_cvs(str(output))

        cv_file = output.join("AMF_product_wind_speed_variable.json")
        assert cv_file.check()
        obj = json.load(cv_file)
        assert "product_wind_speed_variable" in obj
        return obj["product_wind_speed_variable"]

    def test_basic(self, spreadsheets_dir, tmpdir):
        # variables
        s_dir = spreadsheets_dir
        prod = s_dir.join("Product Definition Spreadsheets")
        var = (prod.mkdir("my-great-product").mkdir("my-great-product.xlsx")
                   .join("Variables - Specific.tsv"))
        var.write("\n".join((
            "Variable\tAttribute\tValue",
            "wind_speed\t\t",
            "\tname\twind_speed",
            "\ttype\tfloat32",
            "eastward_wind\t\t",
            "\tname\teastward_wind",
            "\tunits\tm s-1"
        )))

        # dimensions
        prod2 = s_dir.mkdir("other-cool-product")
        dim = prod2.join("Dimensions - Specific.tsv")
        dim = (prod.mkdir("other-cool-product")
                   .mkdir("other-cool-product.xlsx")
                   .join("Dimensions - Specific.tsv"))
        dim.write("\n".join((
            "Name\tLength\tunits",
            "layer_index\t<i>\t1",
            "other\t42\tm"
        )))

        output = tmpdir.mkdir("cvs")
        sh = SpreadsheetHandler(str(s_dir))
        sh.write_cvs(str(output))

        var_cv = output.join("AMF_product_my_great_product_variable.json")
        dim_cv = output.join("AMF_product_other_cool_product_dimension.json")
        assert var_cv.check()
        assert dim_cv.check()

        decoded = []
        for f in (var_cv, dim_cv):
            try:
                decoded.append(json.load(f))
            except json.decoder.JSONDecodeError:
                assert False, "{} is invalid JSON".format(str(f))

        # check variables - variable CV
        assert decoded[0] == {
            "product_my_great_product_variable": {
                "wind_speed": {
                    "name": "wind_speed",
                    "type": "float32"
                },
                "eastward_wind": {
                    "name": "eastward_wind",
                    "units": "m s-1"
                }
            }
        }
        # check dimensions CV
        assert decoded[1] == {
            "product_other_cool_product_dimension": {
                "layer_index": {
                    "length": "<i>",
                    "units": "1"
                },
                "other": {
                    "length": "42",
                    "units": "m"
                }
            }
        }

    def test_numeric_types(self, spreadsheets_dir):
        # Check that the appropriate attribute values are converted to floats
        assert self.get_var_inner_cv(spreadsheets_dir, [
            ["Variable", "Attribute", "Value"],
            ["some_var", "", ""],
            ["", "valid_min", "123"],
            ["", "volid_mon", "123"],
        ]) == {"some_var": {"valid_min": 123, "volid_mon": "123"}}

    def test_numeric_types_derived_from_file(self, spreadsheets_dir):
        # ...unless the value is <derived from file>
        assert self.get_var_inner_cv(spreadsheets_dir, [
            ["Variable", "Attribute", "Value"],
            ["some_var", "", ""],
            ["", "valid_min", "<derived from file>"],
        ]) == {"some_var": {"valid_min": "<derived from file>"}}

    def test_blank_lines(self, spreadsheets_dir):
        """
        Check blank lines in spreadsheet do not matter
        """
        assert self.get_var_inner_cv(spreadsheets_dir, [
            ["Variable", "Attribute", "Value"],
            ["wind_speed", "", ""],
            ["", "name", "wind_speed"],
            ["", "", ""],
            ["", "type", "float32"]
        ]) == {"wind_speed": {"name": "wind_speed", "type": "float32"}}

    def test_question_marks(self, tmpdir):
        """
        Check that an exception is raised if variable names end in ?s
        """
        no_q_marks = tmpdir.join("no_q_marks.tsv")
        no_q_marks.write("\n".join((
            "Variable\tAttribute\tValue",
            "wind_speed\t\t",
            "\ttype\tfloat32",
        )))
        q_marks = tmpdir.join("q_marks.tsv")
        q_marks.write("\n".join((
            "Variable\tAttribute\tValue",
            "wind_speed?\t\t",
            "\ttype\tfloat32",
        )))
        triple_q_marks = tmpdir.join("triple_q_marks.tsv")
        triple_q_marks.write("\n".join((
            "Variable\tAttribute\tValue",
            "wind_speed???\t\t",
            "\ttype\tfloat32",
        )))

        try:
            c = VariablesCV(no_q_marks.open(), ["noq"])
        except CVParseError as ex:
            assert False, "Undexpected exception: {}".format(ex)

        with pytest.raises(CVParseError):
            c = VariablesCV(q_marks.open(), ["qm"])
        with pytest.raises(CVParseError):
            c = VariablesCV(triple_q_marks.open(), ["tqm"])

    def test_ignore_whitespace(self, spreadsheets_dir):
        """
        Check that whitespace in cell values are ignored
        """
        assert self.get_var_inner_cv(spreadsheets_dir, [
            ["Variable", "Attribute", "Value"],
            ["wind_speed", "", ""],
            ["", "name", " wind_speed   "],
            ["", "", "  "],
            ["", "type", "float32 "]
        ]) == {"wind_speed": {"name": "wind_speed", "type": "float32"}}


class TestYamlGeneration(BaseTest):
    def test_basic(self, spreadsheets_dir, tmpdir):
        s_dir = spreadsheets_dir
        var = (s_dir.join("Product Definition Spreadsheets")
                    .mkdir("my-great-product").mkdir("my-great-product.xlsx")
                    .join("Variables - Specific.tsv"))
        var.write("\n".join((
            "Variable\tAttribute\tValue",
            "wind_speed\t\t",
            "\tname\twind_speed",
            "\ttype\tfloat32",
            "eastward_wind\t\t",
            "\tname\teastward_wind",
            "\ttype\tfloat32",
            "\tunits\tm s-1"
        )))

        dim = (s_dir.join("Product Definition Spreadsheets")
                    .join("my-great-product").join("my-great-product.xlsx")
                    .join("Dimensions - Specific.tsv"))
        dim.write("\n".join((
            "Name\tLength\tunits",
            "one\t1\tm",
            "two\t2\tkm"
        )))

        output = tmpdir.mkdir("yaml")
        sh = SpreadsheetHandler(str(s_dir))
        sh.write_yaml(str(output))

        var_output_yml = output.join("AMF_product_my_great_product_variable.yml")
        dim_output_yml = output.join("AMF_product_my_great_product_dimension.yml")
        assert var_output_yml.check()
        assert dim_output_yml.check()

        decoded = []
        for f in (var_output_yml, dim_output_yml):
            try:
                decoded.append(yaml.load(f.read()))
            except yaml.parser.ParserError:
                assert False, "{} is invalid YAML".format(str(f))

        assert decoded[0] == {
            "suite_name": "product_my_great_product_variable_checks",
            "checks": [
                {
                    "check_id": "check_wind_speed_variable_attrs",
                    "check_name": "checklib.register.nc_file_checks_register.NCVariableMetadataCheck",
                    "comments": "Checks the variable attributes for 'wind_speed'",
                    "parameters": {
                        "pyessv_namespace": "product_my_great_product_variable",
                        "var_id": "wind_speed",
                        "vocabulary_ref": "ncas:amf"
                    }
                },
                {
                    "check_id": "check_wind_speed_variable_type",
                    "check_name": "checklib.register.nc_file_checks_register.VariableTypeCheck",
                    "comments": "Checks the type of variable 'wind_speed'",
                    "parameters": {
                        "var_id": "wind_speed",
                        "dtype": "float32",
                        "vocabulary_ref": "ncas:amf"
                    }
                },
                {
                    "check_id": "check_eastward_wind_variable_attrs",
                    "check_name": "checklib.register.nc_file_checks_register.NCVariableMetadataCheck",
                    "comments": "Checks the variable attributes for 'eastward_wind'",
                    "parameters": {
                        "pyessv_namespace": "product_my_great_product_variable",
                        "var_id": "eastward_wind",
                        "vocabulary_ref": "ncas:amf"
                    }
                },
                {
                    "check_id": "check_eastward_wind_variable_type",
                    "check_name": "checklib.register.nc_file_checks_register.VariableTypeCheck",
                    "comments": "Checks the type of variable 'eastward_wind'",
                    "parameters": {
                        "var_id": "eastward_wind",
                        "dtype": "float32",
                        "vocabulary_ref": "ncas:amf"
                    }
                },
            ]
        }

        assert decoded[1] == {
            "suite_name": "product_my_great_product_dimension_checks",
            "checks": [
                {
                    "check_id": "check_one_dimension_attrs",
                    "check_name": "checklib.register.nc_file_checks_register.NetCDFDimensionCheck",
                    "comments": "Checks the dimension attributes for 'one'",
                    "parameters": {
                        "pyessv_namespace": "product_my_great_product_dimension",
                        "dim_id": "one",
                        "vocabulary_ref": "ncas:amf"
                    }
                },
                {
                    "check_id": "check_two_dimension_attrs",
                    "check_name": "checklib.register.nc_file_checks_register.NetCDFDimensionCheck",
                    "comments": "Checks the dimension attributes for 'two'",
                    "parameters": {
                        "pyessv_namespace": "product_my_great_product_dimension",
                        "dim_id": "two",
                        "vocabulary_ref": "ncas:amf"
                    }
                }
            ]
        }

    def test_top_level_product_yaml(self, spreadsheets_dir, tmpdir):
        """
        Check that a top level YAML file is written for each product/deployment
        mode combination, which includes other YAML files
        """
        s_dir = spreadsheets_dir

        # Write common variables and dimensions
        common_dir = s_dir.join("Common.xlsx")
        common_dir.join("Variables - Air.tsv").write("\n".join((
            "Variable\tAttribute\tValue",
            "some_air_variable\t\t",
            "\ttype\tfloat32"
        )))
        common_dir.join("Variables - Land.tsv").write("\n".join((
            "Variable\tAttribute\tValue",
            "some_land_variable\t\t",
            "\ttype\tfloat32"
        )))
        common_dir.join("Dimensions - Land.tsv").write("\n".join((
            "Name\tLength\tunits",
            "index\t<i>\t1"
        )))

        # Write common global attributes
        common_dir.join("Global Attributes.tsv").write("\n".join((
            "Name\tDescription\tExample\tFixed Value\tCompliance checking rules\tConvention Providence",
            "someattr\ta\tb\tc\tInteger\td"
        )))

        # Write product variables and dimensions
        soil_dir = (s_dir.join("Product Definition Spreadsheets")
                         .mkdir("soil").mkdir("soil.xlsx"))
        soil_dir.join("Variables - Specific.tsv").write("\n".join((
            "Variable\tAttribute\tValue",
            "soil_var\t\t",
            "\ttype\tfloat32"
        )))
        soil_dir.join("Dimensions - Specific.tsv").write("\n".join((
            "Name\tLength\tunits",
            "somedim\t<n>\tK"
        )))

        sh = SpreadsheetHandler(str(s_dir))
        yaml_output = tmpdir.mkdir("yaml")
        sh.write_yaml(str(yaml_output))

        assert yaml_output.join("AMF_product_common_variable_air.yml").check()
        assert yaml_output.join("AMF_product_common_variable_land.yml").check()
        assert yaml_output.join("AMF_product_common_dimension_land.yml").check()
        assert yaml_output.join("AMF_file_info.yml").check()
        assert yaml_output.join("AMF_file_structure.yml").check()
        assert yaml_output.join("AMF_global_attrs.yml").check()

        top_level_air = yaml_output.join("AMF_product_soil_air.yml")
        top_level_land = yaml_output.join("AMF_product_soil_land.yml")
        assert top_level_air.check()
        assert top_level_land.check()

        assert yaml.load(top_level_air.read()) == {
            "suite_name": "product_soil_air_checks",
            "checks": [
                # Global checks
                {"__INCLUDE__": "AMF_file_info.yml"},
                {"__INCLUDE__": "AMF_file_structure.yml"},
                {"__INCLUDE__": "AMF_global_attrs.yml"},
                # Common product checks
                {"__INCLUDE__": "AMF_product_common_variable_air.yml"},
                # Product specific
                {"__INCLUDE__": "AMF_product_soil_dimension.yml"},
                {"__INCLUDE__": "AMF_product_soil_variable.yml"}
            ]
        }

        # Land one should be basically the same as air but s/air/land/, and
        # there is also common dimensions CV for land
        assert yaml.load(top_level_land.read()) == {
            "suite_name": "product_soil_land_checks",
            "checks": [
                {"__INCLUDE__": "AMF_file_info.yml"},
                {"__INCLUDE__": "AMF_file_structure.yml"},
                {"__INCLUDE__": "AMF_global_attrs.yml"},
                {"__INCLUDE__": "AMF_product_common_dimension_land.yml"},
                {"__INCLUDE__": "AMF_product_common_variable_land.yml"},
                {"__INCLUDE__": "AMF_product_soil_dimension.yml"},
                {"__INCLUDE__": "AMF_product_soil_variable.yml"}
            ]
        }

    def test_file_info_yaml_check(self, spreadsheets_dir, tmpdir):
        sh = SpreadsheetHandler(str(spreadsheets_dir))
        output = tmpdir.mkdir("yaml")
        sh.write_yaml(str(output))

        file_info_check = output.join("AMF_file_info.yml")
        assert file_info_check.check()
        assert yaml.load(file_info_check.read()) == {
            "suite_name": "file_info_checks",
            "checks": [
                {
                    "check_id": "check_soft_file_size_limit",
                    "check_name": "checklib.register.file_checks_register.FileSizeCheck",
                    "check_level": "LOW",
                    "parameters": {"threshold": 2, "strictness": "soft"}
                },
                {
                    "check_id": "check_hard_file_size_limit",
                    "check_name": "checklib.register.file_checks_register.FileSizeCheck",
                    "check_level": "HIGH",
                    "parameters": {"threshold": 4, "strictness": "hard"}
                },
                {
                    "check_id": "check_filename_structure",
                    "check_name": "checklib.register.file_checks_register.FileNameStructureCheck",
                    "check_level": "HIGH",
                    "parameters": {"delimiter": "_", "extension": ".nc"}
                }
            ]
        }

    def test_file_structure_yaml_check(self, spreadsheets_dir, tmpdir):
        sh = SpreadsheetHandler(str(spreadsheets_dir))
        output = tmpdir.mkdir("yaml")
        sh.write_yaml(str(output))

        file_structure_check = output.join("AMF_file_structure.yml")
        assert file_structure_check.check()
        assert yaml.load(file_structure_check.read()) == {
            "suite_name": "file_structure_checks",
            "checks": [{
                "check_id": "check_valid_netcdf4_file",
                "check_name": "checklib.register.nc_file_checks_register.NetCDFFormatCheck",
                "parameters": {"format": "NETCDF4_CLASSIC"}
            }]
        }

    def test_global_attrs_yaml_check(self, spreadsheets_dir, tmpdir):
        s_dir = spreadsheets_dir
        global_attrs_tsv = s_dir.join("Common.xlsx").join("Global Attributes.tsv")
        global_attrs_tsv.write("\n".join((
            "Name\tDescription\tExample\tFixed Value\tCompliance checking rules\tConvention Providence",
            "myattr\td\te\tf\tValid email\tc",
            "aaaa\td\te\tf\tSomething strange here\tc",
            "bbbb\td\te\tf",
            "otherattr\td\te\tf\tInteger\tc"
        )))

        sh = SpreadsheetHandler(str(s_dir))
        output = tmpdir.mkdir("yaml")
        sh.write_yaml(str(output))

        global_attr_yaml = output.join("AMF_global_attrs.yml")
        assert global_attr_yaml.check()
        decoded = yaml.load(global_attr_yaml.read())

        assert "suite_name" in decoded
        assert "checks" in decoded
        assert decoded["suite_name"] == "global_attrs_checks"
        assert len(decoded["checks"]) == 2

        expected_check_name = "checklib.register.nc_file_checks_register.GlobalAttrRegexCheck"
        assert decoded["checks"][0]["check_name"] == expected_check_name
        assert decoded["checks"][1]["check_name"] == expected_check_name
        email_regex = GlobalAttrCheck.spreadsheet_value_to_regex("Valid email")
        assert decoded["checks"][0]["parameters"]["regex"] == email_regex
        int_regex = GlobalAttrCheck.spreadsheet_value_to_regex("Integer")
        assert decoded["checks"][1]["parameters"]["regex"] == int_regex


class TestCommonVariablesAndDimensions(BaseTest):
    def test_common(self, spreadsheets_dir, tmpdir):
        s_dir = spreadsheets_dir
        common_dir = s_dir.join("Common.xlsx")
        var_air = common_dir.join("Variables - Air.tsv")
        var_sea = common_dir.join("Variables - Sea.tsv")
        dim_land = common_dir.join("Dimensions - Land.tsv")

        var_air.write("\n".join((
            "Variable\tAttribute\tValue",
            "some_air_variable\t\t",
            "\tthingy\tthis_thing",
            "\ttype\tfloat32"
        )))
        var_sea.write("\n".join((
            "Variable\tAttribute\tValue",
            "some_sea_variable\t\t",
            "\tthingy\tthat_thing",
            "\ttype\tstring"
        )))
        dim_land.write("\n".join((
            "Name\tLength\tunits",
            "some_dim\t42\tm"
        )))

        sh = SpreadsheetHandler(str(s_dir))

        cv_output = tmpdir.mkdir("cvs")
        yaml_output = tmpdir.mkdir("yaml")
        sh.write_cvs(str(cv_output))
        sh.write_yaml(str(yaml_output))

        # Check CV and YAML files exist
        var_air_output = cv_output.join("AMF_product_common_variable_air.json")
        assert var_air_output.check()
        assert cv_output.join("AMF_product_common_variable_sea.json").check()
        assert cv_output.join("AMF_product_common_dimension_land.json").check()

        assert yaml_output.join("AMF_product_common_variable_air.yml").check()
        assert yaml_output.join("AMF_product_common_variable_sea.yml").check()

        # Check the content of one of the CVs
        assert json.load(var_air_output) == {
            "product_common_variable_air": {
                "some_air_variable": {
                    "thingy": "this_thing",
                    "type": "float32"
                }
            }
        }


class TestVocabulariesSheet(BaseTest):
    """
    Test that CVs are generated from the sheets within the 'Vocabularies'
    spreadsheet
    """
    def test_instruments(self, spreadsheets_dir, tmpdir):
        s_dir = spreadsheets_dir
        instr = s_dir.join("Vocabularies").join("Instrument Name & Descriptors.tsv")
        instr.write("\n".join((
            # Include some missing old names, some multiple names, and
            # extraneous whitespace
            "Old Instrument Name\tNew Instrument Name\tDescriptor",
            "man-radar-1290mhz\tncas-radar-wind-profiler-1\tNCAS Mobile Radar Wind Profiler unit 1",
            "\tncas-ceilometer-4\t NCAS Lidar Ceilometer unit 4",
            "man-o3lidar\tncas-o3-lidar-1\tNCAS Mobile O3 lidar unit 1",
            "cv-met-tower, cv-met-webdaq\tncas-aws-7\tNCAS Automatic Weather Station unit 7"
        )))

        sh = SpreadsheetHandler(str(s_dir))
        output = tmpdir.mkdir("cvs")
        sh.write_cvs(str(output))
        instr_cv = output.join("AMF_instrument.json")
        assert instr_cv.check()
        assert json.load(instr_cv) == {
            "instrument": {
                "ncas-radar-wind-profiler-1": {
                    "instrument_id": "ncas-radar-wind-profiler-1",
                    "previous_instrument_ids": ["man-radar-1290mhz"],
                    "description": "NCAS Mobile Radar Wind Profiler unit 1"
                },
                "ncas-ceilometer-4": {
                    "instrument_id": "ncas-ceilometer-4",
                    "previous_instrument_ids": [],
                    "description": "NCAS Lidar Ceilometer unit 4"
                },
                "ncas-o3-lidar-1": {
                    "instrument_id": "ncas-o3-lidar-1",
                    "previous_instrument_ids": ["man-o3lidar"],
                    "description": "NCAS Mobile O3 lidar unit 1"
                },
                "ncas-aws-7": {
                    "instrument_id": "ncas-aws-7",
                    "previous_instrument_ids": ["cv-met-tower", "cv-met-webdaq"],
                    "description": "NCAS Automatic Weather Station unit 7"
                }
            }
        }

    def test_duplicate_instrument_id(self, spreadsheets_dir, tmpdir):
        """
        Check that if there are two instruments with the same ID, a warning is
        printed and one of them is overwritten
        """
        s_dir = spreadsheets_dir
        instr = s_dir.join("Vocabularies").join("Instrument Name & Descriptors.tsv")
        instr.write("\n".join((
            "Old Instrument Name\tNew Instrument Name\tDescriptor",
            "old1\tmyinstr\tFirst instrument",
            "old2\tmyinstr\tSecond instrument"
        )))
        output = tmpdir.mkdir("cvs")
        stderr = StringIO()
        sh = SpreadsheetHandler(str(s_dir))
        sys.stderr = stderr
        sh.write_cvs(str(output))
        sys.stderr = sys.__stderr__

        instr_output = output.join("AMF_instrument.json")
        assert instr_output.check()
        assert json.load(instr_output) == {
            "instrument": {
                "myinstr": {
                    "instrument_id": "myinstr",
                    "previous_instrument_ids": ["old1"],
                    "description": "First instrument"
                }
            }
        }
        stderr_contents = stderr.getvalue().lower()
        assert "duplicate instrument name" in stderr_contents

        # Normal case: warning not shown
        instr.write("\n".join((
            "Old Instrument Name\tNew Instrument Name\tDescriptor",
            "old1\tmyinstr1\tFirst instrument",
            "old2\tmyinstr2\tSecond instrument"
        )))
        stderr = StringIO()
        sh = SpreadsheetHandler(str(s_dir))
        sys.stderr = stderr
        sh.write_cvs(str(output))
        sys.stderr = sys.__stderr__
        stderr_contents = stderr.getvalue().lower()
        assert "duplicate instrument name" not in stderr_contents

    def test_product(self, spreadsheets_dir, tmpdir):
        s_dir = spreadsheets_dir
        prod = s_dir.join("Vocabularies").join("Data Products.tsv")
        prod.write("\n".join((
            "Data Product",
            "snr-winds",
            "aerosol-backscatter",
            "aerosol-extinction",
            "cloud-base",
            "o3-concentration-profiles"
        )))

        sh = SpreadsheetHandler(str(s_dir))
        output = tmpdir.mkdir("cvs")
        sh.write_cvs(str(output))
        prod_cv = output.join("AMF_product.json")
        assert prod_cv.check()
        assert json.load(prod_cv) == {
            "product": [
                "snr-winds",
                "aerosol-backscatter",
                "aerosol-extinction",
                "cloud-base",
                "o3-concentration-profiles"
            ]
        }

    def test_platform(self, spreadsheets_dir, tmpdir):
        s_dir = spreadsheets_dir
        plat = s_dir.join("Vocabularies").join("Platforms.tsv")
        plat.write("\n".join((
            "Platform ID\tPlatform Description",
            "wao\tweybourne atmospheric observatory",
            "cvao\tcape verde atmospheric observatory"
        )))
        output = tmpdir.mkdir("cvs")
        sh = SpreadsheetHandler(str(s_dir))
        sh.write_cvs(str(output))

        plat_output = output.join("AMF_platform.json")
        assert plat_output.check()
        assert json.load(plat_output) == {
            "platform": {
                "wao": {
                    "platform_id": "wao",
                    "description": "weybourne atmospheric observatory"
                },
                "cvao": {
                    "platform_id": "cvao",
                    "description": "cape verde atmospheric observatory"
                }
            }
        }

    def test_scientist(self, spreadsheets_dir, tmpdir):
        s_dir = spreadsheets_dir
        plat = s_dir.join("Vocabularies").join("Creators.tsv")
        plat.write("\n".join((
            "name\temail\torcid\tconfirmed",
            # With 'confirmed' column
            "Bob Smith\tbob@smith.com\thttps://orcid.org/123\tyes",
            "Bob Smath\tbob@smath.com\thttps://orcid.org/234\tno",
            # and without
            "Dave Jones\tdave@jones.com\thttps://orcid.org/345",
            # Without orcid
            "Paul Jones\tpaul@jones.com\t\tyes",
            "Paul Janes\tpaul@janes.com\t",
            "Paul Junes\tpaul@junes.com"
        )))
        output = tmpdir.mkdir("cvs")
        sh = SpreadsheetHandler(str(s_dir))
        sh.write_cvs(str(output))

        sci_output = output.join("AMF_scientist.json")
        assert sci_output.check()
        print(json.dumps(json.load(sci_output), indent=4))
        assert json.load(sci_output) == {
            "scientist": {
                "bob@smith.com": {
                    "name": "Bob Smith",
                    "primary_email": "bob@smith.com",
                    "previous_emails": [],
                    "orcid": "https://orcid.org/123"
                },
                "bob@smath.com": {
                    "name": "Bob Smath",
                    "primary_email": "bob@smath.com",
                    "previous_emails": [],
                    "orcid": "https://orcid.org/234"
                },
                "dave@jones.com": {
                    "name": "Dave Jones",
                    "primary_email": "dave@jones.com",
                    "previous_emails": [],
                    "orcid": "https://orcid.org/345"
                },
                "paul@jones.com": {
                    "name": "Paul Jones",
                    "primary_email": "paul@jones.com",
                    "previous_emails": [],
                    "orcid": None
                },
                "paul@janes.com": {
                    "name": "Paul Janes",
                    "primary_email": "paul@janes.com",
                    "previous_emails": [],
                    "orcid": None
                },
                "paul@junes.com": {
                    "name": "Paul Junes",
                    "primary_email": "paul@junes.com",
                    "previous_emails": [],
                    "orcid": None
                }
            }
        }


class TestPyessvGeneration(BaseTest):
    def test_pyessv_cvs_are_generated(self, spreadsheets_dir, tmpdir):
        # Create spreadsheets to generate some CVs
        s_dir = spreadsheets_dir

        # Create scientists CV, to test that @ are allowed in namespaces
        sci_tsv = s_dir.join("Vocabularies").join("Creators.tsv")
        sci_tsv.write("\n".join((
            "name\temail\torcid\tconfirmed",
            "Bob Smith\tbob@smith.com\thttps://orcid.org/123\tyes",
            "Jane Smith\tjane@smith.com\thttps://orcid.org/999\tyes",
        )))

        # Create products CV, since this is a list rather dict like other CVs
        prod_tsv = s_dir.join("Vocabularies").join("Data Products.tsv")
        prod_tsv.write("\n".join((
            "Data Product",
            "snr-winds",
            "aerosol-backscatter"
        )))

        # Write JSON CVs and pyessv CVs
        sh = SpreadsheetHandler(str(s_dir))
        json_cvs_output = tmpdir.mkdir("json_cvs")
        pyessv_cvs_output = tmpdir.mkdir("pyessv_cvs")
        sh.write_cvs(str(json_cvs_output), write_pyessv=True,
                     pyessv_root=str(pyessv_cvs_output))

        root = pyessv_cvs_output.join("ncas")
        assert root.join("MANIFEST").check()
        assert root.join("amf").check()

        # Check the contents of some CVs
        bob_term = root.join("amf").join("scientist").join("bob@smith.com")
        assert bob_term.check()
        bob_term_decoded = json.load(bob_term)
        assert "data" in bob_term_decoded
        assert bob_term_decoded["data"] == {
            "primary_email": "bob@smith.com",
            "previous_emails": [],
            "name": "Bob Smith",
            "orcid": "https://orcid.org/123"
        }

        jane_term = root.join("amf").join("scientist").join("jane@smith.com")
        assert jane_term.check()
        jane_term_decoded = json.load(jane_term)
        assert "data" in jane_term_decoded
        assert jane_term_decoded["data"] == {
            "primary_email": "jane@smith.com",
            "previous_emails": [],
            "name": "Jane Smith",
            "orcid": "https://orcid.org/999"
        }

        product_term = root.join("amf").join("product").join("snr-winds")
        assert product_term.check()


class TestGlobalAttributeRegexes(BaseTest):
    def test_get_regex(self):
        test_data = {
            "String: min 2 characters": {
                "match": [
                    "hello",
                    "h ello",
                    " hello",
                    "he",
                    "09",
                    "H-E-L-L-o",
                    "-_",
                    "h@b.com",
                ],
                "no_match": [
                    "",
                    "a",
                    "7",
                ]
            },
            "Integer": {
                "match": [
                    "123456",
                    "0123",
                    "1",
                    "0",
                    "-1234",
                ],
                "no_match": [
                    "0.0",
                    "hello",
                    "123hello",
                ]
            },
            "Match: YYYY-MM-DDThh:mm:ss.*": {
                "match": [
                    "2018-01-01T00:00:00.hello",
                    "1990-12-31T12:34:56",
                ],
                "no_match": [
                    "1st July 2018",
                    "blah",
                    "abcd-ef-ghT00:00:00",
                ]
            },
            "Valid email": {
                "match": [
                    "hello@there.com",
                    "hello123.456.there@everyone.com",
                    "a.b.c@d.e.f.ac.uk",
                ],
                "no_match": [
                    "hello at there.com",
                    "hello @ there.com",
                ]
            },
            "Match: vN.M": {
                "match": [
                    "v0.0",
                    "v1.2",
                    "v3.0",
                ],
                "no_match": [
                    "v1-2",
                    "v4",
                    "1.3",
                    "v12.3",
                    "v1.23",
                ]
            },
        }

        for spreadsheet_value, strings in test_data.items():
            regex = GlobalAttrCheck.spreadsheet_value_to_regex(spreadsheet_value)
            for string in strings["match"]:
                assert re.match(regex, string)
            for string in strings["no_match"]:
                assert not re.match(regex, string)
