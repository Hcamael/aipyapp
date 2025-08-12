#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基础框架测试 - 验证测试环境是否正常工作
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path


class TestBasicFramework:
    """测试框架基础功能"""
    
    @pytest.mark.unit
    def test_pytest_works(self):
        """验证 pytest 基础功能"""
        assert True
        
    @pytest.mark.unit
    def test_mock_works(self):
        """验证 Mock 功能"""
        mock_obj = Mock()
        mock_obj.test_method = Mock(return_value="test")
        
        result = mock_obj.test_method()
        assert result == "test"
        mock_obj.test_method.assert_called_once()
        
    @pytest.mark.unit
    def test_fixtures_work(self, temp_dir):
        """验证 fixture 功能"""
        assert isinstance(temp_dir, Path)
        assert temp_dir.exists()
        
        # 创建测试文件
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")
        
        assert test_file.exists()
        assert test_file.read_text() == "test content"
        
    @pytest.mark.unit
    def test_patch_works(self):
        """验证 patch 功能"""
        with patch('os.path.exists', return_value=True):
            import os
            assert os.path.exists('/fake/path') == True
            
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_works(self):
        """验证异步测试功能"""
        async def async_function():
            return "async result"
            
        result = await async_function()
        assert result == "async result"
        
    @pytest.mark.unit
    @pytest.mark.parametrize("input,expected", [
        (1, 1),
        (2, 4),
        (3, 9),
        (4, 16),
    ])
    def test_parametrize_works(self, input, expected):
        """验证参数化测试功能"""
        assert input ** 2 == expected
        
    @pytest.mark.unit
    def test_exception_handling(self):
        """验证异常处理"""
        with pytest.raises(ValueError):
            raise ValueError("Test exception")
            
    @pytest.mark.unit
    @pytest.mark.slow
    def test_mark_slow(self):
        """验证慢速测试标记"""
        # 这个测试会被标记为慢速
        # 可以用 pytest -m "not slow" 排除
        assert True
        
    @pytest.mark.unit
    def test_coverage_tracking(self):
        """验证覆盖率追踪"""
        def function_to_test(x):
            if x > 0:
                return x * 2
            else:
                return x * -2
                
        assert function_to_test(5) == 10
        assert function_to_test(-5) == 10