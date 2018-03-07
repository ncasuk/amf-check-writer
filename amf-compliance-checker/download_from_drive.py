import os
import sys
import httplib2

from apiclient import discovery

from credentials import get_credentials


# ID of the top level folder in Google Drive
ROOT_FOLDER_ID = "1TGsJBltDttqs6nsbUwopX5BL_q8AU-5X"


SPREADSHEET_MIME_TYPES = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.google-apps.spreadsheet"
)


FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"


def find_all_spreadsheets(callback, root_id=ROOT_FOLDER_ID, folder_name=""):
    """
    Recursively search the drive folder with the given ID and call `callback`
    on each spreadsheet found. `callback` is called with args
    (spreadsheet name, spreadsheet ID, parent folder name)
    """
    credentials = get_credentials("drive")
    http = credentials.authorize(httplib2.Http())
    service = discovery.build("drive", "v3", http=http)

    results = service.files().list(fields="files(id, name, mimeType)",
                                   q="'{}' in parents".format(root_id)).execute()

    files = results.get("files", [])
    for f in files:
        if f["mimeType"] == FOLDER_MIME_TYPE:
            new_folder = os.path.join(folder_name, f["name"])
            # Make the recursive call if we have found a sub-folder
            find_all_spreadsheets(callback, root_id=f["id"], folder_name=new_folder)

        elif f["mimeType"] in SPREADSHEET_MIME_TYPES:
            # Process the spreadsheet
            callback(f["name"], f["id"], folder_name)


def write_values_to_tsv(values, out_file):
    """
    Write a sheet to `out_file`. `values` is a list of lists representing a
    range in the sheet
    """
    with open(out_file, "w") as f:
        for row in values:
            f.write("\t".join([cell.strip().encode("utf-8") for cell in row]))
            f.write(os.linesep)


def download_all_sheets(sheet_id, out_dir):
    """
    Download each sheet of a spreadsheet as a TSV file and save them in the given
    output directory
    """
    credentials = get_credentials("sheets")
    http = credentials.authorize(httplib2.Http())
    discoveryUrl = ("https://sheets.googleapis.com/$discovery/rest?version=v4")
    service = discovery.build("sheets", "v4", http=http, discoveryServiceUrl=discoveryUrl)

    # Get spreadsheet as a whole and iterate through each sheet
    results = service.spreadsheets().get(spreadsheetId=sheet_id).execute()

    print("Saving {} sheets to {}...".format(len(results["sheets"]), out_dir))
    for sheet in results["sheets"]:
        name = sheet["properties"]["title"]

        # Get cell values
        cell_range = "'{}'!A1:Z200".format(name)
        values_result = (service.spreadsheets().values()
                        .get(spreadsheetId=sheet_id, range=cell_range).execute())

        values = values_result.get("values", [])
        out_file = os.path.join(out_dir, "{}.tsv".format(name))
        write_values_to_tsv(values, out_file)


def save_spreadsheet_callback(out_dir):
    """
    Return a callback function to pass to `find_all_spreadsheets` that downloads
    and saves sheets to a directory under `out_dir`
    """
    def callback(name, sheet_id, parent_folder):
        target_dir = os.path.join(out_dir, parent_folder, name)
        if not os.path.isdir(target_dir):
            os.makedirs(target_dir)

        download_all_sheets(sheet_id, target_dir)

    return callback

if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage = "Usage: {} OUTPUT_DIR".format(sys.argv[0])
        sys.stderr.write(usage + os.linesep)
        sys.exit(1)

    # pop from argv to not get in the way of Google's argparser
    out_dir = sys.argv.pop(1)
    find_all_spreadsheets(save_spreadsheet_callback(out_dir))
