import sys
import importlib.abc
import importlib.util

from loguru import logger

class DictModuleLoader(importlib.abc.Loader):
    def __init__(self, fullname, source):
        self.fullname = fullname
        self.source = source

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        code_obj = self.source
        if isinstance(self.source, str):
            code_obj = compile(self.source, f"<{self.fullname}>", "exec")
        exec(code_obj, module.__dict__)

class DictModuleFinder(importlib.abc.MetaPathFinder):
    def __init__(self, package, source_map):
        self.package = package
        self.source_map = source_map

    def find_spec(self, fullname, path, target=None):
        if fullname == self.package:
            # 返回一个虚拟包的 spec，必须带 submodule_search_locations 说明这是包
            spec = importlib.util.spec_from_loader(fullname, loader=None)
            spec.submodule_search_locations = []
            return spec

        if not fullname.startswith(self.package + "."):
            return None
        subname = fullname[len(self.package) + 1:]
        if subname in self.source_map:
            loader = DictModuleLoader(fullname, self.source_map[subname])
            return importlib.util.spec_from_loader(fullname, loader)
        return None


class DictModuleImporter:
    def __init__(self, package="blocks"):
        self.package = package
        self.source_map = {}
        self.finder = DictModuleFinder(self.package, self.source_map)
        self.log = logger.bind(src='BlockImporter')

    def add_module(self, name, code):
        self.log.info('Add module', name=name)
        self.source_map[name] = code
        fullname = f"{self.package}.{name}"
        if fullname in sys.modules:
            del sys.modules[fullname]

    def reload(self, fullname):
        import importlib
        if fullname in sys.modules:
            return importlib.reload(sys.modules[fullname])
        __import__(fullname)
        return sys.modules[fullname]

    def __enter__(self):
        self._old_meta_path = sys.meta_path[:]
        sys.meta_path.insert(0, self.finder)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        sys.meta_path = self._old_meta_path

# ========== 测试 ==========

if __name__ == "__main__":
    importer = DictModuleImporter("pkg")
    importer.add_module("mod1", "def hello(): return 'hello from mod1'")

    code = '''
from pkg import mod1
print(mod1.hello())
'''

    with importer:
        exec(code)

    # 修改模块代码，重新加载
    importer.add_module("mod1", "def hello(): return 'updated mod1'")

    with importer:
        exec(code)
