"""
This script converts tsv files to a JSON controlled vocabulary format.

Largely based on Ag's work at:
https://github.com/agstephens/AMF_CVs/blob/a87dd06eee27a6cf517a6f5346df6f07468d1120/scripts/write_variables_json.py
"""

import os
import re
import json
import sys
from collections import OrderedDict
from csv import DictReader


class BaseCvGenerator:
    """
    Base class for generating a controlled vocab JSON file from a TSV file.
    Subclass this class for each CV type and define the properties and methods
    below
    """
    # String that is prefixed to TSV filenames for this type of CV
    tsv_filename_prefix = None

    # Name to use for this CV type in namespace
    name = None

    @classmethod
    def convert_to_json(cls, reader, namespace):
        """
        Read a TSV file and convert it to a dictionary in the controlled
        vocab format.

        `reader` is a csv.DictReader instance
        """
        raise NotImplementedError


class VariableCvGenerator(BaseCvGenerator):
    tsv_filename_prefix = "Variables"
    name = "variable"

    # Attributes whose value should be interpreted as a float instead of string
    numeric_types = ("valid_min", "valid_max")

    @classmethod
    def convert_to_json(cls, reader, namespace):
        cv = {namespace: OrderedDict()}
        for row in reader:
            if row["Variable"]:
                # Variable names containing ??? cause problems with pyessv,
                # and are probably not correct anyway
                if row["Variable"].endswith("???"):
                    raise ValueError("Invalid variable name '{}'".format(row["Variable"]))

                current_var = row["Variable"]
                cv[namespace][current_var] = OrderedDict()

            elif row["Attribute"] and row["Value"]:
                attr = row["Attribute"]
                value = row["Value"].strip()  # Some of the sheets have extraneous whitespace...

                if attr in cls.numeric_types and not value.startswith("<"):
                    value = float(value)

                cv[namespace][current_var][attr] = value
        return cv


class DimensionCvGenerator(BaseCvGenerator):
    tsv_filename_prefix = "Dimensions"
    name = "dimension"

    @classmethod
    def convert_to_json(cls, reader, namespace):
        cv = {namespace: OrderedDict()}
        for row in reader:
            if row["Name"] and row["Length"] and row["units"]:
                name, length, units = map(str.strip, (row[x] for x in ("Name", "Length", "units")))
                cv[namespace][name] = {
                    "length": length,
                    "units": units
                }
        if not cv[namespace]:
            raise ValueError("No dimensions found")
        return cv


def main(spreadsheets_dir, out_dir):
    """
    Find TSV files containing metadata about variables etc under
    `spreadsheets_dir` and convert them to a JSON format. Save the resulting
    JSON in `out_dir`.

    The files in `spreadsheets_dir` should be structured like the output of
    download_from_drive.py
    """
    if not os.path.isdir(spreadsheets_dir):
        sys.stderr.write("{}: No such directory '{}'".format(sys.argv[0], spreadsheets_dir) +
                         os.linesep)
        sys.exit(1)

    # Build a mapping from filename prefix to generator class
    cv_generator_mapping = {cls.tsv_filename_prefix: cls
                            for cls in (VariableCvGenerator, DimensionCvGenerator)}

    # Build a regex to figure out with generator class to use for a given file
    prefixes = "|".join(cv_generator_mapping.keys())
    regex = re.compile(r"(?P<cv_type>{prefixes})( - (?P<type>[a-zA-Z]*))?.tsv"
                       .format(prefixes=prefixes))

    for dirpath, dirnames, filenames in os.walk(spreadsheets_dir):
        for fname in filenames:
            match = regex.match(fname)
            if match:
                generator_cls = cv_generator_mapping[match.group("cv_type")]

                # Product name is the name of the spreadsheet, which is the
                # parent directory of the tsv file
                product_name = os.path.split(dirpath)[-1].lower().replace("-", "_")
                if product_name.endswith(".xlsx"):
                    product_name = product_name[:-5]

                # Create namespace for this CV. Needs to be unique across all
                # products; will be of the form
                # <product_name>(_<type>)?_<cv-type> where type is the last
                # component of the sheet name (but ignore 'specific'), and
                # cv-type is 'variable' or 'dimension'
                namespace = product_name
                type_name = match.group("type")
                if type_name:
                    type_name = type_name.lower()
                    if type_name != "specific":
                        namespace += "_{}".format(type_name)
                namespace += "_{}".format(generator_cls.name)

                json_filename = "AMF_{}.json".format(namespace)
                out_file = os.path.join(out_dir, json_filename)

                with open(os.path.join(dirpath, fname)) as tsv_file:
                    reader = DictReader(tsv_file, delimiter="\t")

                    try:
                        # Convert to JSON and write out
                        print("Writing to {}".format(out_file))
                        output = generator_cls.convert_to_json(reader, namespace)
                        with open(out_file, "w") as f:
                            json.dump(output, f, indent=4)

                    except ValueError as ex:
                        sys.stderr.write(
                            "Error in product {}, file '{}': {}".format(product_name, fname, ex)
                            + os.linesep
                        )


if __name__ == "__main__":
    if len(sys.argv) < 3:
        usage = "Usage: {} IN_DIR OUT_DIR".format(sys.argv[0])
        sys.stderr.write(usage + os.linesep)
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])
