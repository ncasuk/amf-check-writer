# ncas-amf-check-writer

This repo contains scripts to generate python checks suites for `compliance-checker`
based on specifications for AMF data in spreadsheets in Google Drive.

The `compliance-checker` plugin resulting from this work can be obtained
here: https://github.com/joesingo/cc-plugin-amf. Note that you still need to
install the JSON controlled vocabulary files with `pyessv`, so most of the steps
listed below are still required.

## Setup ##

```bash
# Create an activate a python 3 virtual environment
python3 -m venv venv
source venv/bin/activate

# Get various repos
git clone https://github.com/ncasuk/ncas-amf-compliance-checker
git clone https://github.com/cedadev/compliance-check-maker
git clone -b amf https://github.com/joesingo/compliance-check-lib  # Note: clone 'amf' branch
git clone https://github.com/joesingo/pyessv-writer-amf

# Install requirements
pip install -r ncas-amf-compliance-checker/requirements.txt
pip install -r pyessv-writer-amf/requirements.txt
pip install -e ./compliance-check-lib
pip install -e ./compliance-check-maker
pip install compliance-checker

# Run scripts - see sections below for details on each
cd ncas-amf-compliance-checker/ncas-amf-compliance-checker
python download_from_drive.py /tmp/spreadsheets
mkdir /tmp/cvs
python create_controlled_vocabs.py /tmp/spreadsheets /tmp/cvs

# Set up compliance-check-maker - SKIP THIS IF USING cc-plugin-amf and
# continue at ***
cd ../../compliance-check-maker
# Clear out old YAMl checks, but keep PROJECT_METADATA.yml
mv project/amf/PROJECT_METADATA.yml /tmp
rm project/amf/*.yml
mv /tmp/PROJECT_METADATA.yml project/amf

cd ../ncas-amf-compliance-checker/ncas-amf-compliance-checker
python create_yaml_checks.py /tmp/cvs ../../compliance-check-maker/project/amf

cd ../../compliance-check-maker
python write_checkers.py amf

# Python checks are now available at ouput/amf/py/AMF_*.py to make them
# available to compliance-checker they need to installed as part of a plugin -
# take cc-plugin-amf as an example and update the files in there. See the
# README.md in that repo to avoid writing list of checks out by hand...

# ***
# Now cache JSON CVs generated earlier so they can be used by compliance-check-lib
cd ../pyessv-writer-amf/sh
mkdir -p ~/.esdoc/pyessv-archive
python write_amf_cvs.py --source /tmp/cvs

# If everything worked okay - run a check! e.g.
cchecker.py --test amf-o2n2_concentration_ratio_variable /path/to/netcdf/file.nc
```

## Scripts ##

### download_from_drive.py ###

Usage: `python download_from_drive.py <output directory>`.

This script recursively finds all spreadsheets under a folder in Google Drive
and save sheets from each as a .tsv file (the root folder ID is hardcoded in
`ncas-amf-compliance-checker/download_from_drive.py`).

The directory structure of the Drive folder is preserved, and a directory for
each spreadsheet is created. The individual sheets are saved as
`<sheet name>.tsv` inside the spreadsheet directory.

For example, after running `python download_from_drive.py /tmp/mysheets` with
a test folder:

```
$ tree /tmp/mysheets
/tmp/mysheets
├── first-spreadsheet.xlsx
│   ├── Sheet1.tsv
│   └── Sheet2.tsv
└── sub-folder
    ├── second-spreadsheet.xlsx
    │   └── Sheet1.tsv
    └── sub-sub-dir
        └── other-spreadsheet.xlsx
            └── my-sheet.tsv

5 directories, 4 files
```

#### Authentication ####

Follow the instructions on the Google site to get credentials for the Sheets
and Drive APIs:

https://developers.google.com/sheets/api/quickstart/python

https://developers.google.com/drive/v3/web/quickstart/python

Put the downloaded `client_secret.json` files at `client_secrets/sheets.json`
and `client_secrets/drive.json`.

When running the script for the first time a web browser will be opened for you
to verify access to your Google account. To avoid this run the script as
`python downloaded <out dir> --noauth_local_webserver` - you will then need to
visit a webpage and enter a verification code (the order of arguments is
important here).

### create_controlled_vocabs.py ###

Usage: `python create_controlled_vocabs.py <input dir> <output dir>`.

This scripts takes a directory containing .tsv files downloaded with
`download_from_drive.py`, finds those that describe specifications for
attributes in variables, and converts them to a JSON format.

JSON files are saved in `<output_dir>` as `amd_<product name>_<type>_variable>.json`,
but `<type>` is omitted if not present. Examples include `AMF_common_air_variable.json`,
`AMF_common_sea_variable.json`, `AMF_sonde_variable.json` (`sonde` is product name, type is
not present).

The format is

```json
{
    "variable": {
        "<var name>": {
            "<attr>": "<value>",
            ...
        },
        ...
    }
}
```

All values are strings except when attribute is `valid_min` or `valid_max` in
which case it is a float.

This is mostly all copied from Ag's previous work:
https://github.com/agstephens/AMF_CVs/blob/a87dd06eee27a6cf517a6f5346df6f07468d1120/scripts/write_variables_json.py

### create_yaml_checks.py ###

Usage: `python create_yaml_checks.py <input dir> <output dir>`.

This script reads JSON controlled vocabulary files generated by `create_controlled_vocabs.py`
and writes YAML files that can be used to generate compliance checker suites with
`compliance-check-maker`.

It is important that the file names in `<input dir>` match the format of those produced by
`create_controlled_vocabs.py`. The files generated in `<output_dir>` are named the same as
the input files but with extension `.yml` instead of `.json`.
