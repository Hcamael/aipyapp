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
        return f"<{self.name}>\n{self.detail.strip()}\n</{self.name}>"

class Tips:
    """提示信息管理器"""
    def __init__(self):
        self.role: Tip
        self.tips: Dict[str, Tip] = {}

    @property
    def name(self):
        return self.role.name
    
    def add_tip(self, tip: Tip):
        self.tips[tip.name] = tip

    def get_tip(self, name: str) -> Optional[Tip]:
        """获取指定名称的提示信息"""
        return self.tips.get(name)

    def __iter__(self):
        return iter(self.tips.items())

    def __len__(self):
        return len(self.tips)

    def __getitem__(self, name: str) -> Tip:
        return self.tips[name]
    
    def __str__(self):
        lines = ['<tips>']
        for name, tip in self.tips.items():
            lines.append(str(tip))
        lines.append('</tips>')
        return '\n'.join(lines)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Tips':
        """从字典创建提示信息管理器"""
        tips = cls()
        tips_data = data.get('tips', {})
        for tip_name, tip_data in tips_data.items():
            tip = Tip.from_dict(tip_name, tip_data)
            if tip_name == 'role':
                tip.name = tip_data.get('name', '')
                tips.role = tip
            else:
                tips.add_tip(tip)
        return tips

    @classmethod
    def load(cls, toml_path: Optional[str] = None) -> 'Tips':
        """从 TOML 文件加载提示信息
        
        Args:
            toml_path: TOML 文件路径，如果为 None 则使用默认路径
            
        Returns:
            Tips: 提示信息管理器
        """
        with open(toml_path, 'rb') as f:
            data = tomllib.load(f)
        
        return cls.from_dict(data)

class TipsManager:
    def __init__(self, tips_dir: str = None):
        self.tips_dir = tips_dir
        self.tips: Dict[str, Tips] = {}
        self.default_tips: Tips
        self.current_tips: Tips
        self.log = logger.bind(src='tips')

    def load_tips(self):
        sys_tips_dir = os.path.join(os.path.dirname(__file__), '..', 'res', 'tips')
        for tips_dir in [sys_tips_dir, self.tips_dir]:
            if not tips_dir or not os.path.exists(tips_dir):
                continue
            for fname in os.listdir(tips_dir):
                if fname.endswith(".toml") and not fname.startswith("_"):
                    tips = Tips.load(os.path.join(tips_dir, fname))
                    self.log.info(f"Loaded tips: {tips.name}/{len(tips)}")
                self.tips[tips.name.lower()] = tips

        self.default_tips = self.tips['aipy']
        self.current_tips = self.default_tips

    def use(self, name: str):
        name = name.lower()
        if name in self.tips:
            self.log.info(f"Using tips: {name}")
            self.current_tips = self.tips[name]
            return True
        return False

if __name__ == '__main__':
    # 创建角色实例
    tips_manager = TipsManager()
    tips_manager.load_tips()
    for name, tips in tips_manager.tips.items():
        role = tips.role
        print(name)
        print(f"Tips: {name}")
        print(f"Role: {role.name}")
        print(f"Short: {role.short}")
        print(f"Detail: {role.detail}")
        print("-" * 100)

        # 打印角色信息
        print(f"角色名称: {role.name}")
        print(f"简短描述: {role.short}")
        print(f"详细描述: {role.detail}")
        
        # 打印所有提示信息
        print("\n提示信息:")
        for name, tip in tips:
            print(f"\n{tip.name}:")
            print(f"简短描述: {tip.short}")
            print(f"详细描述: {tip.detail}")