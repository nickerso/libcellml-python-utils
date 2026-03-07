#!/usr/bin/env python3

import argparse
from pathlib import Path
import sys
import cellml
import logging


root_logger = logging.getLogger("libcellml_python_utils")
root_logger.setLevel(logging.INFO)
terminal_handler = logging.StreamHandler(sys.stderr)
terminal_handler.setLevel(logging.INFO)
root_logger.addHandler(terminal_handler)


def validate_model(file_path, strict_mode):
    model = cellml.parse_model(file_path, strict_mode)
    if model:
        cellml.validate_model(model)
        # del model


def generate_code(file_path, strict_mode, print_code):
    flat_model = flatten_model(file_path, strict_mode, False, None)
    if flat_model:
        if cellml.validate_model(flat_model) > 0:
            root_logger.warning('Validation issues found in flattened model')
            return

        root_logger.info('Model was flattened without any issues.')

        # this will report any issues that come up in analysing the model to prepare for code generation
        analysed_model = cellml.analyse_model(flat_model)
        cellml.generate_code(analysed_model, print_code)


def flatten_model(file_path, strict_mode, add_ids, output=None):
    model = cellml.parse_model(file_path, strict_mode)
    if model is None:
        return None
    if cellml.validate_model(model) > 0:
        return None
    importer = cellml.resolve_imports(model, str(file_path.parent), strict_mode)
    if model.hasUnresolvedImports():
        return None
    if cellml.validate_model(model) > 0:
        return None
    root_logger.info('Model was parsed, resolved, and validated without any issues.')
    # need a flattened model for analysing
    flat_model = cellml.flatten_model(model, importer)
    fms = cellml.print_model(flat_model, add_ids)
    if output:
        with output.open("w") as f:
            f.write(fms)
    return flat_model


def _insert_source_comment(xml_string: str, url: str) -> str:
    """Insert a source comment into an XML string, respecting any XML declaration."""
    comment = f"<!--\n  This is a flattened model originally retrieved from:\n    {url}\n-->"
    
    if xml_string.lstrip().startswith("<?xml"):
        # Insert after the end of the declaration line
        decl_end = xml_string.index("?>") + 2
        return xml_string[:decl_end] + "\n" + comment + xml_string[decl_end:]
    
    return comment + xml_string


def fetch_flat_model(url, strict_mode, add_ids, output=None):
    model = cellml.parse_remote_model(url, strict_mode)
    if model is None:
        return None
    if cellml.validate_model(model) > 0:
        return None
    importer = None
    if model.hasUnresolvedImports():
        importer = cellml.resolve_remote_imports(model, url, strict_mode)
        if model.hasUnresolvedImports():
            root_logger.debug(f'Model has unresolved imports after attempting to resolve remote imports')
            return None
        if cellml.validate_model(model) > 0:
            root_logger.warning('Validation issues found in model after resolving remote imports')
            return None
    root_logger.info('Model was parsed, resolved, and validated without any issues.')
    # # need a flattened model for analysing
    flat_model = cellml.flatten_model(model, importer)
    if output:
        fms = cellml.print_model(flat_model, add_ids)
        fms = _insert_source_comment(fms, url)
        with output.open("w") as f:
            f.write(fms)
    return flat_model


def convert_model(file_path, add_ids, output):
    model = cellml.parse_model(file_path, False)
    if model:
        model_string = cellml.print_model(model, add_ids)
        if output:
            with output.open("w") as f:
                f.write(model_string)
        else:
            print(model_string)


def summarize(file_path, verbose):
    size = Path(file_path).stat().st_size
    print(f"File: {file_path}")
    print(f"Size: {size} bytes")
    if verbose:
        print(f"Absolute path: {Path(file_path).resolve()}")


def main():
    parser = argparse.ArgumentParser(description="Perform various actions on a CellML file.")
    # --- Logging options ---
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        metavar="LEVEL",
        help="Log verbosity: DEBUG (most verbose) → INFO → WARNING → ERROR (least verbose). ",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging. Equivalent to --log-level DEBUG.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: validate
    parser_validate = subparsers.add_parser("validate", help="Validate the model")
    parser_validate.add_argument("input_file", help='Path to the input CellML file')
    parser_validate.add_argument('-s', '--strict', action='store_true',
                                 help='Validate in strict mode.')

    # Subcommand: executable
    parser_executable = subparsers.add_parser("executable", help="Check if code can be generated for the model")
    parser_executable.add_argument("input_file", help='Path to the input CellML file')
    parser_executable.add_argument('-s', '--strict', action='store_true',
                                   help='Parse and import models in strict mode.')
    parser_executable.add_argument('-p', '--print', action='store_true',
                                   help='Print out the generated code')

    # Subcommand: flatten
    parser_flatten = subparsers.add_parser("flatten", help="Flatten the provided model, if possible")
    parser_flatten.add_argument("input_file", help='Path to the input CellML file')
    parser_flatten.add_argument('-s', '--strict', action='store_true',
                                help='Parse and import models in strict mode.')
    parser_flatten.add_argument('-i', '--add-ids', action='store_true',
                                help='If set, make sure all CellML elements have an ID attribute')
    parser_flatten.add_argument('-o', '--output', required=True, type=Path,
                                help='Path to output flattened model')
    parser_flatten.add_argument('-f', '--force', action='store_true',
                                help='Overwrite any existing file at the output location')

    # Subcommand: fetch-flat-model
    parser_fetch_flat_model = subparsers.add_parser("fetch-flat-model", help="Fetch the flattened version of the provided remote model")
    parser_fetch_flat_model.add_argument("url", help='URL of the remote CellML model to fetch and flatten')
    parser_fetch_flat_model.add_argument('-s', '--strict', action='store_true',
                                         help='Parse and import models in strict mode.')
    parser_fetch_flat_model.add_argument('-i', '--add-ids', action='store_true',
                                         help='If set, make sure all CellML elements int he flattened model have an ID attribute')
    parser_fetch_flat_model.add_argument('-o', '--output', required=True, type=Path,
                                         help='Path to output flattened model')
    parser_fetch_flat_model.add_argument('-f', '--force', action='store_true',
                                         help='Overwrite any existing file at the output location')

    # Subcommand: convert
    parser_convert = subparsers.add_parser("convert", help="Convert input CellML model to CellML 2")
    parser_convert.add_argument("input_file", help='Path to the input CellML file')
    parser_convert.add_argument("-n", "--num-lines", type=int, default=5, help="Number of lines to show (default: 5)")
    parser_convert.add_argument('-i', '--add-ids', action='store_true',
                                help='If set, make sure all CellML elements have an ID attribute')
    parser_convert.add_argument('-f', '--force', action='store_true',
                                help='Overwrite any existing file at the output location')
    parser_convert.add_argument("-o", "--output", type=Path,
                                help="Path to output file; fallback to stdout if not provided")

    # Subcommand: summarize
    parser_summary = subparsers.add_parser("summarize", help="Print file summary")
    parser_summary.add_argument("input_file", help='Path to the input file')
    parser_summary.add_argument("-v", "--verbose", action="store_true", help="Show additional file details")

    args = parser.parse_args()

    root_logger.info(f'Command: {args.command}')
    
    if args.debug:
        root_logger.info('Debug logging enabled via --debug flag')
        root_logger.setLevel(logging.DEBUG)
        terminal_handler.setLevel(logging.DEBUG)
    elif args.log_level:
        root_logger.setLevel(getattr(logging, args.log_level))
        terminal_handler.setLevel(getattr(logging, args.log_level))

    file_path = None
    if args.command != 'fetch-flat-model':
        file_path = Path(args.input_file)
        if not file_path.is_file():
            print(f"Error: File '{file_path}' not found.", file=sys.stderr)
            sys.exit(1)

    if args.command == "validate":
        validate_model(file_path, args.strict)
    elif args.command == "convert":
        if args.output:
            if args.output.exists():
                if args.force:
                    root_logger.warning(f'Warning: forcing overwrite of existing file {args.output}')
                else:
                    root_logger.error(f"Error: Output file '{args.output}' already exists. Use a different name or delete it.")
                    sys.exit(1)
        convert_model(file_path, args.add_ids, args.output)
    elif args.command == "flatten":
        if args.output.exists():
            if args.force:
                root_logger.warning(f'Warning: forcing overwrite of existing file {args.output}')
            else:
                root_logger.error(f"Error: Output file '{args.output}' already exists. Use a different name or delete it or force "
                                  f"overwrite.")
                sys.exit(1)
        flatten_model(file_path, args.strict, args.add_ids, args.output)
    elif args.command == "fetch-flat-model":
        root_logger.debug(f'Fetching and flattening model from {args.url} with strict_mode={args.strict} and add_ids={args.add_ids}')
        if args.output.exists():
            if args.force:
                root_logger.warning(f'Warning: forcing overwrite of existing file {args.output}')
            else:
                root_logger.error(f"Error: Output file '{args.output}' already exists. Use a different name or delete it or force "
                                  f"overwrite.")
                sys.exit(1)
        fetch_flat_model(args.url, args.strict, args.add_ids, args.output)
    elif args.command == "summarize":
        summarize(file_path, args.verbose)
    elif args.command == "executable":
        generate_code(file_path, args.strict, args.print)


if __name__ == "__main__":
    main()
