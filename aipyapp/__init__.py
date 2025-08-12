from importlib import resources

from .i18n import T, set_lang, get_lang
from .interface import Event, EventBus, EventListener, EventHandler, Stoppable
from .plugin import Plugin, PluginError, PluginConfigError, PluginInitError, TaskPlugin, PluginType

try:
    from .__version__ import __version__
except ImportError:
    from importlib.metadata import version
    __version__ = version(__package__)

__respkg__ = f'{__package__}.res'
__respath__ = resources.files(__respkg__)
__pkgpath__ = resources.files(__package__)
