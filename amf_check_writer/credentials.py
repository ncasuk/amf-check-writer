"""
Most of this file is copied from quickstart.py at
https://developers.google.com/sheets/api/quickstart/python
"""
from __future__ import print_function
import os

import argparse
from oauth2client import client, tools
from oauth2client.file import Storage


APP_NAME = "amf-check-writer"

SCOPES = {
    # If modifying these scopes, delete your previously saved credentials
    # at ~/.credentials/sheets.googleapis.com-python-quickstart.json
    "sheets": "https://www.googleapis.com/auth/spreadsheets.readonly",
    "drive":  "https://www.googleapis.com/auth/drive.metadata.readonly"
}


def get_credentials(api, secrets_file=None):
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   '{}.googleapis.com-python-quickstart.json'.format(api))

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        if secrets_file is None:
            raise ValueError(
                "No valid credentials found in '{}' and secrets file not "
                "given. Please re-run with --secrets".format(credential_dir)
            )

        flow = client.flow_from_clientsecrets(secrets_file, SCOPES[api])
        flow.user_agent = APP_NAME
        flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args([
            "--noauth_local_webserver"
        ])
        credentials = tools.run_flow(flow, store, flags)
        print('Storing credentials to ' + credential_path)
    return credentials
