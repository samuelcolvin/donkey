import asyncio
import itertools
import locale
import logging
import re
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from subprocess import PIPE
from typing import Any, Dict, List, Tuple

import trafaret as t
from trafaret_config import ConfigError, read_and_validate

from .logs import get_log_format, reset_log_format

command_logger = logging.getLogger('donkey.commands')
main_logger = logging.getLogger('donkey.main')

STD_FILE_NAMES = [
    re.compile('donkey\.ya?ml'),
    re.compile('makefile\.ya?ml'),
]


class DonkeyError(Exception):
    pass


class DonkeyFailure(RuntimeError):
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
        raise DonkeyError('Unable to find definition file with standard name "donkey.yml" or "makefile.yml" in the '
                          'current working directory or any parent directory')
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


class SetException:
    def __init__(self, future):
        self._future = future

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            self._future.set_exception(exc_val)


class DonkeySubprocessProtocol(asyncio.SubprocessProtocol):
    def __init__(self, exit_future, log_format):
        self.exit_future = exit_future
        self.log_format = log_format
        self.has_trailing_nl = True

    def pipe_data_received(self, fd, data):
        with SetException(self.exit_future):
            s = data.decode(locale.getpreferredencoding(False))
            l = command_logger.info if fd == 1 else command_logger.warning
            extra = {
                'fd': fd,
                'symbol': self.log_format['symbol'],
                'colour': self.log_format['colour'],
                'nl': True,
                'prev_nl': self.has_trailing_nl,
            }
            *lines, last = s.split('\n')
            for line in lines:
                self.has_trailing_nl = True
                l('%s', line, extra=extra)
            if last:
                extra['nl'] = False
                l('%s', last, extra=extra)
                self.has_trailing_nl = False

    def process_exited(self):
        with SetException(self.exit_future):
            if not self.has_trailing_nl:
                command_logger.info('<nl>')
            self.exit_future.set_result(True)


def now():
    return datetime.now()


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

    @property
    def command_count(self):
        return len(self.subprocess_args_list) if self.parallel else 1

    async def execute(self, track_multiple) -> list:
        if self.command_count == 1:
            return await self._run_multiple(self.subprocess_args_list, self.name, track_multiple)

        else:
            coros = [
                self._run_multiple([args], '{}: {}'.format(self.name, args[-1]), track_multiple)
                for args in self.subprocess_args_list
            ]
            result = await asyncio.gather(*coros, loop=self.loop)
            return [r[0] for r in result]

    async def _run_multiple(self, args_list: List[Tuple[str, ...]], display_name: str, track_multiple: bool) -> int:
        if track_multiple:
            log_format = get_log_format()
        else:
            log_format = {'symbol': '', 'colour': None}
        main_logger.debug('Running "%s"...', display_name, extra=log_format)

        start = now()
        return_codes = []
        for args in args_list:
            rt = await self._run(args, log_format)
            return_codes.append(rt)
            if rt:
                break
        time_taken = (now() - start).total_seconds()
        # tiny gap generally improves the order of log output without being long enough for the user to noticing
        await asyncio.sleep(0.02)

        main_logger.info('"%s" finished in %0.2fs, return codes: %s', display_name, time_taken,
                         ', '.join(map(str, return_codes)), extra=log_format)
        return return_codes

    async def _run(self, args: Tuple[str, ...], log_format: Dict[str, Any]):
        exit_future = asyncio.Future(loop=self.loop)

        def protocol_factory():
            return DonkeySubprocessProtocol(exit_future, log_format)

        # pytest breaks stdin intentionally, thus we check it's working because calling subprocess_exec
        try:
            sys.stdin.fileno()
        except ValueError:
            stdin = PIPE
        else:  # pragma: no cover
            # sadly no sane way to test this case
            stdin = sys.stdin
        transport, _ = await self.loop.subprocess_exec(protocol_factory, *args, stdin=stdin)

        await exit_future
        return_code = transport.get_returncode()
        transport.close()
        return return_code

    @staticmethod
    def _get_default_interpreter() -> str:
        return 'bash'  # TODO


@contextmanager
def loop_context():
    if sys.platform == 'win32':  # pragma: no cover
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


async def run_coros(executors, parallel, *, loop):
    track_multiple = sum(ex.command_count for ex in executors) > 1
    coros = [ex.execute(track_multiple) for ex in executors]
    if parallel:
        return_code_sets = await asyncio.gather(*coros, loop=loop)
    else:
        return_code_sets = []
        for coro in coros:
            return_codes = await coro
            return_code_sets.append(return_codes)
            if any(return_codes):
                break
    return list(itertools.chain(*return_code_sets))


def execute(*commands: str, parallel: bool=None, args: str=None, definition_file: str=None):
    reset_log_format()
    if definition_file:
        def_path = Path(definition_file).resolve()
    else:
        def_path = find_def_file()
    try:
        def_data = read_and_validate(str(def_path), STRUCTURE)
    except ConfigError as e:
        raise DonkeyError('Invalid definition file, {}'.format(e))
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
            raise DonkeyError('Command "{}" not found in "{}", '
                              'options: {}'.format(c, def_path, ', '.join(def_data.keys())))
        to_run.append((c, def_data[c]))

    with loop_context() as loop:
        executors = []
        for name, c in to_run:
            _settings = settings.copy()
            _settings.update(c.get('settings', {}))  # TODO this should be recursive
            executors.append(CommandExecutor(
                name,
                c['run'],
                loop=loop,
                settings=_settings,
                args=args,
                parallel=c.get('parallel', False),  # TODO add config option
                interpreter=c.get('interpreter') or config.get('interpreter'),
                script_mode=c.get('script_mode', config.get('script_mode', False)),
            ))
        return_codes = loop.run_until_complete(run_coros(executors, parallel, loop=loop))

    try:
        failed_return_code = next(rt for rt in return_codes if rt != 0)
    except StopIteration:
        return 0
    else:
        codes_str = ', '.join(map(str, sorted(return_codes)))
        raise DonkeyFailure('commands failed, return codes: {}'.format(codes_str), failed_return_code)
