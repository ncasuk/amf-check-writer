import json

from amf_check_writer.cv_handlers import BatchCvGenerator


class TestCvGeneration:
    def get_var_inner_cv(self, tmpdir, tsv):
        """
        Create a TSV from the given list of lists of columns, and process it
        as a variable TSV file. Return the inner dictionary of the generated
        JSON CV
        """
        spreadsheets_dir = tmpdir.mkdir("s")
        prod_dir = spreadsheets_dir.mkdir("product.xlsx")
        var_sheet = prod_dir.join("Variables - specific.tsv")
        var_sheet.write(
            "\n".join(("\t".join(x for x in row)) for row in tsv)
        )
        output = tmpdir.mkdir("output")
        BatchCvGenerator.write_cvs(str(spreadsheets_dir), str(output))

        cv_file = output.join("AMF_product_variable.json")
        assert cv_file.check()
        obj = json.load(cv_file)
        assert "product_variable" in obj
        return obj["product_variable"]

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
        BatchCvGenerator.write_cvs(str(s_dir), str(output))

        air_cv = output.join("AMF_my_great_product_air_variable.json")
        spec_cv = output.join("AMF_my_great_product_variable.json")
        dim_cv = output.join("AMF_other_cool_product_dimension.json")
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
            "my_great_product_air_variable": {
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
            "other_cool_product_dimension": {
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
