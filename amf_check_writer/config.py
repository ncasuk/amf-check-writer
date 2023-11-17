import os
import site

# ID of the top level folder in Google Drive
SHARED_DRIVE_ID = "0AEZ8wCGEWktfUk9PVA"
GENERAL_PRODUCTS_FOLDER_ID = "1TGsJBltDttqs6nsbUwopX5BL_q8AU-5X"
CURRENT_VERSION = "v2.0"
NROWS_TO_PARSE = 999
PRODUCT_COUNT_MINIMUM = 50

ALL_VERSIONS = (
    "v1.0", "v1.1", "v2.0"
)


site_packages_dir = (site.getsitepackages() or ["."])[0]
DEFAULT_AMF_CHECKS_DIR = os.path.join(site_packages_dir, "amf-checks")

