from importlib import resources

from .i18n import T, set_lang, get_lang

__version__ = '0.2.3b1'

__respkg__ = f'{__package__}.res'
__respath__ = resources.files(__respkg__)

__all__ = ['T', 'set_lang', 'get_lang', '__version__', '__respkg__', '__respath__']