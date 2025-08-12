#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单的测试用例，用于验证测试框架是否正常工作
"""

import pytest


class TestSimple:
    """简单的测试类"""
    
    @pytest.mark.unit
    def test_addition(self):
        """测试加法"""
        assert 1 + 1 == 2
        
    @pytest.mark.unit
    def test_string_concatenation(self):
        """测试字符串连接"""
        assert "hello" + " " + "world" == "hello world"
        
    @pytest.mark.unit
    def test_list_operations(self):
        """测试列表操作"""
        lst = [1, 2, 3]
        lst.append(4)
        assert lst == [1, 2, 3, 4]
        assert len(lst) == 4
        
    @pytest.mark.unit
    @pytest.mark.parametrize("input,expected", [
        (1, 2),
        (2, 4),
        (3, 6),
        (4, 8),
    ])
    def test_multiplication(self, input, expected):
        """测试乘法（参数化测试）"""
        assert input * 2 == expected
        
    @pytest.mark.unit
    def test_dictionary_operations(self):
        """测试字典操作"""
        d = {"key": "value"}
        d["new_key"] = "new_value"
        assert "new_key" in d
        assert d["new_key"] == "new_value"