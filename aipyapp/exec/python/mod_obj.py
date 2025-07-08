import sys
import types
import importlib.abc
import importlib.util

class ObjectModuleLoader(importlib.abc.Loader):
    def __init__(self, fullname, obj):
        self.fullname = fullname
        self.obj = obj

    def create_module(self, spec):
        mod = types.ModuleType(self.fullname)
        # 注入所有非魔法属性，包括方法
        for attr in dir(self.obj):
            if not attr.startswith("__"):
                setattr(mod, attr, getattr(self.obj, attr))
        return mod

    def exec_module(self, module):
        pass

class ObjectModuleFinder(importlib.abc.MetaPathFinder):
    def __init__(self, package, object_map):
        self.package = package
        self.object_map = object_map

    def find_spec(self, fullname, path, target=None):
        if fullname == self.package:
            spec = importlib.util.spec_from_loader(fullname, loader=None)
            spec.submodule_search_locations = []
            return spec

        if not fullname.startswith(self.package + "."):
            return None

        subname = fullname[len(self.package) + 1:]
        if subname in self.object_map:
            loader = ObjectModuleLoader(fullname, self.object_map[subname])
            return importlib.util.spec_from_loader(fullname, loader)
        return None

class ObjectImporter:
    def __init__(self, object_map, package='aipyapp'):
        self.package = package
        self.finder = ObjectModuleFinder(package, object_map)

    def __enter__(self):
        self._old_meta_path = sys.meta_path[:]
        self._old_sys_modules = sys.modules.copy()
        sys.meta_path.insert(0, self.finder)
        sys.modules = sys.modules.copy()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.meta_path = self._old_meta_path
        sys.modules = self._old_sys_modules

if __name__ == "__main__":
    class Runtime:
        def do(self):
            print("runtime doing something")

    runtime = Runtime()

    obj_importer = ObjectImporter({"runtime": runtime})

    code = '''
from aipyapp import runtime
runtime.do()
'''

    with obj_importer:
        exec(code)
