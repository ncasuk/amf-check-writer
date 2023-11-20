"""
Download spreadsheets from Google Drive and save each worksheet as a TSV
(tab separated values) file.

See the README in amf-check-writer for details.
"""
import os
import sys
import time
import argparse
from pathlib import Path

import httplib2

from apiclient import discovery
from apiclient import http


from amf_check_writer.credentials import get_credentials
from amf_check_writer.workflow_docs import read_workflow_data
from amf_check_writer.config import (
    CURRENT_VERSION,
    SHARED_DRIVE_ID,
    GENERAL_PRODUCTS_FOLDER_ID,
    VOCABS_FOLDER_ID,
    PRODUCT_COUNT_MINIMUM,
    ALL_VERSIONS,
    ALL_VOCABS,
    NROWS_TO_PARSE,
)


SPREADSHEET_MIME_TYPES = "application/vnd.google-apps.spreadsheet"

FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"

FOLDERS_TO_SKIP = ("products under development", "TO_DELETE_SOON", "Archive_1")

API_CALL_TIMES = []

# Load information about which spreadsheets/worksheets are expected
workflow_data = {k: v for k, v in read_workflow_data()["google_drive_content"].items()}
ALLOWED_WORKSHEET_NAMES = {
    worksheet.strip("*")
    for section in ["_common.xlsx", "_vocabularies.xlsx", "_instrument_vocabs.xlsx", "per-product"]
    for worksheet in workflow_data[section]
}


def api_call(func):
    """
    Decorator for functions that make a call to one of Google's APIs. Used to
    avoid hitting rate limits
    """

    def inner(*args, **kwargs):
        # Rate limit is 'max_request' requests per 'min_time' seconds
        max_requests = 30
        min_time = 120

        now = time.time()

        # Trim API_CALL_TIMES to calls made recently
        if API_CALL_TIMES:
            while now - API_CALL_TIMES[0] > min_time:
                API_CALL_TIMES.pop(0)

        # If 100 or more then wait long enough to make this next request
        if len(API_CALL_TIMES) >= max_requests:
            n = min_time - now + API_CALL_TIMES[0] + 2  # Add 2s leeway...
            print(
                "[WARNING] Waiting {} seconds to avoid reaching rate limit...".format(
                    int(n)
                )
            )
            time.sleep(n)

        API_CALL_TIMES.append(time.time())

        return func(*args, **kwargs)

    return inner


class SheetDownloader(object):
    """
    Class to handle dealing with Google's Sheets and Drive API and downloading
    spreadsheets
    """

    def __init__(self, out_dir, version = None, vocab = None, secrets_file=None, regenerate=False):
        self.version = version
        self.vocab = vocab
        self.out_dir = out_dir
        self.vocab_out_dir = os.path.join(out_dir, "vocabs")

        if self.version and not os.path.isdir(self.out_dir):
            os.makedirs(self.out_dir)
        if self.vocab and not os.path.isdir(self.vocab_out_dir):
            os.makedirs(self.vocab_out_dir)

        self.secrets_file = secrets_file
        self.regenerate = regenerate

        # Authenticate and get API handles
        drive_credentials = get_credentials("drive", secrets_file)
        self.drive_api = discovery.build("drive", "v3", credentials=drive_credentials)

        sheets_credentials = get_credentials("sheets", secrets_file)
        discovery_url = "https://sheets.googleapis.com/$discovery/rest?version=v4"
        self.sheets_api = discovery.build(
            "sheets",
            "v4",
            credentials=drive_credentials,
            discoveryServiceUrl=discovery_url,
        )

        # # Also authenticate to separate downloder library for raw XLSX downloads
        # # This isn't currently working, so using the above API handle.
        # drive_service = service.DriveService(self.secrets_file)
        # drive_service.auth()

        # self.drive_service = drive_service.drive_service

    def run(self):
        if self.version:
            self.find_all_spreadsheets(self.save_spreadsheet_callback(), root_id=GENERAL_PRODUCTS_FOLDER_ID, folder_name=self.out_dir)
        if self.vocab:
            self.find_all_spreadsheets(self.save_spreadsheet_callback(), root_id=VOCABS_FOLDER_ID, folder_name=self.vocab_out_dir)

    @api_call
    def get_folder_children(self, shared_drive_id, folder_id):
        """
        Return a list of children of the Drive folder with the given ID
        """
        results = (
            self.drive_api.files()
            .list(
                fields="files(id, name, mimeType)",
                corpora="drive",
                driveId=shared_drive_id,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                q="'{}' in parents".format(folder_id),
            )
            .execute()
        )
        return results.get("files", [])

    @api_call
    def get_spreadsheet(self, sheet_id):
        return self.sheets_api.spreadsheets().get(spreadsheetId=sheet_id).execute()

    @api_call
    def get_sheet_values(self, sheet_id, cell_range):
        results = (
            self.sheets_api.spreadsheets()
            .values()
            .get(spreadsheetId=sheet_id, range=cell_range)
            .execute()
        )
        return results.get("values", [])

    @api_call
    def save_raw_spreadsheet(self, sheet_id, spreadsheet_file):
        request = self.drive_api.files().export_media(
            fileId=sheet_id,
            mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        with open(spreadsheet_file, "wb") as fh:
            downloader = http.MediaIoBaseDownload(fh, request)

            done = False
            while done is False:
                status, done = downloader.next_chunk()

    def find_all_spreadsheets(
        self,
        callback,
        shared_drive_id=SHARED_DRIVE_ID,
        root_id=VOCABS_FOLDER_ID,
        folder_name="",
    ):
        """
        Recursively search the drive folder with the given ID and call `callback`
        on each spreadsheet found. `callback` is called with args
        (spreadsheet name, spreadsheet ID, parent folder name).
        """
        fnames = []

        for f in self.get_folder_children(shared_drive_id, root_id):
            fname = f["name"]
            fnames.append(fname)

            if f["mimeType"] == FOLDER_MIME_TYPE:
                if fname in FOLDERS_TO_SKIP:
                    print(f"[INFO] Skipping folder '{fname}'")
                    continue

                if (self.version and fname in self.version) or (self.vocab and fname in self.vocab):
                    print(f"[INFO] Found and using '{fname}'")
                else:
                    print(
                        f"[INFO] Skipping folder with '{fname}' as we want version '{self.version}' or vocab '{self.vocab}'"
                    )
                    continue

                new_folder = os.path.join(folder_name, fname)

                # Make the recursive call if we have found a sub-folder
                self.find_all_spreadsheets(
                    callback, root_id=f["id"], folder_name=new_folder
                )

            elif f["mimeType"] in SPREADSHEET_MIME_TYPES:
                # Process the spreadsheet
                callback(fname, f["id"], folder_name)

        """
        # Check valid content was found
        if len([item for item in fnames if item.endswith(".xlsx")]) > 5:
            expected_xlsx = {xlsx for xlsx in workflow_data if xlsx.endswith(".xlsx")}
            if not expected_xlsx.issubset(set(fnames)):
                diff = expected_xlsx.difference(fnames)
                print( 'ValueError('
                    f"[ERROR] The following expected spreadsheets were not found on "
                    f"Google Drive: {diff}"
                ')')

            if len(fnames) < PRODUCT_COUNT_MINIMUM:
                raise Exception(
                    f"[ERROR] The number of product spreadsheets found is less than "
                    f"the minimum expected: {len(fnames)} < {PRODUCT_COUNT_MINIMUM}."
                    f" Please investigate."
                )
        """

    def write_values_to_tsv(self, values, out_file):
        """
        Write a sheet to `out_file`. `values` is a list of lists representing a
        range in the sheet
        """
        with open(out_file, "w") as f:
            for row in values:
                f.write(
                    "\t".join(
                        [
                            cell.strip().replace("\n", "|").replace("\r", "")
                            for cell in row
                        ]
                    )
                )
                f.write(os.linesep)

    def download_all_sheets(self, sheet_id, sheet_name, parent_folder):
        """
        Download each sheet of a spreadsheet as a TSV file and save them to an
        output directory.

        Also download the raw spreadsheet and save that

        Spreadsheets are saved in two formats in the following structure:

            .../product-definitions/tsv/<spreadsheet_name>/*.tsv - tab-delimited files
            .../product-definitions/spreadsheet/<spreadsheet_name>.xlsx - XLSX file

        """
        # Get spreadsheet as a whole and iterate through each sheet
        results = self.get_spreadsheet(sheet_id)

        print(
            "[INFO] Saving {} sheets to {}...".format(
                len(results["sheets"]), self.out_dir
            )
        )
        sheet_name_no_xlsx = sheet_name[:-5]

        # Validate sheet name
        if sheet_name_no_xlsx + ".xlsx" != sheet_name:
            raise Exception(
                f"[ERROR] Sheet does not have expected name with '.xlsx' extension: {sheet_name}"
            )

        prod_def_dir = os.path.join(parent_folder, "product-definitions")
        tsv_dir = os.path.join(prod_def_dir, "tsv", sheet_name_no_xlsx)
        spreadsheet_dir = os.path.join(prod_def_dir, "spreadsheet")

        for sdir in (tsv_dir, spreadsheet_dir):
            if not os.path.isdir(sdir):
                os.makedirs(sdir)

        print("[INFO] Saving TSV files to: {}...".format(tsv_dir))
        worksheets = set()

        for sheet in results["sheets"]:
            name = sheet["properties"]["title"]
            worksheets.add(name)

            # Check worksheet name is valid
            if name not in ALLOWED_WORKSHEET_NAMES:
                print("[ERROR] Worksheet name not recognised: {}".format(name))

            cell_range = "'{}'!A1:Z{}".format(name, NROWS_TO_PARSE)
            out_file = os.path.join(tsv_dir, "{}.tsv".format(name))

            if os.path.isfile(out_file) and not self.regenerate:
                print(
                    f"[WARNING] Not regenerating TSV...file already exists: {out_file}"
                )
            else:
                self.write_values_to_tsv(
                    self.get_sheet_values(sheet_id, cell_range), out_file
                )

        # Check the expected worksheet files were processed
        # For general (relating to all products) spreadsheets
        if sheet_name.startswith("_"):
            if not set(workflow_data[sheet_name]) == worksheets:
                raise Exception(
                    f"[ERROR] Could not find/process all expected worksheets for "
                    f"spreadsheet '{sheet_name}'. Difference is:\n"
                    f"\tExpected: {sorted(workflow_data[sheet_name])}\n"
                    f"\tFound:    {sorted(worksheets)}"
                )

        # For product-specific spreadsheets
        else:
            required = {
                wsheet for wsheet in workflow_data["per-product"] if "*" not in wsheet
            }

            if not required.issubset(worksheets):
                raise Exception(
                    f"[ERROR] Could not find/process product-specific worksheets "
                    f"for '{sheet_name}'. Missing: {required.difference(worksheets)}"
                )

        # Now download the raw spreadsheet
        spreadsheet_file = os.path.join(spreadsheet_dir, sheet_name)

        if os.path.isfile(spreadsheet_file) and not self.regenerate:
            print(
                f"[WARNING] Download not initiated...file already exists: {spreadsheet_file}"
            )
            return
        else:
            print(f"[INFO] Saving spreadsheet to: {spreadsheet_file}...")
            self.save_raw_spreadsheet(sheet_id, spreadsheet_file)

    def save_spreadsheet_callback(self):
        """
        Return a callback function to pass to `find_all_spreadsheets` that downloads
        and saves sheets to a directory under `self.out_dir`.

        """

        def callback(name, sheet_id, parent_folder):
            self.download_all_sheets(sheet_id, name, parent_folder)

        return callback


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", help="Directory to write spreadsheets to")

    parser.add_argument(
        "-s",
        "--secrets",
        help="Client secrets JSON file (see README for instructions on how to "
        "obtain this). Only required for first time use.",
    )

    parser.add_argument(
        "-v",
        "--version",
        choices=ALL_VERSIONS,
        help=f"Version of the NCAS-GENERAL spreadsheets to use (e.g. '{CURRENT_VERSION}').",
        default = None,
    )

    parser.add_argument(
        "-c",
        "--vocab",
        choices = ALL_VOCABS,
        help = "Specific vocabulary to download",
        default = None,
    )

    parser.add_argument(
        "--regenerate",
        dest="regenerate",
        action="store_true",
        help="Force download and re-generation of files that already exist on "
        "the file system. Default is to always re-generate files.",
    )
    parser.add_argument("--no-regenerate", dest="regenerate", action="store_false")

    args = parser.parse_args(sys.argv[1:])

    if not args.version and not args.vocab:
        msg = "At least one of -v/--version and -c/--vocab must be specified"
        raise ValueError(msg)
    
    downloader = SheetDownloader(
        args.output_dir,
        version = args.version,
        vocab = args.vocab,
        secrets_file=args.secrets,
        regenerate=args.regenerate,
    )
    downloader.run()


if __name__ == "__main__":
    main()
