"""
Most of this file is copied from quickstart.py at
https://developers.google.com/sheets/api/quickstart/python
"""
from __future__ import print_function
import os

import argparse
from oauth2client import client, tools
from oauth2client.file import Storage


this_dir = os.path.dirname(__file__)
CLIENT_SECRETS_DIR = os.path.join(this_dir, os.pardir, "client_secrets")


config = {
    "sheets": {
        # If modifying these scopes, delete your previously saved credentials
        # at ~/.credentials/sheets.googleapis.com-python-quickstart.json
        "scopes": "https://www.googleapis.com/auth/spreadsheets.readonly",
        "client_secret_file": os.path.join(CLIENT_SECRETS_DIR, "sheets.json"),
        "app_name": "Google Sheets API Python Quickstart"
    },
    "drive": {
        "scopes": "https://www.googleapis.com/auth/drive.metadata.readonly",
        "client_secret_file": os.path.join(CLIENT_SECRETS_DIR, "drive.json"),
        "app_name": "Google Drive API Python Quickstart"
    }
}


def get_credentials(api):
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    info = config[api]

    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   '{}.googleapis.com-python-quickstart.json'.format(api))

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(info["client_secret_file"], info["scopes"])
        flow.user_agent = info["app_name"]
        flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
        credentials = tools.run_flow(flow, store, flags)
        print('Storing credentials to ' + credential_path)
    return credentials
