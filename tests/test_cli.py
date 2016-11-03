import re

from click.testing import CliRunner

from donkey.cli import cli

from .conftest import mktree


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert 'Like make but for the 21st century.' in result.output


def _normalise_log(s):
    s = re.sub('\d\d:\d\d:\d\d', 'TI:XX:ME', s)
    s = re.sub('0.0\ds', '0.0Xs', s)
    return s


async def test_successful_command(tmpworkdir):
    mktree(tmpworkdir, {
        'makefile.yml': 'foo:\n- echo foo\n',
    })
    runner = CliRunner()
    result = runner.invoke(cli, ['foo'])
    assert result.exit_code == 0
    assert _normalise_log(result.output) == """\
Running "foo"...
TI:XX:ME foo
"foo" finished in 0.0Xs, return code: 0\n"""


async def test_no_file(tmpworkdir):
    runner = CliRunner()
    result = runner.invoke(cli)
    assert result.exit_code == 2
    assert result.output == ('Error: Unable to find definition file with standard name "donkey.yml" or "makefile.yml" '
                             'in the current working directory or any parent directory\n')
