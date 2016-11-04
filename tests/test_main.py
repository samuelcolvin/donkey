from unittest.mock import patch

import pytest

from donkey.main import DonkeyError, DonkeyFailure, execute

from .conftest import mktree

async def test_successful_command(tmpworkdir):
    mktree(tmpworkdir, {
        'makefile.yml': 'foo:\n- "echo foovalue > foo.txt"\n',
    })
    execute('foo')
    assert tmpworkdir.join('foo.txt').read_text('utf8') == 'foovalue\n'


async def test_script_mode(tmpworkdir):
    mktree(tmpworkdir, {
        'makefile.yml': """\
foo:
  script: true
  run:
  - VALUE="hello world"
  - echo $VALUE > foo.txt"""
    })
    execute('foo')
    assert tmpworkdir.join('foo.txt').read_text('utf8') == 'hello world\n'


async def test_arguments(tmpworkdir, caplog):
    mktree(tmpworkdir, {
        'makefile.yml': """\
foo:
- echo"""
    })
    execute('foo', args='hello world')
    print(caplog.log)
    assert """\
donkey.commands: hello world
donkey.main: "foo" finished in 0.0Xs, return codes: 0\n""" == caplog.normalised_log


async def test_argument_in_script_mode(tmpworkdir):
    mktree(tmpworkdir, {
        'makefile.yml': """\
foo:
  script: true
  run:
  - echo $VALUE > foo.txt
  """
    })
    with pytest.raises(DonkeyError):
        execute('foo', args='x')
    assert not tmpworkdir.join('foo.txt').exists()


async def test_default_command(tmpworkdir):
    mktree(tmpworkdir, {
        'makefile.yml': """
foo:
- "echo foovalue > foo.txt"
.default: foo
    """,
    })
    execute()
    assert tmpworkdir.join('foo.txt').read_text('utf8') == 'foovalue\n'


async def test_no_default_command(tmpworkdir):
    mktree(tmpworkdir, {
        'makefile.yml': """
foo:
- "echo foovalue > foo.txt"
    """,
    })
    with pytest.raises(DonkeyError):
        execute()


async def test_invalid_command(tmpworkdir):
    mktree(tmpworkdir, {
        'makefile.yml': """
foo:
- "echo foovalue > foo.txt"
    """,
    })
    with pytest.raises(DonkeyError):
        execute('missing')


async def test_invalid_option(tmpworkdir):
    mktree(tmpworkdir, {
        'makefile.yml': """
foo:
  bar: bad
  run:
  - echo foobar
    """,
    })
    with pytest.raises(DonkeyError):
        execute('missing')


async def test_custom_file_name(tmpworkdir):
    mktree(tmpworkdir, {
        'different.yml': 'foo:\n- "echo foovalue > foo.txt"\n',
    })
    execute('foo', definition_file='different.yml')
    assert tmpworkdir.join('foo.txt').read_text('utf8') == 'foovalue\n'


files = {
    'makefile.yml': """
foo:
- "echo foovalue > foo.txt"
fails:
  interpreter: python
  script: true
  run:
  - import sys
  - sys.exit(123)
"""}


async def test_single_failed(tmpworkdir):
    mktree(tmpworkdir, files)
    with pytest.raises(DonkeyFailure) as excinfo:
        execute('fails')
    assert excinfo.value.args == ('commands failed, return codes: 123', 123)


async def test_multiple_failed1(tmpworkdir):
    mktree(tmpworkdir, files)
    with pytest.raises(DonkeyFailure) as excinfo:
        execute('fails', 'foo')
    assert excinfo.value.args == ('commands failed, return codes: 123', 123)
    assert not tmpworkdir.join('foo.txt').exists()


async def test_multiple_failed2(tmpworkdir):
    mktree(tmpworkdir, files)
    with pytest.raises(DonkeyFailure) as excinfo:
        execute('foo', 'fails')
    assert excinfo.value.args == ('commands failed, return codes: 0, 123', 123)
    assert tmpworkdir.join('foo.txt').exists()


async def test_multiple_failed_parallel(tmpworkdir):
    mktree(tmpworkdir, files)
    with pytest.raises(DonkeyFailure) as excinfo:
        execute('foo', 'fails', parallel=True)
    assert excinfo.value.args == ('commands failed, return codes: 0, 123', 123)
    assert tmpworkdir.join('foo.txt').exists()


async def test_logging_error(tmpworkdir):
    mktree(tmpworkdir, {
        'makefile.yml': 'foo:\n- echo hello\n',
    })
    with patch('donkey.main.locale.getpreferredencoding') as mock_getpreferredencoding:
        error = RuntimeError('foobar')
        mock_getpreferredencoding.side_effect = error
        with pytest.raises(RuntimeError) as excinfo:
            execute('foo')
        assert excinfo.value == error


async def test_break_on_fail(tmpworkdir):
    mktree(tmpworkdir, {
        'makefile.yml': """
foo:
- exit 1
- "echo foovalue > foo.txt"
    """,
    })
    with pytest.raises(DonkeyFailure) as excinfo:
        execute('foo', 'foo')
    assert excinfo.value.args == ('commands failed, return codes: 1', 1)
    assert not tmpworkdir.join('foo.txt').exists()


async def test_break_on_fail_after(tmpworkdir):
    mktree(tmpworkdir, {
        'makefile.yml': """
foo:
- "echo foovalue > foo.txt"
- exit 1
    """,
    })
    with pytest.raises(DonkeyFailure) as excinfo:
        execute('foo', 'foo')
    assert excinfo.value.args == ('commands failed, return codes: 0, 1', 1)
    assert tmpworkdir.join('foo.txt').exists()
