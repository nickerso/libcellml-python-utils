# import
import os
import sys
import cellml

#
# load a CellML model, resolve any imports, and validate the full model.
#
# usage:
#   python resolve-and-validate.py <CellML model filename> [strict]
#
#   strict (optional) = false, use a non-strict parser and importer (i.e., allow CellML 1.0 and 1.1 models)
#   default is strict mode (i.e., only allow CellML 2.0 models)
#


cellml_file = sys.argv[1]
cellml_file_dir = os.path.dirname(cellml_file)
print('Working on the CellML file: {}; resolving imports with the context: {}'.format(cellml_file, cellml_file_dir))

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
    exit(-1)

importer = cellml.resolve_imports(model, cellml_file_dir, cellml_strict_mode)
if model.hasUnresolvedImports():
    print("unresolved imports?")
    exit(-2)

if cellml.validate_model(model) > 0:
    print('Validation issues found')
    exit(-3)

print('Model was parsed, resolved, and validated without any issues.')

# need a flattened model for analysing
flat_model = cellml.flatten_model(model, importer)
if cellml.validate_model(model) > 0:
    print('Validation issues found in flattened model')
    exit(-4)

print('Model was flattened without any issues.')

# this will report any issues that come up in analysing the model to prepare for code generation
analysed_model = cellml.analyse_model(flat_model)

