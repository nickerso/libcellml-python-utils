# import
import os
import sys
import cellml

#
# load a CellML model and print out the components and variables
#
# usage:
#   python print-model.py <CellML model filename> [strict]
#
#   strict (optional) = false, use a non-strict parser and importer (i.e., allow CellML 1.0 and 1.1 models)
#   default is strict mode (i.e., only allow CellML 2.0 models)
#


if len(sys.argv) < 2:
    print('Usage: print-model.py <CellML model filename> [strict]')
    exit(-1)

cellml_file = sys.argv[1]
print('Working on the CellML file: {}'.format(cellml_file))

cellml_strict_mode = True
if len(sys.argv) > 2:
    strict_mode = sys.argv[2]
    if strict_mode == 'false':
        cellml_strict_mode = False

if cellml_strict_mode:
    print('  Parsing files in STRICT mode (only CellML 2.0 models accepted)')
else:
    print('  Parsing files in NON-STRICT mode (any CellML models accepted)')

model = cellml.parse_model(cellml_file, cellml_strict_mode)
if cellml.validate_model(model) > 0:
    exit(-2)

# loop over all the components in the model
for i in range(0, model.componentCount()):
    c = model.component(i)
    print('Component: {}'.format(c.name()))
    # loop over all the variables in the component
    for j in range(0, c.variableCount()):
        v = c.variable(j)
        print('  -- Variable: {}'.format(v.name()))

