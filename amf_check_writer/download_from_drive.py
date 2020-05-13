"""
Download spreadsheets from Google Drive and save each worksheet as a TSV
(tab separated values) file.

See the README in amf-check-writer for details.
"""
import os
import sys
import time
import argparse

import httplib2
from pygdrive3 import service

from apiclient import discovery
from apiclient import http


from amf_check_writer.credentials import get_credentials


# ID of the top level folder in Google Drive
ROOT_FOLDER_ID = "1TGsJBltDttqs6nsbUwopX5BL_q8AU-5X"
NROWS_TO_PARSE = 999

SPREADSHEET_MIME_TYPES = (
    "application/vnd.google-apps.spreadsheet"
)

FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"

FOLDERS_TO_SKIP = (
    "products under development",
    "TO_DELETE_SOON",
    "Archive_1"
)

ALLOWED_WORKSHEET_NAMES = (
    "creators",
    "data-products",
    "dimensions-air",
    "dimensions-land",
    "dimensions-sea",
    "dimensions-specific",
    "dimensions-trajectory",
    "file-naming",
    "global-attributes-specific",
    "global-attributes",
    "ncas-instrument-name-and-descriptors",
    "community-instrument-name-and-descriptors",
    "platforms",
    "variables-air",
    "variables-land",
    "variables-sea",
    "variables-specific",
    "variables-trajectory",
)
AWN = ALLOWED_WORKSHEET_NAMES



API_CALL_TIMES = []


def api_call(func):
    """
    Decorator for functions that make a call to one of Google's APIs. Used to
    avoid hitting rate limits
    """
    def inner(*args, **kwargs):
        # Rate limit is 'max_request' requests per 'min_time' seconds
        max_requests = 20
        min_time = 120

        now = time.time()

        # Trim API_CALL_TIMES to calls made recently
        if API_CALL_TIMES:
            while now - API_CALL_TIMES[0] > min_time:
                API_CALL_TIMES.pop(0)

        # If 100 or more then wait long enough to make this next request
        if len(API_CALL_TIMES) >= max_requests:
            n = min_time - now + API_CALL_TIMES[0] + 2 # Add 2s leeway...
            print("[WARNING] Waiting {} seconds to avoid reaching rate limit...".format(int(n)))
            time.sleep(n)

        API_CALL_TIMES.append(time.time())

        return func(*args, **kwargs)

    return inner


class SheetDownloader(object):
    """
    Class to handle dealing with Google's Sheets and Drive API and downloading
    spreadsheets
    """

    def __init__(self, out_dir, secrets_file=None):
        self.out_dir = os.path.join(out_dir, 'product-definitions')
        if not os.path.isdir(self.out_dir):
            os.mkdir(self.out_dir)

        self.secrets_file = secrets_file

        # Authenticate and get API handles
        drive_credentials = get_credentials("drive", secrets_file)
        drive_http = drive_credentials.authorize(httplib2.Http())
        self.drive_api = discovery.build("drive", "v3", http=drive_http)

        sheets_credentials = get_credentials("sheets", secrets_file)
        sheets_http = sheets_credentials.authorize(httplib2.Http())
        discovery_url = ("https://sheets.googleapis.com/$discovery/rest?version=v4")
        self.sheets_api = discovery.build("sheets", "v4", http=sheets_http,
                                          discoveryServiceUrl=discovery_url)

        # Also authenticate to separate downloder library for raw XLSX downloads
        drive_service = service.DriveService(self.secrets_file)
        drive_service.auth()
 
        self.drive_service = drive_service.drive_service

    def run(self):
        self.find_all_spreadsheets(self.save_spreadsheet_callback())

    @api_call
    def get_folder_children(self, folder_id):
        """
        Return a list of children of the Drive folder with the given ID
        """
        results = (self.drive_api.files().list(
            fields="files(id, name, mimeType)",
            q="'{}' in parents".format(folder_id)
        ).execute())
        return results.get("files", [])

    @api_call
    def get_spreadsheet(self, sheet_id):
        return self.sheets_api.spreadsheets().get(spreadsheetId=sheet_id).execute()

    @api_call
    def get_sheet_values(self, sheet_id, cell_range):
        results = self.sheets_api.spreadsheets().values().get(spreadsheetId=sheet_id,
                                                              range=cell_range).execute()
        return results.get("values", [])

    def find_all_spreadsheets(self, callback, root_id=ROOT_FOLDER_ID, folder_name=""):
        """
        Recursively search the drive folder with the given ID and call `callback`
        on each spreadsheet found. `callback` is called with args
        (spreadsheet name, spreadsheet ID, parent folder name).
        """
        for f in self.get_folder_children(root_id):
            if f["mimeType"] == FOLDER_MIME_TYPE:
                if f["name"] in FOLDERS_TO_SKIP:
                    print("[INFO] Skipping folder '{}'".format(f["name"]))
                    continue

                new_folder = os.path.join(folder_name, f["name"])
                # Make the recursive call if we have found a sub-folder
                self.find_all_spreadsheets(callback, root_id=f["id"], folder_name=new_folder)

            elif f["mimeType"] in SPREADSHEET_MIME_TYPES:
                # Process the spreadsheet
                callback(f["name"], f["id"], folder_name)

    def write_values_to_tsv(self, values, out_file):
        """
        Write a sheet to `out_file`. `values` is a list of lists representing a
        range in the sheet
        """
        with open(out_file, "w") as f:
            for row in values:
                f.write("\t".join([cell.strip().replace("\n", "|")
                                   for cell in row]))
                f.write(os.linesep)

    def download_all_sheets(self, sheet_id, sheet_name):
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

        print("[INFO] Saving {} sheets to {}...".format(len(results["sheets"]), self.out_dir))
        sheet_name_no_xlsx = sheet_name[:-5]
        
        # Validate sheet name
        if sheet_name_no_xlsx + '.xlsx' != sheet_name:
            raise Exception('Sheet does not have expected name with ".xlsx" extension: {}'.format(sheet_name))

        tsv_dir = os.path.join(self.out_dir, 'tsv', sheet_name_no_xlsx)
        spreadsheet_dir = os.path.join(self.out_dir, 'spreadsheet')
        
        for sdir in (tsv_dir, spreadsheet_dir):
            if not os.path.isdir(sdir):
                os.makedirs(sdir)

        print('[INFO] Saving TSV files to: {}...'.format(tsv_dir))
        for sheet in results["sheets"]:
            name = sheet["properties"]["title"]

            # Check worksheet name is valid
            if name not in AWN:
                print('[ERROR] Worksheet name not recognised: {}'.format(name))

            cell_range = "'{}'!A1:Z{}".format(name, NROWS_TO_PARSE)
            out_file = os.path.join(tsv_dir, "{}.tsv".format(name))
            self.write_values_to_tsv(self.get_sheet_values(sheet_id, cell_range), out_file)

        # Now download the raw spreadsheet 
        # spreadsheet_file = os.path.join(spreadsheet_dir, sheet_name)
        # print("[INFO] Saving spreadsheet to: {}...".format(spreadsheet_file))

        # request = self.drive_service.files().export_media(fileId=sheet_id,
        #       mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        # with open(spreadsheet_file, 'wb') as fh:
        #     downloader = http.MediaIoBaseDownload(fh, request)

        #     done = False
        #     while done is False:
        #         status, done = downloader.next_chunk()

    def save_spreadsheet_callback(self):
        """
        Return a callback function to pass to `find_all_spreadsheets` that downloads
        and saves sheets to a directory under `self.out_dir`.

        """
        def callback(name, sheet_id, parent_folder):

#            target_dir = os.path.join(self.out_dir, parent_folder, name)
#            if not os.path.isdir(target_dir):
#                os.makedirs(target_dir)

            self.download_all_sheets(sheet_id, name)

        return callback

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output_dir",
        help="Directory to write spreadsheets to"
    )
    parser.add_argument(
        "-s", "--secrets",
        help="Client secrets JSON file (see README for instructions on how to "
             "obtain this). Only required for first time use."
    )
    args = parser.parse_args(sys.argv[1:])
    downloader = SheetDownloader(args.output_dir, secrets_file=args.secrets)
    downloader.run()

if __name__ == "__main__":
    main()
