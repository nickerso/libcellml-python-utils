import os
from tempfile import mkstemp
import importlib

def module_from_string(python_code_string):
    """
    Take the Python code generated by libCellML and load it into a module that can be executed.

    :param module_name: The name to give the generated module.
    :param python_code_string: The string of the Python code.
    :return: The executable module.
    """

    # write the generated code to a temporary file
    fid, filename = mkstemp(suffix='.py', prefix="csimpy_", text=True)
    file = os.fdopen(fid, "w")
    file.write(python_code_string)
    #print("Generated code is in: " + filename)
    file.close()
    # and load it back in
    module_name = os.path.splitext(os.path.basename(filename))[0]
    spec = importlib.util.spec_from_file_location(module_name, filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # and delete temporary file
    os.remove(filename)
    #print("Generated code file: {}; has been deleted.".format(filename))
    return module
