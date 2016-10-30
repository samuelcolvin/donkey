import asyncio
import locale
import logging
import re
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import trafaret as t
from trafaret_config import read_and_validate

logger = logging.getLogger('donkey')
main_logger = logging.getLogger('donkey.main')

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


class AnyKey:
    name = 'ANY'

    def __init__(self, check_root=False):
        self.check_root = check_root
        self.trafaret = None

    def set_trafaret(self, trafaret):
        self.trafaret = t.Trafaret._trafaret(trafaret)
        return self

    def __call__(self, data):
        for k, v in data.items():
            if self.check_root and k in ROOT_KEYS:
                continue
            yield (
                k,
                t.catch_error(self.trafaret, v),
                (k,)
            )

# TODO in trafaret
# AnyKey Support
# better errors for Or
# missing keys take value

STRING_LIST = t.List(t.String)
STRING_DICT = t.Dict({AnyKey(): t.String})
STRUCTURE = t.Dict({
    t.Key('.default', optional=True): t.Or(
        t.Dict({
            'name': t.String,
        }),
        t.String,
    ),
    t.Key('.settings', optional=True, default={}): STRING_DICT,
    t.Key('.config', optional=True): t.Dict({
        t.Key('parallel', default=False): t.Bool,
        t.Key('mode', default='script'): t.String(regex='^(script|independent)$'),
    }),
    AnyKey(check_root=True): t.Or(
        t.Dict({  # TODO this should extend on .config
            t.Key(name='interpreter', default='bash'): t.String,
            t.Key(name='command', optional=True): t.String,
            t.Key(name='settings', optional=True): STRING_DICT,
            t.Key(name='commands'): STRING_LIST,
        }),
        STRING_LIST,
    ),
})

ROOT_KEYS = {k.name if isinstance(k, t.Key) else k for k in STRUCTURE.keys if not isinstance(k, AnyKey)}


@contextmanager
def loop_context():
    if sys.platform == 'win32':
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
    else:
        loop = asyncio.get_event_loop()
    yield loop
    loop.close()


STD_FILES = {
    1: 'stdout',
    2: 'stderr',
}


class DonkeySubprocessProtocol(asyncio.SubprocessProtocol):
    def __init__(self, exit_future):
        self.exit_future = exit_future

    def pipe_data_received(self, fd, data):
        s = data.decode(locale.getpreferredencoding(False))
        l = logger.info if fd == 1 else logger.warning
        extra = {'stdfile': STD_FILES[fd]}
        for line in s.split('\n'):
            if line:
                l('%s', line, extra=extra)

    def process_exited(self):
        self.exit_future.set_result(True)


async def run(loop, *args):
    exit_future = asyncio.Future(loop=loop)
    transport, _ = await loop.subprocess_exec(lambda: DonkeySubprocessProtocol(exit_future), *args)

    await exit_future
    return_code = transport.get_returncode()
    transport.close()
    return return_code


async def execute_command(loop, name, command_data):
    main_logger.info('starting command "%s"', name)
    start = datetime.now()
    return_code = await run(loop, 'bash', '-c', '\n'.join(command_data))
    time_taken = datetime.now() - start
    main_logger.info('"%s" finished in %0.2fs, return code: %d', name, time_taken.total_seconds(), return_code)


def execute(*, commands, parallel, args, definition_file):
    if definition_file:
        def_path = Path(definition_file).resolve()
    else:
        def_path = find_def_file()
    def_data = read_and_validate(str(def_path), STRUCTURE)
    default_command = def_data.pop('.default', None)
    settings = def_data.pop('.settings', None)
    config = def_data.pop('.config', {})
    to_run = []
    for c in commands:
        if c not in def_data:
            raise DonkeyError('command "{}" not found in "{}", '
                              'options: {}'.format(c, def_path, ', '.join(def_data.keys())))
        to_run.append((c, def_data[c]))
    with loop_context() as loop:
        for name, c in to_run:
            loop.run_until_complete(execute_command(loop, name, c))
