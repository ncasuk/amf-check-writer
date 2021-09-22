# Workflow diagram for AMF Check Writer: Checks and Vocabularies

## Content from the Google Drive

The initial content is loaded from the versioned spreadsheets held on the AMOF Google Drive.

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

The YAML checks are generated from the CSV version of the worksheets saved from the Google Drive spreadsheets.

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
## Controlled vocabularies

A set of controlled vocabularies are generated from the spreadsheet data. These are written as JSON files and in PYESSV format. The latter is used in by the `compliance-check-lib` library when running the checks.

json-common | json-per-product | pyessv
-- | -- | --
AMF_ncas_instrument.json | AMF_product_{product}_variable.json | noone
AMF_community_instrument.json | AMF_product_{product}_dimension.json* | 
AMF_product.json | AMF_product_{product}_global-attributes.json* | 
AMF_platform.json |  | 
AMF_scientist.json |  | 
AMF_product_common_variable_land.json |  | 
AMF_product_common_variable_sea.json |  | 
AMF_product_common_variable_air.json |  | 
AMF_product_common_variable_trajectory.json |  | 
AMF_product_common_dimension_land.json |  | 
AMF_product_common_dimension_sea.json |  | 
AMF_product_common_dimension_air.json |  | 
AMF_product_common_dimension_trajectory.json |  | 
AMF_product_common_global-attributes_land.json |  | 
AMF_product_common_global-attributes_sea.json |  | 
AMF_product_common_global-attributes_air.json |  | 
AMF_product_common_global-attributes_trajectory.json |  | 
