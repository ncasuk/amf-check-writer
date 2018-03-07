"""
This script converts tsv files to a JSON controlled vocabulary format.

Largely based on Ag's work at:
https://github.com/agstephens/AMF_CVs/blob/a87dd06eee27a6cf517a6f5346df6f07468d1120/scripts/write_variables_json.py
"""

import os
import json
import sys
from collections import OrderedDict
from csv import DictReader


# Attributes whose value should be interpreted as a float instead of string
NUMERIC_TYPES = ("valid_min", "valid_max")


def convert_to_json(tsv_filename):
    """
    Read a tsv file and return a dictionary in the controlled vocab format
    """
    cv = {"variable": OrderedDict()}

    with open(tsv_filename) as tsv_file:
        reader = DictReader(tsv_file, delimiter="\t")

        for row in reader:
            if row["Variable"]:
                current_var = row["Variable"]
                cv["variable"][current_var] = OrderedDict()

            elif row["Attribute"] and row["Value"]:
                attr = row["Attribute"]
                value = row["Value"].strip()  # Some of the sheets have extraneous whitespace...

                if attr in NUMERIC_TYPES and not value.startswith("<"):
                    value = float(value)

                cv["variable"][current_var][attr] = value
    return cv


def main(spreadsheets_dir, out_dir):
    """
    Find TSV files containing metadata about variables under `spreadsheets_dir`
    and convert them to a JSON format. Save the resulting JSON in `out_dir`.

    The files in `spreadsheets_dir` should be structed like the output of
    download_from_drive.py
    """
    for dirpath, dirnames, filenames in os.walk(spreadsheets_dir):
        for fname in filenames:
            if fname.endswith(".tsv") and fname.startswith("Variables"):
                # Product name is the name of the spreadsheet, which is the
                # parent directory of the tsv file
                product_name = os.path.split(dirpath)[-1].lower()
                if product_name.endswith(".xlsx"):
                    product_name = product_name[:-5]

                # Format sheet nicely
                sheet_name = fname[:-4].lower().replace(" ", "-").replace("---", "-")

                # Convert to JSON and write out
                json_filename = "amf-{}-{}.json".format(product_name, sheet_name)
                out_file = os.path.join(out_dir, json_filename)
                print("Writing to {}".format(out_file))
                with open(out_file, "w") as f:
                    json.dump(convert_to_json(os.path.join(dirpath, fname)), f, indent=4)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        usage = "Usage: {} IN_DIR OUT_DIR".format(sys.argv[0])
        sys.stderr.write(usage + os.linesep)
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])
