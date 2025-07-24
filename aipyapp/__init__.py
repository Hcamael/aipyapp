from importlib import resources

from .i18n import T, set_lang, get_lang

try:
    from .__version__ import __version__
except ImportError:
    from importlib.metadata import version
    __version__ = version(__package__)

__respkg__ = f'{__package__}.res'
__respath__ = resources.files(__respkg__)

__all__ = ['T', 'set_lang', 'get_lang', '__version__', '__respkg__', '__respath__']