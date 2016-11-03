from datetime import datetime

from donkey.main import execute

from .conftest import mktree

async def test_multiple(tmpworkdir, caplog):
    mktree(tmpworkdir, {
        'makefile.yml': """
foo:
- sleep 0.1
- echo foo
bar:
- sleep 0.1
- echo bar
spam:
- sleep 0.1
- echo spam
    """,
    })
    start = datetime.now()
    execute('foo', 'bar', 'spam', parallel=True)
    diff = (datetime.now() - start).total_seconds()
    assert 0.1 < diff < 0.15
    log = caplog.normalised_log
    print(log)
    assert 'donkey.main: Running "foo: echo foo"...' in log
    assert 'donkey.command: foo' in log
    assert 'donkey.command: bar' in log
    assert 'donkey.command: spam' in log


async def test_single_parallel(tmpworkdir):
    mktree(tmpworkdir, {
        'makefile.yml': """
foo:
  parallel: true
  run:
  - sleep 0.1
  - sleep 0.1
  - sleep 0.1
  - "echo foovalue > foo.txt"
    """,
    })
    start = datetime.now()
    execute('foo', parallel=True)
    diff = (datetime.now() - start).total_seconds()
    assert 0.1 < diff < 0.15
    assert tmpworkdir.join('foo.txt').read_text('utf8') == 'foovalue\n'
