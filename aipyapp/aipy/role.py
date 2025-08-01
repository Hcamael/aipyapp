#! /usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import tomllib
import os

from loguru import logger

@dataclass
class Tip:
    """提示信息对象"""
    name: str
    short: str
    detail: str

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, str]) -> 'Tip':
        """从字典创建提示信息对象"""
        return cls(
            name=name,
            short=data.get('short', ''),
            detail=data.get('detail', '')
        )
    
    def __str__(self):
        return f"<tip name=\"{self.name}\">\n{self.detail.strip()}\n</tip>"

class Role:
    """提示信息管理器"""
    def __init__(self):
        self.name: str = ''
        self.short: str = ''
        self.detail: str = ''
        self.envs: Dict[str, tuple[str, str]] = {}
        self.packages: Dict[str, set[str]] = {}
        self.tips: Dict[str, Tip] = {}
        self.plugins: Dict[str, Dict[str, Any]] = {}

    def get_tip(self, name: str) -> Optional[Tip]:
        """获取指定名称的提示信息"""
        return self.tips.get(name, None)

    def add_env(self, name: str, value: str, desc: str):
        self.envs[name] = (value, desc)

    def add_package(self, name: str, packages: List[str]):
        self.packages[name] = set(packages)

    def add_tip(self, name: str, short: str, detail: str):
        self.tips[name] = Tip(name, short, detail)

    def add_plugin(self, name: str, data: Dict[str, Any]):
        self.plugins[name] = data

    def __iter__(self):
        return iter(self.tips.items())

    def __len__(self):
        return len(self.tips)

    def __getitem__(self, name: str) -> Tip:
        return self.tips[name]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Role':
        """从字典创建角色对象"""
        role = cls()
        
        # 设置角色基本信息
        role.name = data.get('name', '')
        role.short = data.get('short', '')
        role.detail = data.get('detail', '')
        
        # 加载环境变量
        env_data = data.get('envs', {})
        for env_name, env_info in env_data.items():
            if isinstance(env_info, list):
                value = env_info[0]
                desc = env_info[1]
            else:
                value = str(env_info)
                desc = ''
            role.add_env(env_name, value, desc)
        
        # 加载包信息
        packages_data = data.get('packages', {})
        for lang, packages in packages_data.items():
            role.add_package(lang, packages)
        
        # 加载提示信息
        tips_data = data.get('tips', {})
        for tip_name, tip_data in tips_data.items():
            short = tip_data.get('short', '')
            detail = tip_data.get('detail', '')
            role.add_tip(tip_name, short, detail)
        
        # 加载插件信息
        plugins_data = data.get('plugins', {})
        for plugin_name, plugin_data in plugins_data.items():
            role.add_plugin(plugin_name, plugin_data)
        
        return role

    @classmethod
    def load(cls, toml_path: str) -> 'Role':
        """从 TOML 文件加载角色信息
        
        Args:
            toml_path: TOML 文件路径
            
        Returns:
            Role: 角色对象
        """
        with open(toml_path, 'rb') as f:
            data = tomllib.load(f)
        
        return cls.from_dict(data)

class RoleManager:
    def __init__(self, roles_dir: str = None, api_conf: Dict[str, Dict[str, Any]] = None):
        self.roles_dir = roles_dir
        self.roles: Dict[str, Role] = {}
        self.default_role: Role = None
        self.current_role: Role = None
        self.log = logger.bind(src='roles')
        self.api_conf = api_conf

    def _add_api(self, role: Role):
        for api_name, api_conf in self.api_conf.items():
            desc = api_conf.get('desc')
            if not desc:
                self.log.warning(f"API {api_name} has no description")
                continue
            role.add_tip(api_name, '', desc)
            envs = api_conf.get('env')
            if not envs:
                continue
            for name, (value, desc) in envs.items():
                role.add_env(name, value, desc)

    def load_roles(self):
        sys_roles_dir = os.path.join(os.path.dirname(__file__), '..', 'res', 'roles')
        for roles_dir in [sys_roles_dir, self.roles_dir]:
            if not roles_dir or not os.path.exists(roles_dir):
                continue
            for fname in os.listdir(roles_dir):
                if fname.endswith(".toml") and not fname.startswith("_"):
                    role = Role.load(os.path.join(roles_dir, fname))
                    self.log.info(f"Loaded role: {role.name}/{len(role)}")
                    self.roles[role.name.lower()] = role
                    self._add_api(role)

        if self.roles:
            self.default_role = list(self.roles.values())[0]
            self.current_role = self.default_role

    def use(self, name: str):
        name = name.lower()
        if name in self.roles:
            self.log.info(f"Using role: {name}")
            self.current_role = self.roles[name]
            return True
        return False

if __name__ == '__main__':
    # 创建角色管理器实例
    role_manager = RoleManager()
    role_manager.load_roles()
    
    for name, role in role_manager.roles.items():
        # 打印角色信息
        print(f"角色名称: {role.name}")
        print(f"简短描述: {role.short}")
        print(f"详细描述: {role.detail}")
        print("-" * 100)

        print(role.envs)
        print(role.packages)
        
        # 打印所有提示信息
        print("\n提示信息:")
        for name, tip in role:
            print(f"\n{tip.name}:")
            print(f"简短描述: {tip.short}")
            print(f"详细描述: {tip.detail}")