import os
from dataclasses import dataclass, field
from typing import Set, Dict, Any, Optional
from enum import Enum, auto

import yaml
from loguru import logger

class ModelCapability(Enum):
    TEXT = auto()
    IMAGE_INPUT = auto()
    IMAGE_OUTPUT = auto()
    AUDIO_INPUT = auto()
    AUDIO_OUTPUT = auto()
    VIDEO_INPUT = auto()
    VIDEO_OUTPUT = auto()
    FILE_INPUT = auto()
    FILE_OUTPUT = auto()
    CODE = auto()
    FUNCTION_CALLING = auto()
    REASONING = auto()
    NATIVE_SEARCH = auto()
    EXTENDED_THINKING = auto()
    CODE_EXECUTION = auto()
    STRUCTURED_OUTPUT = auto()

@dataclass(frozen=True)
class ModelInfo:
    name: str
    description: str
    capabilities: Set[ModelCapability]
    context_length: int
    company: str
    alias: Set[str] = field(default_factory=set)
    extra: Optional[Dict[str, Any]] = None

    def has_capability(self, cap: ModelCapability) -> bool:
        return cap in self.capabilities

class ModelRegistry:
    def __init__(self, config_path: str):
        self.models: Dict[str, ModelInfo] = {}
        self.alias_map: Dict[str, str] = {}
        self.logger = logger.bind(src=self.__class__.__name__)
        self._load_from_yaml(config_path)

    def _load_from_yaml(self, path: str):
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        for company, models_dict in data.items():
            for model_name, v in models_dict.items():
                aliases = set(v.get('alias', []))
                info = ModelInfo(
                    name=model_name,  # 直接用 key 作为 name
                    description=v['description'],
                    capabilities={ModelCapability[cap] for cap in v['capabilities']},
                    context_length=v['context_length'],
                    company=company,
                    alias=aliases,
                    extra={k: v for k, v in v.items() if k not in ('description', 'capabilities', 'context_length', 'alias')}
                )
                self.models[model_name] = info
                for a in aliases:
                    self.alias_map[a] = model_name
        self.logger.info(f"Loaded {len(self.models)} models from {path}")

    def get_model_info(self, model_name: str) -> Optional[ModelInfo]:
        main_name = self.alias_map.get(model_name, model_name)
        return self.models.get(main_name)

    def get_models_by_company(self, company: str) -> Dict[str, ModelInfo]:
        return {k: v for k, v in self.models.items() if v.company == company}

    def all_models(self) -> Dict[str, ModelInfo]:
        return self.models

    def reload(self, config_path: str):
        self.models.clear()
        self.alias_map.clear()
        self._load_from_yaml(config_path)

# ================== 测试代码 ==================
if __name__ == "__main__":
    # 假设 res/models.yaml 路径
    yaml_path = os.path.join(os.path.dirname(__file__), '../res/models.yaml')
    yaml_path = os.path.abspath(yaml_path)
    print(f"加载模型配置: {yaml_path}")
    registry = ModelRegistry(yaml_path)

    # 测试：获取模型信息
    info = registry.get_model_info('gpt-4o')
    print("gpt-4o:", info)
    # 测试：通过 alias 查询
    info2 = registry.get_model_info('gpt-4o-2024-05-13')
    print("gpt-4o-2024-05-13 (alias):", info2)
    # 测试：alias 查询能力
    if info2:
        print("gpt-4o-2024-05-13 是否支持图片理解:", info2.has_capability(ModelCapability.IMAGE_UNDERSTAND))
        print("gpt-4o-2024-05-13 是否支持图片生成:", info2.has_capability(ModelCapability.IMAGE_GENERATE))
    # 测试：获取公司下所有模型
    openai_models = registry.get_models_by_company('OpenAI')
    print("OpenAI models:", list(openai_models.keys()))
    # 测试：所有模型
    print("所有模型:", list(registry.all_models().keys()))
    # 遍历所有模型，输出其能力
    print("\n所有模型及其能力:")
    for name, model in registry.all_models().items():
        print(f"- {name}: {[c.name for c in model.capabilities]}")
    # 测试不存在模型
    not_found = registry.get_model_info('not-exist-model')
    print("not-exist-model:", not_found)
    # 测试不存在 alias
    not_found_alias = registry.get_model_info('not-exist-alias')
    print("not-exist-alias:", not_found_alias)
    # 输出每个模型的所有 alias
    print("\n每个模型的 alias:")
    for name, model in registry.all_models().items():
        print(f"- {name}: {sorted(model.alias) if model.alias else '无'}") 