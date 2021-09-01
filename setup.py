from setuptools import setup, find_packages

with open("requirements.txt") as req_file:
    requirements = [line.strip() for line in req_file]

setup(
    name="amf_check_writer",
    version="0.0.1",
    description="Library to write AMF compliance checks",
    packages=find_packages(),
    install_requires=requirements,
    extras_require={
        "test": ["pytest"]
    },
    entry_points={
        "console_scripts": [
            "amf-checker=amf_check_writer.amf_checker:main",
            "create-cvs=amf_check_writer.create_cvs:main",
            "create-yaml-checks=amf_check_writer.create_yaml_checks:main",
            "download-from-drive=amf_check_writer.download_from_drive:main",
            "write-workflow-docs=amf_check_writer.workflow_docs:main"
        ]
    }
)
