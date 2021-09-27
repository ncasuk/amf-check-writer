"""
workflow_doc.py
===============

Writes some documentation (Markdown) about the workflow.

"""

import os
import yaml


this_dir = os.path.dirname(os.path.abspath(__file__))
INPUT_DATA = os.path.join(this_dir, 'workflow_data.yml')
OUTPUT_DIR = '.'


def read_workflow_data():
    return yaml.load(open(INPUT_DATA), Loader=yaml.SafeLoader)


def _get(seq, indx, default=""):
    "Returns `default` if `indx` not in sequence"
    if indx >= len(seq): 
        return default

    return seq[indx]


def _filter_dict(dct):
    ignores = ["header", "text"]
    dct = dct.copy()
    
    for ignore in ignores:
        del dct[ignore]

    return dct


def fmt_table(dct):
    # Remove ignore fields from dict
    dct = _filter_dict(dct)
    SEP = " | "

    # Format table header
    md = SEP.join([key for key in dct]) + "\n"
    md += SEP.join(["--" for key in dct]) + "\n"

    # Format table content
    values = [vals for vals in dct.values()]
    n = max([len(vals) for vals in values])

    for i in range(n):
        md += SEP.join([_get(vals, i) for vals in values]) + "\n"

    return md


def fmt_section(dct):
    text = dct["text"].replace("[NEW_PARA]", "\n\n")
    md = f"## {dct['header']}\n\n{text}\n\n"
    md += fmt_table(dct)
    return md


def format_content(content):
    gdrive_content = content

    # Build the markdown
    md = f"# Workflow diagram for AMF Check Writer: Checks and Vocabularies\n\n"

    for key, value in content.items():
        md += fmt_section(value)

    return md


def write_workflow_doc():
    content = read_workflow_data()
    markdown = format_content(content)

    output_file = os.path.join(OUTPUT_DIR, 'amf-check-workflow.md')
    with open(output_file, "w") as writer:
        writer.write(markdown)

    print(f"[INFO] Wrote workflow to: {output_file}")
 

def write_docs():
    write_workflow_doc()


def main():
    write_docs()


