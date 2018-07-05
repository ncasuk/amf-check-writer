import sys
import json
import os

import yaml


def convert_to_yaml_check(json_filename):
    """
    Return a dictionary that will be saved as a YAML file to check variables
    according to the variables listed in a JSON file.

    The JSON file should have beeen produced by create_cvs.py.
    """
    with open(json_filename) as f:
        cv = json.load(f)

    basename = os.path.basename(json_filename)
    assert basename.startswith("AMF_")

    # Extract namespace from JSON filename. This relies heavily on the format
    # of the JSON files as produced by create_cvs.main().
    # Simply remove 'AMF_' prefix and '.json' suffix to get the namespace
    namespace = basename[4:-5]

    # Reformat name for use in various places
    parts = namespace.split("_")
    cls_name = "".join(map(str.capitalize, parts))
    desc_name = " ".join(parts)

    variables = cv[namespace]

    yml = []
    # Add header information
    yml.append({
        "ccPluginClass": "AMF{}Check".format(cls_name),
        "description": "Check {} in AMF files".format(desc_name),
        "ccPluginId": "amf-{}".format(namespace),
        "ccPluginPackage": "cc_plugin_amf.amf_{}".format(namespace),
        "ccPluginTemplate": "BaseNCCheck",
        "checklibPackage": "checklib.register.nc_file_checks_register",
    })

    for i, (var, attrs) in enumerate(variables.items()):
        # Add variable metadata check
        yml.append({
            "check_id": "varattrs{}".format(i + 1),
            "check_name": "NCVariableMetadataCheck",
            "check_level": "HIGH",
            "vocabulary_ref": "ncas:amf",
            "modifiers": {
                "var_id": str(var),
                "pyessv_namespace": str(namespace)
            },
            "comments": "Checks the variable attributes for '{}'".format(var),
        })

        # Add variable type check
        yml.append({
            "check_id": "vartype{}".format(i + 1),
            "check_name": "VariableTypeCheck",
            "check_level": "HIGH",
            "vocabulary_ref": "",
            "modifiers": {"var_id": str(var), "dtype": str(attrs["type"])}
        })

    return yml

def main():
    """
    Read JSON controlled vocabulary files describing attributes for variables,
    and write YAML checks that can be used with compliance-check-maker
    """
    if len(sys.argv) < 3:
        usage = "Usage: {} IN_DIR OUT_DIR".format(sys.argv[0])
        sys.stderr.write(usage + os.linesep)
        sys.exit(1)

    json_dir, out_dir = sys.argv[1:3]

    for dirpath, dirnames, filenames in os.walk(json_dir):
        for fname in filenames:
            if fname.startswith("AMF_") and fname.endswith(".json"):
                in_file = os.path.join(dirpath, fname)
                out_file = os.path.join(out_dir, "{}.yml".format(fname[:-5]))

                try:
                    yml = convert_to_yaml_check(in_file)

                    print("Writing to {}".format(out_file))
                    with open(out_file, "w") as f:
                        yaml.dump(yml, stream=f)

                except KeyError as ex:
                    sys.stderr.write("Missing value in {}: {}".format(in_file, ex) + os.linesep)

if __name__ == "__main__":
    main()
