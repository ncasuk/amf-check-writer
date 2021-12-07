# Workflow diagram for AMF Check Writer: Checks and Vocabularies


## Content from the Google Drive

The initial content is loaded from the versioned spreadsheets held on the AMOF Google Drive. The downloaded versions are published in the http://github.com/ncasuk/AMF_CVs repository.

_common.xlsx | _vocabularies.xlsx | per-product
-- | -- | --
global-attributes | community-instrument-name-and-descriptors | dimensions-specific
dimensions-trajectory | ncas-instrument-name-and-descriptors | global-attributes-specific*
variables-trajectory | data-products | variables-specific
dimensions-land | platforms | 
variables-land | creators | 
dimensions-air | file-naming | 
variables-air |  | 
dimensions-sea |  | 
variables-sea |  | 

## YAML checks

The YAML checks are generated from the CSV version of the worksheets saved from the Google Drive spreadsheets. These are published in the http://github.com/ncasuk/amf-compliance-checks repository.

common | per-product
-- | --
AMF_product_common_dimension_air.yml | AMF_product_{product}_air.yml
AMF_product_common_dimension_land.yml | AMF_product_{product}_dimension.yml
AMF_product_common_dimension_sea.yml | AMF_product_{product}_land.yml
AMF_product_common_dimension_trajectory.yml | AMF_product_{product}_sea.yml
AMF_product_common_global-attributes_air.yml | AMF_product_{product}_trajectory.yml
AMF_product_common_global-attributes_land.yml | AMF_product_{product}_variable.yml
AMF_product_common_global-attributes_sea.yml | AMF_product_{product}_global-attributes.yml*
AMF_product_common_global-attributes_trajectory.yml | 
AMF_product_common_variable_air.yml | 
AMF_product_common_variable_land.yml | 
AMF_product_common_variable_sea.yml | 
AMF_product_common_variable_trajectory.yml | 
AMF_file_info.yml | 
AMF_file_structure.yml | 
AMF_global_attrs.yml | 

## Controlled vocabularies (in JSON format)

A set of controlled vocabularies are generated from the spreadsheet data. These are written as JSON files and are published in the https://github.com/ncasuk/AMF_CVs repository.

common | per-product
-- | --
AMF_ncas_instrument.json | AMF_product_{product}_variable.json
AMF_community_instrument.json | AMF_product_{product}_dimension.json*
AMF_product.json | AMF_product_{product}_global-attributes.json*
AMF_platform.json | 
AMF_scientist.json | 
AMF_product_common_variable_land.json | 
AMF_product_common_variable_sea.json | 
AMF_product_common_variable_air.json | 
AMF_product_common_variable_trajectory.json | 
AMF_product_common_dimension_land.json | 
AMF_product_common_dimension_sea.json | 
AMF_product_common_dimension_air.json | 
AMF_product_common_dimension_trajectory.json | 
AMF_product_common_global-attributes_land.json | 
AMF_product_common_global-attributes_sea.json | 
AMF_product_common_global-attributes_air.json | 
AMF_product_common_global-attributes_trajectory.json | 

## Controlled vocabularies (in PYESSV format)

A set of controlled vocabularies are generated from the spreadsheet data. These are written as PYESSV files and are published in the https://github.com/ncasuk/AMF_CVs repository.


These are used by the https://github.com/cedadev/compliance-check-lib library when running checks.

common | per-product
-- | --
community-instrument | product-{product}-dimension
ncas-instrument | product-{product}-global-attributes
platform | product-{product}-variable
scientist | 
product-common-dimension-air | 
product-common-dimension-land | 
product-common-dimension-sea | 
product-common-dimension-trajectory | 
product-common-global-attributes-air | 
product-common-global-attributes-land | 
product-common-global-attributes-sea | 
product-common-global-attributes-trajectory | 
product-common-variable-air | 
product-common-variable-land | 
product-common-variable-sea | 
product-common-variable-trajectory | 


