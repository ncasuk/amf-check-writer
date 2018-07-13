# amf-check-writer

**TODO:**

provisional installation instructions:

---

This repo contains scripts to:

* Download spreadsheets containing specifications for AMF data products from a
  folder in Google Drive

* Generate check suites for the [IOOS compliance
  checker](https://github.com/ioos/compliance-checker) based on the contents of
  the spreadsheets

* Generate controlled vocabulary files from the spreadsheets

The checks are generated in YAML format for use with the
[cc-yaml](https://github.com/joesingo/cc-yaml) plugin for compliance-checker.
The code for the checks themselves is implemented in
[compliance-check-lib](https://github.com/cedadev/compliance-check-lib).

## Quickstart

(**TODO:** come up with correct and up-to-date instructions for installing
dependencies. Possibly use: install JAP, and then `yum install python27-netCDF4
python27-iris python27-cf python27-virtualenv python27-cf_units`)

```bash
# Create an activate a python 2.7 virtual environment
virtualenv -p python2.7 venv
source venv/bin/activate

# Install dependencies
...

# Download spreadsheets. See 'authentication' section below for first time usage
download-from-drive /tmp/spreadsheets

# Create controlled vocabulary files from spreadsheets
create-cvs /tmp/spreadsheets /tmp/cvs

# Create YAML checks from spreadsheets
create-yaml-checks /tmp/spreadsheets /tmp/yaml

# Run a check; e.g:
compliance-checker --yaml /tmp/yaml/AMF_product_radiation_land.yml \
                   --test product_radiation_land_checks \
                   /path/to/dataset.nc
```

See below for more details on the scripts called above.

## Scripts

### download-from-drive

Usage: `download-from-drive <output dir>`.

This script recursively finds all spreadsheets under a folder in Google Drive
and saves each worksheet as a .tsv file (the root folder ID is hardcoded in
`amf_check_writer/download-from-drive.py`).

The directory structure of the Drive folder is preserved, and a directory for
each spreadsheet is created. The individual sheets are saved as
`<sheet name>.tsv` inside the spreadsheet directory.

For example, after running `download-from-drive /tmp/mysheets` with
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

#### Authentication

Downloding spreadsheets from Google Drive requires the script to authenticate
as your Google account. This is done using a JSON file obtained from the
Google API dashboard.

* Visit https://console.developers.google.com/apis/dashboard

* Select a project from the dropdown in the heaader bar, or create a new
  project (blue button named 'Create project')

* Click the 'Enable APIs and Services' button in the header bar

* Search for 'Google Drive API'. Click the result and press 'Enable'. Return to
  the dashboard and do the same for 'Google Sheets API'

* Return to the dashboard and click 'Credentials' in the sidebar on the left
  (key icon)

* Click 'Create credentials' and select 'OAuth client ID'. Select 'Other' for
  application type and follow the prompts. Dismiss the popup that appears.

* You should see the newly created credentials in the table. On the right hand
  side of the table there is a download icon ('Download JSON'). Click it and
  save the JSON file to `client_secrets/client_secret.json` in this repo.

* When running `download-from-drive` for the first time a web browser will be
  opened for you to verify access to your Google account. To avoid this run the
  script as `download-from-drive <out dir> --noauth_local_webserver` - you will
  then need to visit a webpage and enter a verification code. Note that the
  order of arguments is important here.

Alternatively follow the quickstart guide on the Google sheets site to enable
the sheets API and create credentials (this also allows you to create a new
project):

https://developers.google.com/sheets/api/quickstart/python

After this visit the API dashboard to enable the Drive API, as detailed above.
You do not need to create another credentials JSON file.

### create-cvs

Usage: `create-cvs [--pyessv-dir <pyessv root>] <spreadsheets dir> <output dir>`.

This script reads .tsv files downloaded with `download-from-drive`, and
generates controlled vocabularies in JSON format from various worksheets. Each
file is saved in `<output dir>` as `AMF_<name>.json`.

CVs are created for:

* List of instruments and their names and descriptions
* List of platforms
* List of data products
* List of creators (`AMF_scientist.json`)
* Variable names and expected attributes (and values) for each data product
* Dimension names and expected attributes (and values) for each data product
* Variable/dimension names and attributes common to all data products
  (`AMF_product_common_{variable,dimension}_{air,land,sea}.json`)

The format of the CVs is specific to each type.

Each CV is also saved with [pyessv](https://github.com/ES-DOC/pyessv) and
written to pyessv's archive directory. The directory can be overridden with the
`--pyessv-dir` option.

### create-yaml-checks

Usage: `create-yaml-checks <spreadsheets dir> <output dir>`.

This script reads .tsv files and produces YAML checks to be used with
[cc-yaml](https://github.com/joesingo/cc-yaml) and
[compliance-check-lib](https://github.com/cedadev/compliance-check-lib).

Similar to `create-cvs`, checks are saved in `<output dir>` as `AMF_name.yml`.
Checks are created for:

* Variable/dimension specifications (common and per-product)
* Global attribute checks
* File info (name, size etc...) and file structure

For each data product/deployment mode combination, a check
`AMF_product_<name>_<mode>.yml` is created that includes global checks and the relevant
variable/dimensions checks for the product and mode. e.g.:

`AMF_product_soil_land.yml`:
```yaml
suite_name: product_soil_land_checks
checks:
# Global checks
- {__INCLUDE__: AMF_file_info.yml}
- {__INCLUDE__: AMF_file_structure.yml}
- {__INCLUDE__: AMF_global_attrs.yml}
# Common checks for 'land' deployment mode
- {__INCLUDE__: AMF_product_common_dimension_land.yml}
- {__INCLUDE__: AMF_product_common_variable_land.yml}
# Product specific
- {__INCLUDE__: AMF_product_soil_dimension.yml}
- {__INCLUDE__: AMF_product_soil_variable.yml}
```

### amf-checker

Usage: `amf-checker [--yaml-dir <yaml dir>] [-o <output dir>] [-f <output format>] <dataset>...`

Wrapper script around compliance-checker to automatically find and run the
relevant YAML checks for AMF datasets. See `--help` output for detailed help on
the meaning of the available options.

`<dataset>` can be either the path to a NetCDF file or a directory, in which
case all files in the directory are checked. Multiple files/directories can be
given, so shell globs can be used: e.g.

```bash
amf-checker /path/to/data/*.nc
```

## Testing

There are tests -- run using:

```
pytest amf_check_writer/tests.py
```
