#!/bin/bash

# Installs checker with everything required to run.
#
# Usage:
# ------
#
# ./install-checker-suite.sh <base_directory>
#

CHECKS_BASE_DIR=${1:-${PWD}/checks-work-dir}
CHECKS_BASE_DIR=$(realpath $CHECKS_BASE_DIR)

ENV_NAME=amf-checks-env
pdir=$(dirname $CHECKS_BASE_DIR)

if [ ! -d "$pdir" ]; then
    echo "[ERROR] Parent directory of base directory must exist: $pdir"
    exit
fi

echo "[INFO] Making/checking base directory: $CHECKS_BASE_DIR"
mkdir -p $CHECKS_BASE_DIR

echo "[INFO] Installing miniconda and python..."
cd $CHECKS_BASE_DIR/
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
sh Miniconda3-latest-Linux-x86_64.sh -p ${CHECKS_BASE_DIR}/miniconda3 -b
rm -f Miniconda3-latest-Linux-x86_64.sh
export PATH=$PATH:${CHECKS_BASE_DIR}/miniconda3/bin

echo "[INFO] Creating environment: $ENV_NAME"
conda create --name $ENV_NAME python=3.9 -y
source activate $ENV_NAME

echo "[INFO] Install the third-party compliance-checker framework..."
conda install -c conda-forge compliance-checker pip -y

echo "[INFO] Install and/or clone the relevant repositories..."
pip install git+https://github.com/cedadev/compliance-check-lib
pip install git+https://github.com/cedadev/cc-yaml
pip install git+https://github.com/ncasuk/amf-check-writer

CV_VERSIONS=2.0.0
PACKAGES="AMF_CVs amf-compliance-checks"

for pkg in $PACKAGES; do
    zfile=v${CV_VERSIONS}.zip
    wget https://github.com/ncasuk/${pkg}/archive/refs/tags/${zfile}
    unzip $zfile
    rm -f $zfile 
done

echo "[INFO] Create setup file..."
PYESSV_ARCHIVE_HOME=$CHECKS_BASE_DIR/AMF_CVs-${CV_VERSIONS}/pyessv-vocabs
CHECKS_DIR=$CHECKS_BASE_DIR/amf-compliance-checks-${CV_VERSIONS}/checks

setup_file=${CHECKS_BASE_DIR}/setup-checks-env.sh

echo "export CHECKS_BASE_DIR=$CHECKS_BASE_DIR" >> $setup_file
echo "export PATH=\$PATH:\${CHECKS_BASE_DIR}/miniconda3/bin" >> $setup_file
echo " "  >> $setup_file
echo "source activate amf-checks-env" >> $setup_file
echo "export PYESSV_ARCHIVE_HOME=$PYESSV_ARCHIVE_HOME" >> $setup_file
echo "export CHECKS_DIR=$CHECKS_DIR" >> $setup_file

echo "[INFO] To setup environment, do:"
echo "source $setup_file" 

echo "[INFO] Installation complete..."
echo "[INFO] You can test it with:"

echo "source $setup_file"
echo "VERSION=v2.0"
echo "TEST_FILE_NAME=ncas-anemometer-1_ral_29001225_mean-winds_v0.1.nc"
echo 'TEST_FILE_URL="https://github.com/cedadev/compliance-check-lib/blob/master/tests/example_data/nc_file_checks_data/${TEST_FILE_NAME}?raw=true"'
echo "wget -O \$TEST_FILE_NAME \$TEST_FILE_URL"
echo "TEST_FILE=\${PWD}/\${TEST_FILE_NAME}"
echo "amf-checker --yaml-dir \$CHECKS_DIR --version \$VERSION \$TEST_FILE"

echo "[INFO] Or more generally:"
echo "amf-checker --yaml-dir $CHECKS_DIR --version <version> <test_file>"

