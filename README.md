# libCellml Python Utilities
Andre playing with some Python scripts to do stuff with libCellML (https://libcellml.org).

You will need some version of the libCellML python bindings that could vary depending on what Andre used on his machine to try these out....good luck!

## Utilities available

* `resolve-and-validate.py` will parse a CellML model, resolve imports, and validate - reporting any issues that occur at any point in the process. Can be used in a non-strict mode that will allow CellML 1.0 and 1.1 models as well as CellML 2.0. Will also run an analysis of the model to check the math in preparation for code generation which may find some useful issues in debugging the model.