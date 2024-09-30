from libcellml import Analyser, AnalyserModel, Component, Generator, GeneratorProfile,\
    Importer, Model, Parser, Printer, Validator, Issue, Variable, Units


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


def print_model(model):
    printer = Printer()
    s = printer.printModel(model)
    print(s)


def validate_model(model):
    validator = Validator()
    validator.validateModel(model)
    _dump_issues("validate_model", validator)
    return validator.issueCount()


def analyse_model(model):
    analyser = Analyser()
    analyser.analyseModel(model)
    _dump_issues("analyse_model", analyser)
    return analyser

print('\n\ntest adding a units to the model and setting a variable units by name')
m = Model("model")
c1 = Component("c1")
m.addComponent(c1)
v1 = Variable("v1")
v1.setUnits("bob")
c1.addVariable(v1)
print_model(m)
validate_model(m)
analyse_model(m)

bob = Units('bob')
m.addUnits(bob)
if m.hasUnlinkedUnits():
    print('**Unlinked units found**')
    if m.linkUnits():
        print('Units successfully linked')
    else:
        print('Units NOT successfully linked?!')
print_model(m)
validate_model(m)
analyse_model(m)

print('\n\ntest adding a units to a variable directly')
v2 = Variable("v2")
fred = Units('fred')
v2.setUnits(fred)
c1.addVariable(v2)
print_model(m)
validate_model(m)
analyse_model(m)
m.addUnits(fred)

if m.hasUnlinkedUnits():
    print('**Unlinked units found**')
    if m.linkUnits():
        print('Units successfully linked')
    else:
        print('Units NOT successfully linked?!')
print_model(m)
validate_model(m)
analyse_model(m)
