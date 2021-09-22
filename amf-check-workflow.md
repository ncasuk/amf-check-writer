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
AMF_file_info.yml | AMF_product_{product}_air.yml
AMF_file_structure.yml | AMF_product_{product}_dimension.yml
AMF_global_attrs.yml | AMF_product_{product}_land.yml
 | AMF_product_{product}_sea.yml
 | AMF_product_{product}_trajectory.yml
 | AMF_product_{product}_variable.yml
 | AMF_product_{product}_global-attributes.yml*
