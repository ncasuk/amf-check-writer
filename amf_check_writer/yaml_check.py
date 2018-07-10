from operator import attrgetter

import yaml

from amf_check_writer.base_file import AmfFile


class YamlCheck(AmfFile):
    """
    A YAML file that can be used with cc-yaml to run a suite of checks
    """
    def to_yaml_check(self):
        """
        Use `get_yaml_checks` to write a YAML check suite for use with cc-yaml
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


class WrapperYamlCheck(YamlCheck):
    """
    Wrapper check that just includes checks from other files
    """
    def __init__(self, child_checks, *args, **kwargs):
        self.child_checks = child_checks
        super(WrapperYamlCheck, self).__init__(*args, **kwargs)

    def get_yaml_checks(self):
        for check in sorted(self.child_checks, key=attrgetter("namespace")):
            yield {"__INCLUDE__": check.get_filename("yml")}
