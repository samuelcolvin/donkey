from click.testing import CliRunner

from donkey.cli import cli

from .conftest import mktree, normalise_log


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert 'Like make but for the 21st century.' in result.output


files = {
    'makefile.yml': """
foo:
- echo foo
bar:
- echo bar
fails:
  interpreter: python
  script: true
  run:
  - import sys
  - print('hello')
  - sys.exit(123)
  - print('good bye')
"""}


async def test_single_command(tmpworkdir):
    mktree(tmpworkdir, files)
    runner = CliRunner()
    result = runner.invoke(cli, ['foo'])
    assert result.exit_code == 0
    assert """\
Running "foo"...
TI:XX:ME (1) foo
"foo" finished in 0.0Xs, return code: 0\n""" == normalise_log(result.output)


async def test_multiple_commands(tmpworkdir):
    mktree(tmpworkdir, files)
    runner = CliRunner()
    result = runner.invoke(cli, ['foo', 'bar'])
    assert result.exit_code == 0
    assert """\
Running "foo"... ●
TI:XX:ME ● (1) foo
"foo" finished in 0.0Xs, return code: 0 ●
Running "bar"... ●
TI:XX:ME ● (1) bar
"bar" finished in 0.0Xs, return code: 0 ●\n""" == normalise_log(result.output)


async def test_no_file(tmpworkdir):
    runner = CliRunner()
    result = runner.invoke(cli)
    assert result.exit_code == 2
    assert result.output == ('Error: Unable to find definition file with standard name "donkey.yml" or "makefile.yml" '
                             'in the current working directory or any parent directory\n')


async def test_failed_command(tmpworkdir):
    mktree(tmpworkdir, files)
    runner = CliRunner()
    result = runner.invoke(cli, ['fails'])
    assert result.exit_code == 123
    print(result.output)
    assert """\
Running "fails"...
TI:XX:ME (1) hello
"fails" finished in 0.0Xs, return code: 123
Error: commands failed, return codes: 123\n""" == normalise_log(result.output)
