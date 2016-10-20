import re
from pathlib import Path

STD_FILE_NAMES = [
    re.compile('donkey\.ya?ml'),
    re.compile('makefile\.ya?ml'),
]


class DonkeyError(Exception):
    pass


def find_def_file(p=None):
    p = p or Path('.').resolve()
    files = [x for x in p.iterdir() if x.is_file()]
    for std_file_name in STD_FILE_NAMES:
        try:
            def_path = next(f for f in files if std_file_name.fullmatch(f.name))
        except StopIteration:
            pass
        else:
            return def_path
    if p == p.parent:
        # got to /
        raise DonkeyError('Unable to definition file with standard name {} in the current working '
                          'directory or any parent directory'.format(' or '.join(r.pattern for r in STD_FILE_NAMES)))
    return find_def_file(p.parent)


def execute(*, commands, parallel, args, definition_file):
    if definition_file:
        def_path = Path(definition_file).resolve()
    else:
        def_path = find_def_file()
    print(def_path)
    print('commands       ', commands)
    print('parallel       ', parallel)
    print('args           ', args)
