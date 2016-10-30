import click
from .logs import setup_logging
from .main import execute
from .version import VERSION

PARALLEL_HELP = (
    '(default: serial) Whether to run multiple commands in parallel or serial, '
    'only relevant if multiple commands are being called.'
)
ARGS_HELP = (
    'extra args to pass to the command, '
    'only valid if one single line command is being executed'
)
DF_HELP = (
    'definition file to use, if absent the closest defintion file is found and used'
)
# extra options to add in future
# watch/interval
# recover


@click.command()
@click.version_option(VERSION, '-V', '--version', prog_name='donkey')
@click.argument('commands', nargs=-1)
@click.option('--parallel/--serial', 'parallel', default=False, help=PARALLEL_HELP)
@click.option('-a', '--args', help=ARGS_HELP)
@click.option('-d', '--definition-file', type=click.Path(exists=True, dir_okay=False, file_okay=True), help=DF_HELP)
@click.option('-v', '--verbose', is_flag=True)
def cli(*, verbose, **kwargs):
    """
    Like "make" but for the 21st century.

    command(s) are run from the specified definition file or the "closest" definition file found.
    If no commands are passed the default (or first if no default is set) command is executed.
    The special command "check" looks for a definition file and checks it is valid but does nothing more,
    if the command "check" is included all other commands are skipped.

    "closest" means current directory or nearest direct parent directory, standard definition file names
    which are looked for are "donkey.yml/yaml" or "makefile.yml/yaml".
    """
    setup_logging(verbose)
    execute(**kwargs)

