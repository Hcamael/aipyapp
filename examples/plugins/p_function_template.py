#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AiPy 功能函数插件模板

这是一个完整的插件模板，用于快速创建提供功能函数的插件。
插件通过 fn_* 方法向 LLM 提供可调用的工具函数。

使用方法：
1. 复制此文件并重命名为 p_<your_plugin_name>.py
2. 修改插件基本信息（name, version, description, author）
3. 在 init() 方法中添加初始化逻辑
4. 添加 fn_* 方法实现功能函数
5. 可选择添加事件处理方法 on_*

文件放置位置：
- 系统插件：aipyapp/plugins/
- 用户插件：~/.aipyapp/plugins/
"""

from typing import Dict, List, Optional, Union, Any
from aipyapp import TaskPlugin, PluginInitError


class FunctionTemplatePlugin(TaskPlugin):
    """功能函数插件模板
    
    这个模板展示了如何创建一个提供功能函数的插件。
    插件可以向 LLM 提供各种实用的工具函数。
    """
    
    # ================================
    # 插件基本信息（必需修改）
    # ================================
    name = "function_template"          # 插件名称，用于配置和标识
    version = "1.0.0"                   # 版本号
    description = "功能函数插件模板"      # 插件描述
    author = "AiPy Team"                # 作者信息
    
    def __init__(self, config: Dict[str, Any] = None):
        """插件构造函数
        
        Args:
            config: 插件配置字典，来自角色配置文件
        """
        super().__init__(config)
    
    def init(self):
        """插件初始化方法（可选实现）
        
        在这里进行插件的初始化工作：
        - 验证必需的配置参数
        - 初始化外部服务连接
        - 设置插件内部状态
        
        Raises:
            PluginInitError: 当初始化失败时抛出
        """
        # 示例：获取配置参数
        self.api_key = self.config.get('api_key')
        self.base_url = self.config.get('base_url', 'https://api.example.com')
        self.timeout = self.config.get('timeout', 30)
        self.max_retries = self.config.get('max_retries', 3)
        
        # 示例：验证必需配置
        required_configs = ['api_key']
        for key in required_configs:
            if not self.config.get(key):
                raise PluginInitError(f"缺少必需配置参数: {key}")
        
        # 示例：初始化客户端或连接
        # self.client = SomeAPIClient(api_key=self.api_key, base_url=self.base_url)
        
        self.logger.info(f"插件 {self.name} 初始化完成")
    
    # ================================
    # 功能函数定义区域
    # ================================
    # 以 fn_ 开头的方法会自动注册为可供 LLM 调用的函数
    # 方法名去掉 fn_ 前缀后成为函数名
    
    def fn_example_basic(self, text: str) -> str:
        """基础示例函数
        
        Args:
            text: 输入文本
            
        Returns:
            str: 处理后的文本

        Examples:
            >>> fn_example_basic("hello world")
            "处理结果: HELLO WORLD"
        """
        result = f"处理结果: {text.upper()}"
        self.logger.info(f"基础函数处理完成: {text}")
        return result
    
    def fn_example_with_options(
        self, 
        data: str, 
        operation: str = "upper",
        include_timestamp: bool = False
    ) -> Dict[str, Any]:
        """带选项的示例函数
        
        Args:
            data: 输入数据
            operation: 操作类型 (upper/lower/title/reverse)
            include_timestamp: 是否包含时间戳
            
        Returns:
            Dict[str, Any]: 包含处理结果的字典

        Examples:
            >>> fn_example_with_options("hello world", operation="upper", include_timestamp=True)
            {
                "original": "hello world",
                "processed": "HELLO WORLD",
                "operation": "upper",
                "timestamp": "2025-08-08T10:00:00Z"
            }
        """
        import datetime
        
        # 处理逻辑
        operations = {
            "upper": lambda x: x.upper(),
            "lower": lambda x: x.lower(),
            "title": lambda x: x.title(),
            "reverse": lambda x: x[::-1]
        }
        
        processed = operations.get(operation, operations["upper"])(data)
        
        result = {
            "original": data,
            "processed": processed,
            "operation": operation
        }
        
        if include_timestamp:
            result["timestamp"] = datetime.datetime.now().isoformat()
        
        self.logger.info(f"选项函数处理完成: {operation}")
        return result
    
    def fn_example_complex(
        self,
        items: List[str],
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "name",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """复杂类型参数示例函数
        
        Args:
            items: 字符串列表
            filters: 可选的过滤条件字典
            sort_by: 排序字段 (name/length/reverse)
            limit: 返回结果数量限制
            
        Returns:
            List[Dict[str, Any]]: 处理后的结果列表

        Examples:
            >>> fn_example_complex(["apple", "banana", "cherry", "date"], filters={"min_length": 4}, sort_by="length", limit=3)
            [
                {"name": "apple", "length": 5, "upper": "APPLE"},
                {"name": "banana", "length": 6, "upper": "BANANA"},
                {"name": "cherry", "length": 6, "upper": "CHERRY"}
            ]
        """
        if filters is None:
            filters = {}
        
        # 转换为字典格式
        processed_items = [
            {
                "name": item,
                "length": len(item),
                "upper": item.upper()
            }
            for item in items
        ]
        
        # 应用过滤器
        min_length = filters.get('min_length', 0)
        max_length = filters.get('max_length', float('inf'))
        
        filtered_items = [
            item for item in processed_items 
            if min_length <= item['length'] <= max_length
        ]
        
        # 排序
        sort_keys = {
            "name": lambda x: x['name'],
            "length": lambda x: x['length'],
            "reverse": lambda x: x['name'][::-1]
        }
        
        if sort_by in sort_keys:
            filtered_items.sort(key=sort_keys[sort_by])
        
        # 应用限制
        result = filtered_items[:limit]
        
        self.logger.info(f"复杂函数处理完成，返回 {len(result)} 项结果")
        return result
    
    def fn_example_api_call(self, query: str, model: str = "default") -> Dict[str, Any]:
        """API调用示例函数
        
        展示如何在函数中调用外部API
        
        Args:
            query: 查询内容
            model: 使用的模型名称
            
        Returns:
            Dict[str, Any]: API响应结果

        Examples:
            >>> fn_example_api_call("test query", "test-model")
            {
                "success": True,
                "query": "test query",
                "model": "test-model",
                "response": "模拟API响应: test query",
                "metadata": {"processing_time": 0.5, "tokens_used": 2}
            }
        """
        try:
            # 示例：调用外部API
            # response = self.client.query(query, model=model)
            
            # 模拟API响应
            result = {
                "success": True,
                "query": query,
                "model": model,
                "response": f"模拟API响应: {query}",
                "metadata": {
                    "processing_time": 0.5,
                    "tokens_used": len(query.split())
                }
            }
            
            self.logger.info(f"API调用成功: {query}")
            return result
            
        except Exception as e:
            self.logger.error(f"API调用失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
    
    def fn_example_file_operation(self, file_path: str, operation: str = "read") -> Union[str, Dict[str, Any]]:
        """文件操作示例函数
        
        Args:
            file_path: 文件路径
            operation: 操作类型 (read/info/exists)
            
        Returns:
            Union[str, Dict[str, Any]]: 操作结果

        Examples:
            >>> fn_example_file_operation("test.txt", "read")
            "文件内容"

            >>> fn_example_file_operation("test.txt", "info")
            {
                "path": "test.txt",
                "size": 1024,
                "modified": 1717987200,
                "is_file": True,
                "is_dir": False
            }
        """
        import os
        from pathlib import Path
        
        try:
            path = Path(file_path)
            
            if operation == "exists":
                return {"exists": path.exists(), "path": str(path)}
            
            elif operation == "info":
                if not path.exists():
                    return {"error": "文件不存在", "path": str(path)}
                
                stat = path.stat()
                return {
                    "path": str(path),
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "is_file": path.is_file(),
                    "is_dir": path.is_dir()
                }
            
            elif operation == "read":
                if not path.exists():
                    return "错误: 文件不存在"
                
                # 限制文件大小，避免读取过大文件
                if path.stat().st_size > 1024 * 1024:  # 1MB
                    return "错误: 文件过大，超过1MB限制"
                
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.logger.info(f"文件读取成功: {file_path}")
                return content
            
            else:
                return f"错误: 不支持的操作类型 '{operation}'"
                
        except Exception as e:
            self.logger.error(f"文件操作失败: {e}")
            return f"错误: {str(e)}"
    
    # ================================
    # 事件处理方法区域（可选实现）
    # ================================
    # 以 on_ 开头的方法会自动注册为事件处理器
    
    def on_call_function(self, **kwargs):
        """函数调用事件处理
        
        当插件的功能函数被调用时触发此事件
        """
        funcname = kwargs.get('funcname')
        function_kwargs = kwargs.get('kwargs', {})
        self.logger.info(f"插件函数被调用: {funcname}, 参数: {function_kwargs}")
    
    def on_task_start(self, **kwargs):
        """任务开始事件处理（可选）
        
        当新任务开始时触发
        """
        instruction = kwargs.get('instruction')
        task_id = kwargs.get('task_id')
        self.logger.info(f"新任务开始: {task_id}, 指令: {instruction[:50]}...")
    
    def on_exec_result(self, **kwargs):
        """代码执行结果事件处理（可选）
        
        当代码执行完成时触发
        """
        result = kwargs.get('result')
        block = kwargs.get('block')
        
        if result and result.get('success'):
            self.logger.info(f"代码执行成功: {block.name if block else 'unknown'}")
        elif result:
            self.logger.warning(f"代码执行失败: {result.get('error', 'unknown error')}")
    
    # ================================
    # 私有辅助方法区域
    # ================================
    
    def _validate_input(self, data: Any, expected_type: type) -> bool:
        """验证输入数据类型
        
        Args:
            data: 待验证数据
            expected_type: 期望的数据类型
            
        Returns:
            bool: 验证结果
        """
        return isinstance(data, expected_type)
    
    def _handle_error(self, error: Exception, context: str = "") -> Dict[str, Any]:
        """统一错误处理
        
        Args:
            error: 异常对象
            context: 错误上下文
            
        Returns:
            Dict[str, Any]: 错误信息字典
        """
        error_msg = f"{context}: {str(error)}" if context else str(error)
        self.logger.error(error_msg)
        
        return {
            "success": False,
            "error": error_msg,
            "type": type(error).__name__
        }


# ================================
# 测试代码区域（可选）
# ================================

if __name__ == '__main__':
    """
    插件测试代码
    
    这部分代码仅在直接运行插件文件时执行，用于测试插件功能。
    在实际部署时不会执行。
    """
    print("=== 插件模板测试 ===")
    
    # 创建插件实例
    config = {
        'api_key': 'test_key_12345',
        'base_url': 'https://api.test.com',
        'timeout': 10,
        'debug': True
    }
    
    try:
        plugin = FunctionTemplatePlugin(config)
        plugin.init()
        print(f"✓ 插件初始化成功: {plugin.name}")
        
        # 测试基础函数
        result1 = plugin.fn_example_basic("hello world")
        print(f"✓ 基础函数测试: {result1}")
        
        # 测试带选项的函数
        result2 = plugin.fn_example_with_options(
            "test data", 
            operation="title", 
            include_timestamp=True
        )
        print(f"✓ 选项函数测试: {result2}")
        
        # 测试复杂参数函数
        result3 = plugin.fn_example_complex(
            items=["apple", "banana", "cherry", "date"],
            filters={"min_length": 4},
            sort_by="length",
            limit=3
        )
        print(f"✓ 复杂函数测试: {result3}")
        
        # 测试API调用函数
        result4 = plugin.fn_example_api_call("test query", "test-model")
        print(f"✓ API函数测试: {result4}")
        
        # 测试事件处理
        plugin.on_task_start(instruction="测试任务", task_id="test123")
        plugin.on_call_function(funcname="example_basic", kwargs={"text": "test"})
        
        print("✓ 所有测试通过！")
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")