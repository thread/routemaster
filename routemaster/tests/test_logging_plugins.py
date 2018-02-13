import pytest

from logger_plugin import TestLogger as _TestLogger  # So pytest doesn't run it

from routemaster.config import LoggingPluginConfig
from routemaster.logging import register_loggers, PluginConfigurationException


def test_loads_plugins(custom_app_config):
    kwargs = {'foo': 'bar'}

    app_config = custom_app_config(logging_plugins=[
        LoggingPluginConfig(
            dotted_path='logger_plugin.TestLogger',
            kwargs=kwargs,
        ),
    ])

    loggers = register_loggers(app_config.config)

    assert len(loggers) == 1
    assert isinstance(loggers[0], _TestLogger)
    assert loggers[0].config == app_config.config
    assert loggers[0].kwargs == kwargs


def test_raises_for_invalid_plugin_base_class(custom_app_config):
    app_config = custom_app_config(logging_plugins=[
        LoggingPluginConfig(
            dotted_path='logger_plugin.InvalidLogger',
            kwargs={},
        ),
    ])

    with pytest.raises(PluginConfigurationException):
        register_loggers(app_config.config)
