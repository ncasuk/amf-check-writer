"""
Tests to add:
- CVParseError raised when dimensions sheet is empty, invalid var name
"""
import os
import json
import yaml

import pytest

from amf_check_writer.spreadsheet_handler import SpreadsheetHandler


class BaseTest(object):
    @pytest.fixture
    def spreadsheets_dir(self, tmpdir):
        s = tmpdir.mkdir("spreadsheets")
        s.mkdir("Common.xlsx")
        s.mkdir("Product Definition Spreadsheets")
        vars_sheet = s.mkdir("Vocabularies")
        vars_sheet.join("Instrument Name & Descriptors.tsv").write("")
        return s


class TestCvGeneration(BaseTest):
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

        output = tmpdir.mkdir("yaml")
        sh = SpreadsheetHandler(str(s_dir))
        sh.write_yaml(str(output))

        output_yml = output.join("AMF_product_my_great_product_variable.yml")
        assert output_yml.check()

        try:
            decoded = yaml.load(output_yml.read())
        except yaml.parser.ParserError:
            assert False, "{} is invalid YAML".format(str(output_yml))

        assert decoded == {
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
        print(instr_cv.read())
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
