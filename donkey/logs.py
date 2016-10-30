import logging
import logging.config

import click

LOG_COLOURS = {
    logging.DEBUG: 'white',
    logging.INFO: 'green',
    logging.WARN: 'yellow',
}


class MainHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        colour = LOG_COLOURS.get(record.levelno, 'red')
        click.secho(log_entry, fg=colour)


class DefaultHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        kwargs = {}
        if record.levelno == logging.DEBUG:
            kwargs['dim'] = True
        # kwargs['fg'] = 'green'  # TODO
        click.secho(log_entry, **kwargs)


def log_config(verbose: bool) -> dict:
    """
    Setup default config. for dictConfig.
    :param verbose: level: DEBUG if True, INFO if False
    :return: dict suitable for ``logging.config.dictConfig``
    """
    log_level = 'DEBUG' if verbose else 'INFO'
    return {
        'version': 1,
        'disable_existing_loggers': True,
        'formatters': {
            'main': {
                'format': '%(message)s',
            },
            'default': {
                'format': '%(asctime)s %(message)s',
                'datefmt': '%H:%M:%S',
            },
        },
        'handlers': {
            'main': {
                'level': log_level,
                'class': 'donkey.logs.MainHandler',
                'formatter': 'main'
            },
            'default': {
                'level': log_level,
                'class': 'donkey.logs.DefaultHandler',
                'formatter': 'default'
            },
        },
        'loggers': {
            'donkey.main': {
                'handlers': ['main'],
                'level': log_level,
                'propagate': False,
            },
            'donkey': {
                'handlers': ['default'],
                'level': log_level,
                'foobar': 123,
            },
        },
    }


def setup_logging(verbose):
    config = log_config(verbose)
    logging.config.dictConfig(config)
