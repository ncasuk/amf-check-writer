"""
Wrapper script around compliance-checker to automatically find and run the
relevant YAML checks for AMF datasets.
"""
from __future__ import print_function
import os
import subprocess
import sys
import re
import argparse

from netCDF4 import Dataset

from amf_check_writer.spreadsheet_handler import DeploymentModes


# Regex to match filenames and extract product name
FILENAME_REGEX = re.compile(
    r"^([^\s_]+_){2}"                 # <instrument>_<platform>_
    r"(\d{4}(\d{2})?(\d{2})?|\d{8}(-\d{2})?(\d{2})?(\d{2})?)_"
                                      # Valid options:
                                      # <YYYY>
                                      # <YYYY><MM>
                                      # <YYYY><MM><DD>
                                      # <YYYY><MM><DD>-<HH>
                                      # <YYYY><MM><DD>-<HH><mm>
                                      # <YYYY><MM><DD>-<HH><mm><ss>
    r"(?P<product>[a-zA-Z][^\s_]+)_"  # data product
    r"([a-zA-Z][^\s_]*_)*"            # optional: <option1>_<option2>_...<optionN>_
    r"v\d+(\.\d+)?"                   # version: vN[.M]
    r"\.nc$"                          # .nc extension
)


# The above regex in a human readable form, used in error messages. MAKE SURE
# IT MATCHES THE REGEX!
FILENAME_FORMAT_HUMAN_READABLE = (
    "<instrument_name>_<platform_name>_<YYYY><MM><DD>-<HH><mm><SS>_<data_product>_[<option1>_<option2>_...<optionN>_]v<version>.nc"
)


def get_product_from_filename(path):
    """
    Calculate the product name from a dataset filename
    :param path: path to dataset
    :return:     product name as a string

    :raises ValueError: if filename does not match the expected regex
    """
    fname = os.path.basename(path)
    match = FILENAME_REGEX.match(fname)
    if not match:
        raise ValueError(
            "Filename '{}' does not match expected format '{}'"
            .format(fname, FILENAME_FORMAT_HUMAN_READABLE)
        )
    return match.group("product")


def get_deployment_mode(path):
    """
    Work out the 'deployment mode' from the global attributes in a NetCDF file
    :param path: path to dataset
    :return:     Mode as a value from `DeploymentModes` enumeration
    :raises ValueError: if mode cannot be determined or is invalid
    """
    fname = os.path.basename(path)
    d = Dataset(path)
    try:
        mode_str = d.deployment_mode
    except AttributeError:
        raise ValueError("Attribute 'deployment_mode' not found in '{}'".format(fname))

    for mode in DeploymentModes:
        if mode.value.lower() == mode_str:
            return mode

    raise ValueError(
        "Unrecognised deployment mode '{}' in '{}'".format(mode_str, fname)
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "files",
        nargs="+",
        help="Dataset(s) to run checks against, or a directory to find "
             "datasets in"
    )
    # Options
    parser.add_argument(
        "--yaml-dir",
        help="Directory containing YAML checks for AMF"
    )
    parser.add_argument(
        "-o", "--output-dir",
        help="Output directory in which to save compliance-checker results. "
             "Files are saved in this directory as "
             "'<netcdf filename>.cc-output'"
    )
    parser.add_argument(
        "-f", "--format",
        dest="output_format",
        help="Output format. This is forwarded to compliance-checker. See "
             "'compliance-checker --help' for the available formats. Note "
             "you must use 'json_new' instead of 'json' if checking multiple "
             "files"
    )
    parser.add_argument(
        "-v", "--version",
        dest="checks_version_number",
        help="This should be the version number of the checks you want to "
             "use. For example, \"2.0\" for v2.0."
    )
    args = parser.parse_args(sys.argv[1:])

    # Check yaml_dir exists
    if not args.yaml_dir or not os.path.isdir(args.yaml_dir):
        raise ValueError("Please include directory of YAML checks as argument: '--yaml-dir'.") 

    # Check for version number
    if not args.checks_version_number:
        raise ValueError("Please include the version number of the checks "
                         "you\'d like to use, eg. \'--version 2.0\'")

    files = []
    for fname in args.files:
        if os.path.isfile(fname):
            files.append(fname)
        elif os.path.isdir(fname):
            # If fname is a directory, check all files within it
            dir_contents = [os.path.join(fname, p) for p in os.listdir(fname)]
            files += filter(os.path.isfile, dir_contents)
        else:
            parser.error("cannot check `{}': no such file or directory"
                         .format(fname))

    if args.output_dir and not os.path.isdir(args.output_dir):
        os.mkdir(args.output_dir)

    # Group files by data product and deployment mode
    groups = {}
    for fname in files:
        try:
            product = get_product_from_filename(fname)
            mode = get_deployment_mode(fname)
        except ValueError as ex:
            print("WARNING: {}".format(ex), file=sys.stderr)
            continue

        key = (product, mode)
        if key not in groups:
            groups[key] = []
        groups[key].append(fname)

    if not groups:
        print("Nothing to do")
        sys.exit(0)

    for (product, mode), fnames in groups.items():
        yaml_check = "product_{prod}_{dep_m}".format(prod=product,
                                                     dep_m=mode.value.lower())
        cc_args = [
            "compliance-checker",
            "--yaml", os.path.join(args.yaml_dir, "AMF_{}.yml".format(yaml_check)),
            "--test", "{}_checks:{}".format(yaml_check,args.checks_version_number)
        ]

        if args.output_format:
            cc_args += ["--format", args.output_format]

        if args.output_dir:
            for fname in fnames:
                result_fname = "{}.cc-output".format(os.path.basename(fname))
                cc_args += ["--output", os.path.join(args.output_dir, result_fname)]

        cc_args += fnames
        subprocess.call(cc_args)


if __name__ == "__main__":
    main()
