import os
from datetime import datetime


class PyessvWriter(object):

    def __init__(self, pyessv_root=None):
        if pyessv_root:
            os.environ["PYESSV_ARCHIVE_HOME"] = pyessv_root

        # Not normally good to import modules anywhere except top of the file,
        # but pyessv loads archive directory from an environment variable when
        # the module is imported. This means we cannot change the archive
        # directory from the code unless it is imported afterwards...
        #
        # This also prevents cluttering output with pyessv's logs even when CVs
        # are not being generated
        import pyessv
        self._pyessv = pyessv

        self.create_date = datetime(year=2018, month=7, day=9, hour=13,
                                    minute=9)

        self.authority = pyessv.create_authority(
            "NCAS",
            "NCAS Atmospheric Measurement Facility CVs",
            label="NCAS",
            url="https://www.ncas.ac.uk/en/about-amf",
            create_date=self.create_date
        )

        self.scope_amf = pyessv.create_scope(
            self.authority,
            "AMF",
            "Controlled Vocabularies (CVs) for use in AMF",
            label="AMF",
            url="https://github.com/ncasuk/AMF_CVs",
            create_date=self.create_date
        )

        # Make sure to include '@' for email addresses
        self.term_regex = r"^[a-z0-9\-@\.]*$"

    def write_cvs(self, cvs):
        print("[INFO] Writing to pyessv archive...")
        for cv in cvs:

            print(f"[INFO] Working on: {cv.namespace}")
            collection = self._pyessv.create_collection(
                self.scope_amf,
                cv.namespace,
                "NCAS AMF CV collection: {}".format(cv.namespace),
                create_date=self.create_date,
                term_regex=self.term_regex
            )

            # Note: This relies on the namespace being a top level key in CV
            # dictionary
            inner_cv = cv.cv_dict[cv.namespace]
            # If inner_cv is a dict then use keys for term names and values for
            # 'data' attribute. Otherwise (e.g. inner_cv is a list), ommit data
            # attribute
            for name in inner_cv:
                kwargs = {}
                if isinstance(inner_cv, dict):
                    kwargs["data"] = inner_cv[name]

                self._pyessv.create_term(collection, name=name, label=name,
                                         create_date=self.create_date,
                                         **kwargs)
            self._pyessv.archive(self.authority)

