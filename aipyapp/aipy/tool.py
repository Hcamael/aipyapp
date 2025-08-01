import inspect
from typing import Any, Callable, Dict, Optional, List 

from loguru import logger
from pydantic import create_model, ValidationError

# 函数注册表：func_name -> meta 信息
LLM_FUNCTION_REGISTRY: Dict[str, Dict[str, Any]] = {}

class LLMCallError(Exception):
    """LLM 调用相关的基础异常"""
    pass

class FunctionNotFoundError(LLMCallError):
    """函数/方法未找到异常"""
    pass

class ParameterValidationError(LLMCallError):
    """参数验证异常"""
    pass

def llm_callable(group: str = "default") -> Callable:
    def decorator(fn: Callable) -> Callable:
        sig = inspect.signature(fn)

        fields = {}
        for name, param in sig.parameters.items():
            annotation = param.annotation if param.annotation != inspect.Parameter.empty else Any
            default = param.default if param.default != inspect.Parameter.empty else ...
            fields[name] = (annotation, default)

        ParamModel = create_model(f"{fn.__name__}_Params", **fields)

        LLM_FUNCTION_REGISTRY[fn.__name__] = {
            "func": fn,
            "group": group,
            "signature": str(sig),
            "doc": inspect.getdoc(fn) or "",
            "param_model": ParamModel
        }

        return fn
    return decorator


def llm_call(func_name: str, **kwargs) -> Any:
    entry = LLM_FUNCTION_REGISTRY.get(func_name)
    if not entry:
        logger.error(f"调用未注册函数：{func_name}")
        raise FunctionNotFoundError(f"函数 '{func_name}' 未注册。")

    fn = entry["func"]
    ParamModel = entry.get("param_model")

    try:
        parsed = ParamModel(**kwargs)
        logger.info(f"调用函数 {func_name}，参数: {parsed.model_dump()}")
        return fn(**parsed.model_dump())

    except ValidationError as e:
        logger.error(f"函数 '{func_name}' 参数校验失败:\n{e}")
        raise ParameterValidationError(f"参数校验失败：\n{e}")


def get_llm_tools_description(group: Optional[str] = None, as_text: bool = False) -> str | Dict[str, Dict[str, str]]:
    tools_info: Dict[str, Dict[str, str]] = {}

    for name, meta in LLM_FUNCTION_REGISTRY.items():
        if group is None or meta["group"] == group:
            tools_info[name] = {
                "signature": meta["signature"],
                "doc": meta["doc"],
                "group": meta["group"]
            }

    if as_text:
        grouped: Dict[str, list[str]] = {}
        for name, meta in tools_info.items():
            grp = meta["group"]
            grouped.setdefault(grp, []).append(
                f"- {name}{meta['signature']}\n  {meta['doc']}"
                if meta["doc"] else f"- {name}{meta['signature']}"
            )
        lines = ["你可以使用以下函数（通过 llm_call(\"函数名\", 参数=值) 调用）："]
        for group_name, func_lines in grouped.items():
            lines.append(f"\n📂 {group_name}：")
            lines.extend(func_lines)
        return "\n".join(lines)

    return tools_info


def get_llm_tools_json_schema(group: Optional[str] = None) -> List[dict]:
    tools = []
    for name, meta in LLM_FUNCTION_REGISTRY.items():
        if group and meta["group"] != group:
            continue
        model = meta.get("param_model")
        if model is None:
            continue
        schema = model.model_json_schema()
        tools.append({
            "name": name,
            "description": meta["doc"],
            "parameters": schema
        })
    return tools


def get_llm_tools_multimodal_prompt(group: Optional[str] = None) -> str:
    tools = get_llm_tools_json_schema(group)
    lines = [
        "你可以调用以下函数。每个函数包含：",
        "- 函数说明（自然语言，供你理解用途）",
        "- 参数格式（JSON Schema 格式，供你按规范生成参数）\n"
    ]
    for tool in tools:
        lines.append(f"函数名：{tool['name']}")
        lines.append(f"功能：{tool['description']}")
        lines.append("参数要求（JSON Schema）：")
        import json
        schema_json = json.dumps(tool["parameters"], indent=2, ensure_ascii=False)
        lines.append(schema_json)
        lines.append("-" * 30)
    return "\n".join(lines)

def register_instance_method(obj: Any, method_name: str, group: str = "default"):
    method = getattr(obj, method_name, None)
    if method is None:
        raise FunctionNotFoundError(f"对象 {obj} 没有方法 '{method_name}'")

    sig = inspect.signature(method)
    doc = inspect.getdoc(method) or ""

    fields = {}
    for name, param in sig.parameters.items():
        if name == "self":
            continue
        annotation = param.annotation if param.annotation != inspect.Parameter.empty else Any
        default = param.default if param.default != inspect.Parameter.empty else ...
        fields[name] = (annotation, default)

    ParamModel = create_model(f"{method_name}_Params", **fields)

    def wrapper(**kwargs):
        return method(**kwargs)

    wrapper.__name__ = method_name
    wrapper.__doc__ = doc

    LLM_FUNCTION_REGISTRY[method_name] = {
        "func": wrapper,
        "group": group,
        "signature": str(sig),
        "doc": doc,
        "param_model": ParamModel
    }

    return wrapper


def register_instance_methods(obj: Any, methods: List[str], group: str = "default"):
    for method in methods:
        register_instance_method(obj, method, group)


if __name__ == "__main__":
    # 顶层函数
    @llm_callable(group="math")
    def add(x: int, y: int = 0) -> int:
        """返回两个整数的和"""
        return x + y

    assert llm_call("add", x="3", y=5) == 8

    # 缺省参数
    assert llm_call("add", x=2) == 2

    # 类型错误
    try:
        llm_call("add", x="foo", y="bar")
    except ParameterValidationError as e:
        print("✅ 捕获类型错误:", e)

    # 实例方法注册
    class Greeter:
        def greet(self, name: str, title: str = "朋友") -> str:
            """打招呼"""
            return f"你好，{title}{name}"

    g = Greeter()
    register_instance_method(g, "greet", group="social")
    assert llm_call("greet", name="小明") == "你好，朋友小明"
    assert llm_call("greet", name="李老师", title="尊敬的") == "你好，尊敬的李老师"

    # 提示信息输出
    print("\n[自然语言提示]\n")
    print(get_llm_tools_description(as_text=True))

    print("\n[JSON Schema 提示]\n")
    import json
    print(json.dumps(get_llm_tools_json_schema(), indent=2, ensure_ascii=False))

    print("\n[多模态提示]\n")
    print(get_llm_tools_multimodal_prompt())
