from libcellml import Analyser, AnalyserModel, Component, Generator, GeneratorProfile,\
    Importer, Model, Parser, Printer, Validator, Issue


import logging
import requests
from pathlib import Path
from urllib.parse import urljoin
from posixpath import dirname
import xml.etree.ElementTree as ET


log = logging.getLogger("libcellml_python_utils.cellml")


CELLML_NAMESPACES = {
    "http://www.cellml.org/cellml/1.0#": "1.0",
    "http://www.cellml.org/cellml/1.1#": "1.1",
    "http://www.cellml.org/cellml/2.0#": "2.0",
}

def _get_cellml_version(text: str, url: str = "") -> str | None:
    """
    Check the CellML model string and return its version ("1.0", "1.1", or "2.0").

    Returns None if text is not a CellML file.
    """
    if text is None:
        return None

    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        log.error("Failed to parse XML from %s: %s", url, e)
        return None

    # ElementTree represents namespaced tags as "{namespace}localname"
    tag = root.tag  # e.g. "{http://www.cellml.org/cellml/2.0#}model"

    if not tag.startswith("{"):
        log.error("Root element has no namespace — not a CellML file: %s", url)
        return None

    namespace = tag[1:tag.index("}")]
    version = CELLML_NAMESPACES.get(namespace)

    if version is None:
        log.error("Unrecognised root namespace '%s' in: %s", namespace, url)
        return None

    log.debug("Detected CellML %s at: %s", version, url)
    return version


def _fetch_text_file(url: str, check_cellml: bool = False) -> tuple[str, str] | None:
    """
    Fetch a remote text file and return its contents as a string.

    Parameters
    ----------
    url : str
        URL of the file to retrieve.
    check_cellml : bool
        If True, verify the content looks like a CellML XML file.
        Raises ValueError if the check fails.

    Returns
    -------
    str
        The file contents, or None if the file could not be retrieved.
    str
        The CellML version, or None if the file is not CellML XML

    Raises
    ------
    ValueError
        If check_cellml is True and the content doesn't look like CellML.
    """
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        log.error("Timed out fetching: %s", url)
        return None
    except requests.exceptions.ConnectionError:
        log.error("Could not connect to: %s", url)
        return None
    except requests.exceptions.HTTPError as e:
        log.error("HTTP %s fetching %s: %s", e.response.status_code, url, e)
        return None
    except requests.exceptions.RequestException as e:
        log.error("Unexpected error fetching %s: %s", url, e)
        return None

    # Check the Content-Type header before decoding
    content_type = response.headers.get("Content-Type", "")
    if content_type and not any(t in content_type for t in ("text/", "xml", "json")):
        log.error("Expected a text file but got Content-Type '%s' from: %s", content_type, url)
        return None

    try:
        text = response.content.decode(response.encoding or "utf-8")
    except (UnicodeDecodeError, LookupError) as e:
        log.error("Could not decode response from %s as text: %s", url, e)
        return None

    version = None
    if check_cellml:
        version = _get_cellml_version(text, url)
        if version == None:
            raise ValueError(
                f"XML file does not appear to be CellML (no recognised CellML namespace found): {url}"
            )

    log.debug("Fetched %d chars from %s", len(text), url)
    return text, version


# def _assert_is_cellml(text: str, url: str = "") -> None:
#     """
#     Raise ValueError if text doesn't look like a CellML file.
#     Checks for an XML declaration or root element containing the CellML namespace.
#     """
#     # Scan just the start of the file — no need to parse the whole thing
#     head = text[:2048]

#     if not head.lstrip().startswith("<"):
#         raise ValueError(f"Not an XML file (does not start with '<'): {url}")

#     CELLML_NAMESPACES = (
#         "http://www.cellml.org/cellml/1.0#",
#         "http://www.cellml.org/cellml/1.1#",
#         "http://www.cellml.org/cellml/2.0#",
#     )
#     if not any(ns in head for ns in CELLML_NAMESPACES):
#         raise ValueError(
#             f"XML file does not appear to be CellML (no recognised CellML namespace found): {url}"
#         )


#
# Wrappers for the libCellML python API to give some convenient methods.
#


def issue_level_to_string(level):
    if level == Issue.Level.ERROR:
        return 'Error'
    if level == Issue.Level.WARNING:
        return 'Warning'
    if level == Issue.Level.MESSAGE:
        return 'Message'
    return 'unknown level'


def _dump_issues(source_method_name, logger):
    if logger.issueCount() > 0:
        print('The method "{}" found {} issues:'.format(source_method_name, logger.issueCount()))
        for i in range(0, logger.issueCount()):
            print('    - ({}) {}'.format(issue_level_to_string(logger.issue(i).level()),
                                         logger.issue(i).description()))


def parse_remote_model(url: str, silent: bool = False, strict_mode: bool = False) -> tuple[str, str] | tuple[None, None]:
    log.debug(f'Attempting to fetch and parse a CellML model from {url} with strict_mode={strict_mode}')
    (text, version) = _fetch_text_file(url, check_cellml=True)
    if text is None:
        return None, None
    log.debug(f'Successfully fetched model text from {url}, now parsing...')
    parser = Parser(strict_mode)
    model = parser.parseModel(text)
    if not silent:
        _dump_issues("parse_remote_model", parser)
    if parser.errorCount() > 0:
        return None, None
    
    return model, version


def parse_model(filename, strict_mode):
    cellml_file = open(filename)
    parser = Parser(strict_mode)
    model = parser.parseModel(cellml_file.read())
    _dump_issues("parse_model", parser)
    if parser.errorCount() > 0:
        return None
    return model


def print_model(model, auto_ids=False):
    printer = Printer()
    s = printer.printModel(model, auto_ids)
    return s


def validate_model(model):
    validator = Validator()
    validator.validateModel(model)
    _dump_issues("validate_model", validator)
    return validator.issueCount()


def resolve_remote_imports(model, url, strict_mode, logger=None):
    if logger is None:
        logger = log

    importer = Importer(strict_mode)

    _fetch_remote_imports(model, importer, strict_mode, url, logger)

    importer.resolveImports(model, '')
    _dump_issues("_resolve_remote_imports", importer)
    if model.hasUnresolvedImports():
        logger.debug(f'Model has unresolved imports')
    else:
        logger.debug('No unresolved imports.')

    return importer


def _fetch_remote_imports(model, importer, strict_mode, base_url, logger, relative_path=""):
    required_models = model.importRequirements()
    logger.debug(f'Model has {len(required_models)} remote import requirements: {required_models}')
    base_dir = dirname(base_url) + "/"
    logger.debug(f'Base directory for resolving imports: {base_dir}')
    for required_model in required_models:
        logger.debug(f'Processing import requirement: {required_model}')
        imported_model = None
        import_key = required_model
        if required_model.startswith("http://") or required_model.startswith("https://"):
            if importer.library(import_key) is not None:
                logger.debug(f'Model for {required_model} already imported, skipping fetch')
                continue
            imported_model, version = parse_remote_model(required_model, strict_mode=strict_mode, silent=True)
        else:
            rel_dir = dirname(relative_path)
            import_key = Path(rel_dir) / required_model if rel_dir else required_model
            logger.debug(f'required_model={required_model}, relative_path={relative_path}, import_key={import_key}')
            required_model_url = urljoin(base_dir, required_model)
            logger.debug(f'Constructed URL for import: {required_model_url}')
            if importer.library(import_key) is not None:
                logger.debug(f'Model for {required_model} already imported, skipping fetch')
                continue
            imported_model, version = parse_remote_model(required_model_url, strict_mode=strict_mode, silent=True)
        if imported_model is not None:
            logger.debug(f'Successfully parsed imported model for requirement: {required_model}')
            logger.debug(f'imported_model: {imported_model}; with the name: {imported_model.name()}')
            logger.debug(f'import_key: {import_key}')
            importer.addModel(imported_model, import_key)
            if imported_model.hasUnresolvedImports():
                logger.debug(f'Imported model for {required_model} has its own imports, resolving them recursively')
                _fetch_remote_imports(imported_model, importer, strict_mode, required_model_url, logger, import_key)


def resolve_imports(model, base_dir, strict_mode):
    importer = Importer(strict_mode)
    importer.resolveImports(model, base_dir)
    _dump_issues("resolve_imports", importer)
    if model.hasUnresolvedImports():
        print("unresolved imports?")
    else:
        print("no unresolved imports.")
    return importer


def flatten_model(model, importer):
    flat_model = importer.flattenModel(model)
    return flat_model


def analyse_model(model, silent=False):
    analyser = Analyser()
    analyser.analyseModel(model)
    if not silent:
        _dump_issues("analyse_model", analyser)
    return analyser, analyser.errorCount()


def generate_code(analysed_model, print_code=True) -> bool:
    if print_code:
        print(analysed_model.model().type())

    # generate code from the analysed model
    g = Generator()
    profile = GeneratorProfile(GeneratorProfile.Profile.PYTHON)
    g.setProfile(profile)
    g.setModel(analysed_model.model())
    interface_code = g.interfaceCode()
    implementation_code = g.implementationCode()
    if print_code:
        print('header code:')
        print(interface_code)
        print('implementation code:')
        print(implementation_code)

    return True if (len(implementation_code) + len(interface_code)) > 0 else False


def _get_component_node(component):
    node = {
        'id': component.name(),
        'metaid': component.id() if component.id() else "UNIDENTIFIED_COMPONENT",
        'imported': str(component.isImport()),
        'title': 'imported source:'
    }
    return node


def _get_component_hierarchy(root, source_name):
    nodes = []
    edges = []
    current_node = _get_component_node(root)
    nodes.append(current_node)
    destination = current_node['id']
    edges.append({
        'from': source_name,
        'to': destination,
        'type': 'encapsulation'
    })
    for i in range(0, root.componentCount()):
        c = root.component(i)
        child_edges, children = _get_component_hierarchy(c, destination)
        nodes.extend(children)
        edges.extend(child_edges)
    if root.isImport():
        print(root.isResolved())
        imported_model = root.importSource().model()
        imported_component = imported_model.component(root.importReference())
        imported_node = _get_component_node(imported_component)
        nodes.append(imported_node)
        imported_destination = imported_node['id']
        edges.append({
            'from': destination,
            'to': imported_destination,
            'type': 'import'
        })
        child_edges, children = _get_component_hierarchy(imported_component, destination)
        nodes.extend(children)
        edges.extend(child_edges)
    return edges, nodes


def get_model_component_hierarchy(model):
    nodes = []
    edges = []
    model_node = {
        'id': model.name() if model.name() else "UNAMED_MODEL",
        'metaid': model.id() if model.id() else "UNIDENTIFIED_MODEL",
        'imported': 'False',
        'title': 'Model node'
    }
    nodes.append(model_node)
    source = model_node['id']
    for i in range(0, model.componentCount()):
        c = model.component(i)
        child_edges, children = _get_component_hierarchy(c, source)
        nodes.extend(children)
        edges.extend(child_edges)
    return edges, nodes
