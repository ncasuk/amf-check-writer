#!/bin/bash

# Installs checker with everything required to run.
#
# Usage:
# ------
#
# ./install-checker-suite.sh [--no-conda] [<base_directory>]
#

INSTALL_DIR=
INSTALL_CONDA=1

while [[ "$#" -gt 0 ]]; do
    case $1 in
        -n|--no-conda) INSTALL_CONDA=0 ;;
        *) INSTALL_DIR=$1 ;;
    esac
    shift
done

CHECKS_BASE_DIR=${INSTALL_DIR:-${PWD}/checks-work-dir}
CHECKS_BASE_DIR=$(realpath $CHECKS_BASE_DIR)

ENV_NAME=amf-checks-env
pdir=$(dirname $CHECKS_BASE_DIR)

if [ ! -d "$pdir" ]; then
    echo "[ERROR] Parent directory of base directory must exist: $pdir"
    exit
fi

echo "[INFO] Making/checking base directory: $CHECKS_BASE_DIR"
mkdir -p $CHECKS_BASE_DIR

if [ $INSTALL_CONDA -eq 0 ]; then
    which conda > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "[ERROR] Cannot find 'conda' executable. Suggested fix: run with '--no-conda' option."
        exit
    fi 
    echo "[INFO] Found 'conda' executable, will use the local installation."

else
    echo "[INFO] Installing miniconda and python..."
    cd $CHECKS_BASE_DIR/

    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
    sh Miniconda3-latest-Linux-x86_64.sh -p ${CHECKS_BASE_DIR}/miniconda3 -b
    rm -f Miniconda3-latest-Linux-x86_64.sh
    export PATH=$PATH:${CHECKS_BASE_DIR}/miniconda3/bin
fi

echo "[INFO] Creating environment: $ENV_NAME"
conda create --name $ENV_NAME python=3.9 -y
source activate $ENV_NAME

echo "[INFO] Install the third-party compliance-checker framework..."
conda install -c conda-forge compliance-checker pip -y

CHECKS_VERSION=v2.0.1test
MINOR_VERSION=$(echo $CHECKS_VERSION | cut -d. -f1-2)

echo "[INFO] Install and/or clone the relevant repositories..."
CEDADEV_REPOS="cedadev/compliance-check-lib cedadev/cc-yaml"
NCASUK_REPOS="ncasuk/amf-check-writer ncasuk/AMF_CVs.git@${CHECKS_VERSION} ncasuk/amf-compliance-checks.git@${CHECKS_VERSION}"

for repo in $CEDADEV_REPOS $NCASUK_REPOS; do
    pip install git+https://github.com/$repo
done

echo "[INFO] Create setup file..."
setup_file=${CHECKS_BASE_DIR}/setup-checks-env.sh

echo "export CHECKS_BASE_DIR=$CHECKS_BASE_DIR" >> $setup_file
echo "export PATH=\$PATH:\${CHECKS_BASE_DIR}/miniconda3/bin" >> $setup_file
echo " "  >> $setup_file
echo "source activate amf-checks-env" >> $setup_file
echo "export CHECKS_VERSION=${MINOR_VERSION}" >> $setup_file

echo "[INFO] To setup environment, do:"
echo "source $setup_file" 

echo "[INFO] Installation complete..."
echo "[INFO] You can test it with:"

echo "source $setup_file"
echo "TEST_FILE_NAME=ncas-anemometer-1_ral_29001225_mean-winds_v0.1.nc"
echo 'TEST_FILE_URL="https://github.com/cedadev/compliance-check-lib/blob/main/tests/example_data/nc_file_checks_data/${TEST_FILE_NAME}?raw=true"'
echo "wget -O \$TEST_FILE_NAME \$TEST_FILE_URL"
echo "amf-checker --version \$CHECKS_VERSION \$TEST_FILE_NAME"

echo "[INFO] Or more generally:"
echo "amf-checker --version <version> <test_file>"

