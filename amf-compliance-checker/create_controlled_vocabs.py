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


# Attributes whose value should be interpreted as a float instead of string
NUMERIC_TYPES = ("valid_min", "valid_max")


def convert_to_json(tsv_filename, namespace):
    """
    Read a tsv file and return a dictionary in the controlled vocab format
    """
    cv = {namespace: OrderedDict()}

    with open(tsv_filename) as tsv_file:
        reader = DictReader(tsv_file, delimiter="\t")

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

                if attr in NUMERIC_TYPES and not value.startswith("<"):
                    value = float(value)

                cv[namespace][current_var][attr] = value
    return cv


def main(spreadsheets_dir, out_dir):
    """
    Find TSV files containing metadata about variables under `spreadsheets_dir`
    and convert them to a JSON format. Save the resulting JSON in `out_dir`.

    The files in `spreadsheets_dir` should be structed like the output of
    download_from_drive.py
    """
    if not os.path.isdir(spreadsheets_dir):
        sys.stderr.write("{}: No such directory '{}'".format(sys.argv[0], spreadsheets_dir) +
                         os.linesep)
        sys.exit(1)

    variables_sheet_regex = re.compile(r"Variables( - [a-zA-Z]*)?.tsv")

    for dirpath, dirnames, filenames in os.walk(spreadsheets_dir):
        for fname in filenames:
            match = variables_sheet_regex.match(fname)
            if match:
                # Product name is the name of the spreadsheet, which is the
                # parent directory of the tsv file
                product_name = os.path.split(dirpath)[-1].lower().replace("-", "_")
                if product_name.endswith(".xlsx"):
                    product_name = product_name[:-5]

                # Remove .tsv suffix and split into components
                sheet_name_parts = fname[:-4].lower().split(" - ")

                # Create namespace for variables for this product. Needs to be
                # unique across all products; will be of the form
                # <product_name>(_<type>)?_variable where type if the last
                # component of the sheet name (but ignore 'specific')
                namespace = product_name
                var_type = match.groups()[0]
                if var_type:
                    # Remove " - " prefix and convert to lower case
                    var_type = var_type.lower()[3:]
                    if var_type != "specific":
                        namespace += "_{}".format(var_type)
                namespace += "_variable"

                json_filename = "amf_{}.json".format(namespace)
                out_file = os.path.join(out_dir, json_filename)

                try:
                    # Convert to JSON and write out
                    output = convert_to_json(os.path.join(dirpath, fname), namespace)
                    print("Writing to {}".format(out_file))
                    with open(out_file, "w") as f:
                        json.dump(output, f, indent=4)

                except ValueError as ex:
                    sys.stderr.write("Error in file {}: {}".format(fname, ex) +
                                     os.linesep)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        usage = "Usage: {} IN_DIR OUT_DIR".format(sys.argv[0])
        sys.stderr.write(usage + os.linesep)
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])
