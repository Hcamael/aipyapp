#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from typing import Dict
from pathlib import Path

class BaseConfig:
    FILE = None

    def __init__(self, path: str):
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        self.config_file = path / self.FILE
        self.config = self.load_config()

    def load_config(self) -> Dict:
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_config(self, config: Dict):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)