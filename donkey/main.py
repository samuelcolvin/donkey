import asyncio
import locale
import logging
import re
import shlex
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

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
        raise DonkeyError('Unable to find #definition file with standard name {} in the current working '
                          'directory or any parent directory'.format(' or '.join(r.pattern for r in STD_FILE_NAMES)))
    return find_def_file(p.parent)


# TODO in trafaret
# better errors for Or

CONFIG_OPTIONS = t.Dict({
    t.Key('interpreter', optional=True): t.String,
    t.Key('parallel', optional=True): t.Bool,
    t.Key('script', optional=True, to_name='script_mode'): t.Bool,
})

STRING_DICT = t.Dict()
STRING_DICT.allow_extra('*', trafaret=t.String)

STRUCTURE = t.Dict({
    t.Key('.default', optional=True): t.String,
    t.Key('.settings', default={}): STRING_DICT,
    t.Key('.config', default={}): CONFIG_OPTIONS,
})

STRUCTURE.allow_extra(
    '*',
    trafaret=t.Or(
        CONFIG_OPTIONS + t.Dict({
            t.Key(name='settings', default={}): STRING_DICT,
            t.Key(name='run'): t.List(t.String),
        }),
        t.List(t.String) >> (lambda s: {'settings': {}, 'run': s}),
    )
)


class DonkeySubprocessProtocol(asyncio.SubprocessProtocol):
    STD_FILES = {
        1: 'stdout',
        2: 'stderr',
    }

    def __init__(self, exit_future):
        self.exit_future = exit_future

    def pipe_data_received(self, fd, data):
        s = data.decode(locale.getpreferredencoding(False))
        l = logger.info if fd == 1 else logger.warning
        extra = {'stdfile': self.STD_FILES[fd]}
        for line in s.split('\n'):
            if line:
                l('%s', line, extra=extra)

    def process_exited(self):
        self.exit_future.set_result(True)


class CommandExecutor:
    def __init__(self, name, run_commands, *,
                 loop, settings=None, args=None, parallel=False, interpreter=None, script_mode=False):
        self.loop = loop
        self.name = name
        if script_mode:
            if args is not None:
                raise DonkeyError('"args" are invalid for a command in "script" mode')
            commands = ['\n'.join(run_commands)]
        elif args:
            commands = ['{} {}'.format(c, args) for c in run_commands]
        else:
            commands = run_commands

        interpreter = interpreter or self._get_default_interpreter()
        self.subprocess_args_list = [(interpreter, '-c', c) for c in commands]
        self.settings = settings
        self.parallel = parallel

    def create_coros(self) -> list:
        coros = []
        for args in self.subprocess_args_list:
            if len(self.subprocess_args_list) == 1:
                display_name = self.name
            else:
                display_name = '{}: {}'.format(self.name, ' '.join(args))
            coros.append(self._run(display_name, args))
        if self.parallel:
            return [asyncio.gather(*coros, loop=self.loop)]
        else:
            return coros

    async def _run(self, display_name: str, args: Tuple[str, ...]) -> int:
        main_logger.info('Running "%s"...', display_name)
        start = datetime.now()
        exit_future = asyncio.Future(loop=self.loop)

        def protocol_factory():
            return DonkeySubprocessProtocol(exit_future)

        transport, _ = await self.loop.subprocess_exec(protocol_factory, *args)

        await exit_future
        return_code = transport.get_returncode()
        transport.close()
        time_taken = (datetime.now() - start).total_seconds()
        main_logger.info('"%s" finished in %0.2fs, return code: %d', display_name, time_taken, return_code)
        return return_code

    @staticmethod
    def _get_default_interpreter() -> str:
        return 'bash'  # TODO


@contextmanager
def loop_context():
    if sys.platform == 'win32':
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
    else:
        loop = asyncio.get_event_loop()
    yield loop
    loop.close()


async def run_coros(coros, parallel, *, loop):
    if parallel:
        await asyncio.gather(*coros, loop=loop)
    else:
        for coro in coros:
            await coro


def execute(*, commands: List[str], parallel: bool=None, args: List[str]=None, definition_file: str=None):
    if definition_file:
        def_path = Path(definition_file).resolve()
    else:
        def_path = find_def_file()
    def_data = read_and_validate(str(def_path), STRUCTURE)
    default_command = def_data.pop('.default', None)
    if not commands:
        if not default_command:
            raise DonkeyError('no commands supplied and default command not set')
        commands = default_command,
    settings = def_data.pop('.settings')
    config = def_data.pop('.config')
    if parallel is None:
        parallel = config.get('parallel', False)

    to_run = []
    for c in commands:
        if c not in def_data:
            raise DonkeyError('command "{}" not found in "{}", '
                              'options: {}'.format(c, def_path, ', '.join(def_data.keys())))
        to_run.append((c, def_data[c]))

    with loop_context() as loop:
        coros = []
        for name, c in to_run:
            _settings = settings.copy()
            _settings.update(c.get('settings', {}))  # TODO this should be recursive
            command_executor = CommandExecutor(
                name,
                c['run'],
                loop=loop,
                settings=_settings,
                args=args,
                parallel=c.get('parallel', parallel),
                interpreter=c.get('interpreter') or config.get('interpreter'),
                script_mode=c.get('script_mode', config.get('script_mode', False)),
            )
            coros.extend(command_executor.create_coros())

        loop.run_until_complete(run_coros(coros, parallel, loop=loop))
