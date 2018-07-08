import json
from csv import DictReader

import yaml


class BaseCV(object):
    """
    Base class for a controlled vocabulary instance
    """

    # Character to separate facets in namespace and filenames
    facet_separator = "_"

    def __init__(self, tsv_file, facets):
        """
        :param tsv_file: file object for the input TSV file
        :param facets:   list of facets to give this CV a unique name and
                         pyessv namespace
        """
        self.tsv_file = tsv_file
        self.namespace = self.facet_separator.join(facets)

        reader = StripWhitespaceReader(self.tsv_file, delimiter="\t")
        self.cv_dict = self.parse_tsv(reader)

    def to_json(self):
        """
        Return JSON representation of this CV as a string
        """
        return json.dumps(self.cv_dict, indent=4)

    def get_filename(self, ext):
        return "AMF{sep}{ns}.{ext}".format(sep=self.facet_separator,
                                           ns=self.namespace,
                                           ext=ext)

    def parse_tsv(self, reader):
        """
        Convert the TSV file to a dictionary in the controlled vocab format.
        Must be implemented in child classes.

        :param reader: StripWhitespaceReader instance for the TSV file
        :return:       dict containing data in JSON controlled vocab format
        """
        raise NotImplementedError


class StripWhitespaceReader(DictReader):
    """
    Subclasss of DictReader that automatically strips whitespace from cell
    and header values
    """
    def next(self):
        # Note: cannot use super because DictReader is an old-style class
        row = DictReader.next(self)
        return {k.strip(): v.strip() if v is not None else v for k, v in row.items()}


class YamlCheckCV(BaseCV):
    """
    A CV from which a YAML check can be generated
    """

    def to_yaml_check(self):
        """
        Use `get_yaml_checks` to write a YAML check suite for use with
        cc-yaml
        :return: the YAML document as a string
        """
        return yaml.dump({
            "suite_name": "{}_checks".format(self.namespace),
            "checks": list(self.get_yaml_checks())
        })

    def get_yaml_checks(self):
        """
        Return an iterable of check dictionaries for use with cc-yaml check
        suite. Must be implemented in child classes.
        """
        raise NotImplementedError
