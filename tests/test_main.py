from donkey.main import execute

from .conftest import mktree

async def test_successful_command(tmpworkdir):
    mktree(tmpworkdir, {
        'makefile.yml': 'foo:\n- "echo foovalue > foo.txt"\n',
    })
    execute(commands=['foo'])
    assert tmpworkdir.join('foo.txt').read_text('utf8') == 'foovalue\n'
