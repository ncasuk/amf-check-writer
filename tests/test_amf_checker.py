from amf_check_writer.amf_checker import (FILENAME_REGEX, 
        get_product_from_filename, get_deployment_mode)


def _get_good_filenames():
    
    fnames = []
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
                fnames.append(prefix + extra + suffix)

    return fnames


def test_FILENAME_REGEX_success():
    fnames = _get_good_filenames()
    for fname in fnames:
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
    fnames = _get_good_filenames()

    for fname in fnames:
        prod = get_product_from_filename(fname)
        assert prod == "prod", f"Did not match product in: {fname}"


def test_get_deployment_mode():
    # Not written yet - need to find inside files
    pass
