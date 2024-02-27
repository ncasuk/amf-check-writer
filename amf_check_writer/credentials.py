"""
Most of this file is copied from quickstart.py at
https://developers.google.com/sheets/api/quickstart/python
"""
from __future__ import print_function
import os

import argparse
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


APP_NAME = "amf-check-writer"

SCOPES = {
    # If modifying these scopes, delete your previously saved credentials
    # at ~/.credentials/sheets.googleapis.com-python-quickstart.json
    "sheets": "https://www.googleapis.com/auth/spreadsheets.readonly",
    "drive": "https://www.googleapis.com/auth/drive.readonly",
}


def get_credentials(api, secrets_file=None):
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    credentials = None
    home_dir = os.path.expanduser("~")
    credential_dir = os.path.join(home_dir, ".credentials")
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(
        credential_dir, "{}.googleapis.com-python-quickstart.json".format(api)
    )

    if os.path.exists(credential_path):
        credentials = Credentials.from_authorized_user_file(credential_path)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        elif secrets_file is None:
            raise ValueError(
                "No valid credentials found in '{}' and secrets file not "
                "given. Please re-run with --secrets".format(credential_dir)
            )
        else:
            flow = InstalledAppFlow.from_client_secrets_file(secrets_file, SCOPES[api])
            credentials = flow.run_local_server()
            with open(credential_path, "w") as token:
                token.write(credentials.to_json())
            print("Storing credentials to " + credential_path)
    return credentials
