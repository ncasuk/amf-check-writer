import json
import yaml

from amf_check_writer.cv_handlers import BatchTsvProcessor


class TestCvGeneration(object):
    def get_var_inner_cv(self, tmpdir, tsv):
        """
        Create a TSV from the given list of lists of columns, and process it
        as a variable TSV file. Return the inner dictionary of the generated
        JSON CV
        """
        spreadsheets_dir = tmpdir.mkdir("s")
        prod_dir = spreadsheets_dir.mkdir("wind-speed.xlsx")
        var_sheet = prod_dir.join("Variables - specific.tsv")
        var_sheet.write(
            "\n".join(("\t".join(x for x in row)) for row in tsv)
        )
        output = tmpdir.mkdir("output")
        BatchTsvProcessor.write_cvs(str(spreadsheets_dir), str(output))

        cv_file = output.join("AMF_product_wind_speed_variable.json")
        assert cv_file.check()
        obj = json.load(cv_file)
        assert "product_wind_speed_variable" in obj
        return obj["product_wind_speed_variable"]

    def test_basic(self, tmpdir):
        # variables
        s_dir = tmpdir.mkdir("spreadsheets")
        prod = s_dir.mkdir("my-great-product.xlsx")
        air = prod.join("Variables - Air.tsv")
        spec = prod.join("Variables - Specific.tsv")
        for f in (air, spec):
            f.write("\n".join((
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
        dim.write("\n".join((
            "Name\tLength\tunits",
            "layer_index\t<i>\t1",
            "other\t42\tm"
        )))

        output = tmpdir.mkdir("cvs")
        BatchTsvProcessor.write_cvs(str(s_dir), str(output))

        air_cv = output.join("AMF_product_my_great_product_variable_air.json")
        spec_cv = output.join("AMF_product_my_great_product_variable.json")
        dim_cv = output.join("AMF_product_other_cool_product_dimension.json")
        assert air_cv.check()
        assert spec_cv.check()
        assert dim_cv.check()

        decoded = []
        for f in (air_cv, spec_cv, dim_cv):
            try:
                decoded.append(json.load(f))
            except json.decoder.JSONDecodeError:
                assert False, "{} is invalid JSON".format(str(f))

        # check variables - air CV
        assert decoded[0] == {
            "product_my_great_product_variable_air": {
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
        assert decoded[2] == {
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

    def test_numeric_types(self, tmpdir):
        assert self.get_var_inner_cv(tmpdir, [
            ["Variable", "Attribute", "Value"],
            ["some_var", "", ""],
            ["", "valid_min", "123"],
            ["", "volid_mon", "123"],
        ]) == {"some_var": {"valid_min": 123, "volid_mon": "123"}}

    def test_blank_lines(self, tmpdir):
        """
        Check blank lines in spreadsheet do not matter
        """
        assert self.get_var_inner_cv(tmpdir, [
            ["Variable", "Attribute", "Value"],
            ["wind_speed", "", ""],
            ["", "name", "wind_speed"],
            ["", "", ""],
            ["", "type", "float32"]
        ]) == {"wind_speed": {"name": "wind_speed", "type": "float32"}}

    def test_ignore_whitespace(self, tmpdir):
        """
        Check that whitespace in cell values are ignored
        """
        assert self.get_var_inner_cv(tmpdir, [
            ["Variable", "Attribute", "Value"],
            ["wind_speed", "", ""],
            ["", "name", " wind_speed   "],
            ["", "", "  "],
            ["", "type", "float32 "]
        ]) == {"wind_speed": {"name": "wind_speed", "type": "float32"}}


class TestYamlGeneration(object):
    def test_basic(self, tmpdir):
        s_dir = tmpdir.mkdir("spreadsheets")
        prod = s_dir.mkdir("my-great-product.xlsx")
        air = prod.join("Variables - Specific.tsv")
        air.write("\n".join((
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
        BatchTsvProcessor.write_yaml(str(s_dir), str(output))

        output_yml = output.join("amf_product_my_great_product_variable.yml")
        assert output_yml.check()

        try:
            decoded = yaml.load(output_yml.read())
        except yaml.parser.ParserError:
            assert False, "{} is invalid YAML".format(str(output_yml))

        # check variables - air CV
        print(json.dumps(decoded, indent=4))
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
