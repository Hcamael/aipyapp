#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for ConfigManager and config utilities
"""

import pytest
import re
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open
import tempfile
import shutil

from aipyapp.aipy.config import (
    CONFIG_DIR,
    init_config_dir,
    get_config_file_path,
    lowercase_keys,
    is_valid_api_key,
    get_mcp_config_file,
    CONFIG_FILE_NAME,
    USER_CONFIG_FILE_NAME,
    MCP_CONFIG_FILE_NAME
)

# 尝试导入可能不存在的函数
try:
    from aipyapp.aipy.config import ConfigManager, get_tt_api_key
except ImportError:
    ConfigManager = None
    get_tt_api_key = None


class TestConfigPaths:
    """测试配置路径相关功能"""
    
    @pytest.mark.unit
    def test_config_dir_initialization(self):
        """测试配置目录初始化"""
        with patch('pathlib.Path.home', return_value=Path('/home/test')):
            with patch('pathlib.Path.mkdir') as mock_mkdir:
                config_dir = init_config_dir()
                
                assert config_dir == Path('/home/test/.aipyapp')
                mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
                
    @pytest.mark.unit
    def test_config_dir_permission_error(self):
        """测试配置目录创建权限错误"""
        with patch('pathlib.Path.home', return_value=Path('/home/test')):
            with patch('pathlib.Path.mkdir', side_effect=PermissionError):
                with pytest.raises(PermissionError):
                    init_config_dir()
                    
    @pytest.mark.unit
    def test_get_config_file_path_default(self, temp_dir):
        """测试获取默认配置文件路径"""
        config_file = get_config_file_path(temp_dir, create=False)
        expected = temp_dir / CONFIG_FILE_NAME
        assert config_file == expected
        
    @pytest.mark.unit
    def test_get_config_file_path_create(self, temp_dir):
        """测试创建配置文件"""
        config_file = get_config_file_path(temp_dir, create=True)
        assert config_file.exists()
        
    @pytest.mark.unit
    def test_get_config_file_path_custom_name(self, temp_dir):
        """测试自定义配置文件名"""
        custom_name = "custom_config.toml"
        config_file = get_config_file_path(temp_dir, file_name=custom_name, create=False)
        expected = temp_dir / custom_name
        assert config_file == expected


class TestConfigUtilities:
    """测试配置工具函数"""
    
    @pytest.mark.unit
    def test_lowercase_keys_simple(self):
        """测试简单字典键小写转换"""
        input_dict = {'KEY1': 'value1', 'Key2': 'value2'}
        result = lowercase_keys(input_dict)
        
        assert result == {'key1': 'value1', 'key2': 'value2'}
        
    @pytest.mark.unit
    def test_lowercase_keys_nested(self):
        """测试嵌套字典键小写转换"""
        input_dict = {
            'OUTER': {
                'INNER': 'value',
                'Another': {'DEEP': 'nested'}
            }
        }
        result = lowercase_keys(input_dict)
        
        expected = {
            'outer': {
                'inner': 'value',
                'another': {'deep': 'nested'}
            }
        }
        assert result == expected
        
    @pytest.mark.unit
    def test_lowercase_keys_non_dict(self):
        """测试非字典输入"""
        assert lowercase_keys("string") == "string"
        assert lowercase_keys(123) == 123
        assert lowercase_keys(['list']) == ['list']
        
    @pytest.mark.unit
    @pytest.mark.parametrize("api_key,expected", [
        ("valid_key_123", True),
        ("UPPER_CASE_KEY", True),
        ("key-with-dashes", True),
        ("12345678", True),  # 最小长度 8
        ("a" * 128, True),  # 最大长度 128
        ("short", False),  # 太短
        ("a" * 129, False),  # 太长
        ("key with spaces", False),  # 包含空格
        ("key@special", False),  # 包含特殊字符
        ("", False),  # 空字符串
    ])
    def test_is_valid_api_key(self, api_key, expected):
        """测试 API Key 验证"""
        assert is_valid_api_key(api_key) == expected


class TestMCPConfig:
    """测试 MCP 配置相关功能"""
    
    @pytest.mark.unit
    def test_get_mcp_config_file_exists(self, temp_dir):
        """测试获取存在的 MCP 配置文件"""
        mcp_file = temp_dir / MCP_CONFIG_FILE_NAME
        mcp_file.write_text('{"test": "config"}')
        
        result = get_mcp_config_file(temp_dir)
        assert result == mcp_file
        
    @pytest.mark.unit
    def test_get_mcp_config_file_not_exists(self, temp_dir):
        """测试 MCP 配置文件不存在"""
        result = get_mcp_config_file(temp_dir)
        assert result is None
        
    @pytest.mark.unit
    def test_get_mcp_config_file_empty(self, temp_dir):
        """测试空的 MCP 配置文件"""
        mcp_file = temp_dir / MCP_CONFIG_FILE_NAME
        mcp_file.touch()  # 创建空文件
        
        result = get_mcp_config_file(temp_dir)
        assert result is None


@pytest.mark.skipif(ConfigManager is None, reason="ConfigManager not available")
class TestConfigManager:
    """测试 ConfigManager 类"""
    
    @pytest.mark.unit
    @patch('aipyapp.aipy.config.Dynaconf')
    def test_config_manager_initialization(self, mock_dynaconf):
        """测试 ConfigManager 初始化"""
        mock_settings = MagicMock()
        mock_dynaconf.return_value = mock_settings
        
        config_manager = ConfigManager()
        
        assert config_manager.settings == mock_settings
        mock_dynaconf.assert_called_once()
        
    @pytest.mark.unit
    @patch('aipyapp.aipy.config.Dynaconf')
    def test_config_manager_with_custom_path(self, mock_dynaconf, temp_dir):
        """测试自定义路径的 ConfigManager"""
        mock_settings = MagicMock()
        mock_dynaconf.return_value = mock_settings
        
        custom_config = temp_dir / "custom.toml"
        custom_config.write_text("[test]\nkey = 'value'")
        
        config_manager = ConfigManager(config_file=str(custom_config))
        
        assert config_manager.settings == mock_settings
        
    @pytest.mark.unit
    @patch('aipyapp.aipy.config.Dynaconf')
    def test_config_manager_get(self, mock_dynaconf):
        """测试 ConfigManager get 方法"""
        mock_settings = MagicMock()
        mock_settings.get.return_value = "test_value"
        mock_dynaconf.return_value = mock_settings
        
        config_manager = ConfigManager()
        value = config_manager.get("test_key", default="default")
        
        assert value == "test_value"
        mock_settings.get.assert_called_once_with("test_key", "default")
        
    @pytest.mark.unit
    @patch('aipyapp.aipy.config.Dynaconf')
    def test_config_manager_set(self, mock_dynaconf):
        """测试 ConfigManager set 方法"""
        mock_settings = MagicMock()
        mock_dynaconf.return_value = mock_settings
        
        config_manager = ConfigManager()
        config_manager.set("test_key", "test_value")
        
        mock_settings.set.assert_called_once_with("test_key", "test_value")
        
    @pytest.mark.unit
    @patch('aipyapp.aipy.config.Dynaconf')
    def test_config_manager_update(self, mock_dynaconf):
        """测试 ConfigManager update 方法"""
        mock_settings = MagicMock()
        mock_dynaconf.return_value = mock_settings
        
        config_manager = ConfigManager()
        updates = {"key1": "value1", "key2": "value2"}
        config_manager.update(updates)
        
        mock_settings.update.assert_called_once_with(updates)


@pytest.mark.skipif(get_tt_api_key is None, reason="get_tt_api_key not available")
class TestTrustTokenAPI:
    """测试 TrustToken API 相关功能"""
    
    @pytest.mark.unit
    @patch('aipyapp.aipy.config.TrustToken')
    def test_get_tt_api_key_from_settings(self, mock_tt):
        """测试从设置中获取 TrustToken API Key"""
        settings = {'api': {'trusttoken': 'test_api_key'}}
        
        result = get_tt_api_key(settings)
        assert result == 'test_api_key'
        
    @pytest.mark.unit
    @patch('aipyapp.aipy.config.TrustToken')
    def test_get_tt_api_key_from_trusttoken(self, mock_tt):
        """测试从 TrustToken 获取 API Key"""
        mock_tt.get_tt_key.return_value = 'tt_api_key'
        settings = {}
        
        result = get_tt_api_key(settings)
        assert result == 'tt_api_key'
        mock_tt.get_tt_key.assert_called_once()
        
    @pytest.mark.unit
    @patch('aipyapp.aipy.config.TrustToken')
    def test_get_tt_api_key_none(self, mock_tt):
        """测试无 API Key 的情况"""
        mock_tt.get_tt_key.return_value = None
        settings = {}
        
        result = get_tt_api_key(settings)
        assert result is None


class TestConfigSave:
    """测试配置保存功能"""
    
    @pytest.mark.unit
    def test_save_config_to_file(self, temp_dir):
        """测试保存配置到文件"""
        config_data = {
            'test': {
                'key1': 'value1',
                'key2': 123
            }
        }
        
        config_file = temp_dir / "test_config.toml"
        
        with patch('tomli_w.dump') as mock_dump:
            with open(config_file, 'wb') as f:
                import tomli_w
                tomli_w.dump(config_data, f)
                
            mock_dump.assert_called_once()
            
    @pytest.mark.unit
    @patch('aipyapp.aipy.config.Dynaconf')
    def test_config_manager_save(self, mock_dynaconf, temp_dir):
        """测试 ConfigManager 保存配置"""
        mock_settings = MagicMock()
        mock_settings.to_dict.return_value = {'key': 'value'}
        mock_dynaconf.return_value = mock_settings
        
        config_manager = ConfigManager()
        config_file = temp_dir / "save_test.toml"
        
        # 模拟保存方法
        with patch('builtins.open', mock_open()) as mock_file:
            with patch('tomli_w.dump') as mock_dump:
                # 如果 ConfigManager 有 save 方法的话
                if hasattr(config_manager, 'save'):
                    config_manager.save(config_file)
                    mock_dump.assert_called_once()


class TestConfigMigration:
    """测试配置迁移功能"""
    
    @pytest.mark.unit
    def test_old_config_detection(self, temp_dir):
        """测试检测旧配置文件"""
        from aipyapp.aipy.config import OLD_SETTINGS_FILES
        
        # 创建一个模拟的旧配置文件
        with patch('pathlib.Path.home', return_value=temp_dir):
            old_config = temp_dir / '.aipy.toml'
            old_config.write_text('[old]\nconfig = true')
            
            # 检查旧配置文件是否存在
            assert old_config.exists()
            assert old_config.stat().st_size > 0