from amf_check_writer.amf_checker import (FILENAME_REGEX, 
        get_product_from_filename, get_deployment_mode)


import re
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


def test_FILENAME_REGEX_success():

    extras = ["", "opt1_", "opt1_opt2_", "opt1_opt2_opt3_"]
    suffixes = ["v1.nc", "v1.1.nc"]

    prefixes = [
        "instr_plat_1999_prod_",
        "instr_plat_199901_prod_",
        "instr_plat_19990101_prod_",
        "instr_plat_19990101-01_prod_",
        "instr_plat_19990101-0101_prod_",
        "instr_plat_19990101-010101_prod_"
    ]

    for extra in extras:
        for suffix in suffixes:
            for prefix in prefixes:
                fname = prefix + extra + suffix
                assert FILENAME_REGEX.match(fname), f"Did not match: {fname}" 


def test_FILENAME_REGEX_failures():

    extras = ["", "opt1_", "opt1_opt2_", "opt1_opt2_opt3_"]
    suffixes = ["v1.nc", "v1.1.nc", "v1.2.0.nc"]

    prefixes = [
        "instr_plat_19991_prod_",
        "instr_plat_1999_01_prod_",
        "instr_plat_1999010_prod_",
        "instr_plat_19990101-0_prod_",
        "instr_plat_19990101-010_prod_",
        "instr_plat_19990101-01010_prod_"
        "instr_plat_19990101-01010434_prod_"
    ]

    for prefix in prefixes:
        fname = prefix + "" + "v1.nc"
        assert FILENAME_REGEX.match(fname) == None, f"Should not match - but did! {fname}"

    prefix = "instr_plat_19990101_prod_"
    suffixes = ["1.nc", "v1.0..nc", "v1.0.0.nc", "v1.csv"]
    for suffix in suffixes:
        fname = prefix + suffix
        assert FILENAME_REGEX.match(fname) == None, f"Should not match - but did! {fname}" 


def test_get_product_from_filename():
    #fname = os.path.basename(path)
    match = FILENAME_REGEX.match(fname)
    if not match:
        raise ValueError(
            "Filename '{}' does not match expected format '{}'"
            .format(fname, FILENAME_FORMAT_HUMAN_READABLE)
        )
    return match.group("product")


def test_get_deployment_mode():
    #d = Dataset(path)
   
    try:
        mode_str = d.deployment_mode
    except AttributeError:
        raise ValueError("Attribute 'deployment_mode' not found in '{}'".format(fname))

    for mode in DeploymentModes:
        if mode.value.lower() == mode_str:
            return mode

