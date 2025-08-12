#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import base64
import mimetypes
from typing import Union

from openai import OpenAI

from aipyapp import TaskPlugin, PluginInitError

class ImageToolPlugin(TaskPlugin):
    """图片识别工具插件"""
    name = "image_tool"
    version = "1.0.0"
    description = "使用大模型识别和分析图片内容"
    author = "AiPy Team"
    
    def init(self):
        """初始化OpenAI客户端"""
        api_key = self.config.get('api_key')
        base_url = self.config.get('base_url')
        model = self.config.get('model', 'gpt-4-vision-preview')
        
        if not api_key:
            raise PluginInitError("未配置OpenAI API Key")
        
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model = model
        self.logger.info(f"初始化OpenAI客户端，模型: {model}")
    
    def fn_recognize_image(self,
        image_source: str,
        prompt: str = "请描述这张图片的内容。",
        return_json: bool = False
    ) -> Union[str, dict]:
        """
        使用大模型识别图片内容，可接受本地路径或图片URL
        
        Args:
            image_source: 本地图片路径或远程图片URL
            prompt: 分析提示词
            return_json: 是否返回完整JSON响应
            
        Returns:
            字符串描述或JSON响应
        """
        return self._recognize_image(image_source, prompt, return_json)
    
    def fn_analyze_image(self, image_source: str, analysis_type: str = "general") -> str:
        """
        深度分析图片内容
        
        Args:
            image_source: 本地图片路径或远程图片URL
            analysis_type: 分析类型 (general/technical/artistic/text)
            
        Returns:
            分析结果
        """
        prompts = {
            "general": "请详细描述这张图片的内容，包括主要对象、场景、颜色、构图等。",
            "technical": "请从技术角度分析这张图片，包括拍摄参数、后期处理、技术特点等。",
            "artistic": "请从艺术角度欣赏这张图片，分析其构图、色彩搭配、艺术风格等。",
            "text": "请识别并提取图片中的所有文字内容，保持原有格式。"
        }
        
        prompt = prompts.get(analysis_type, prompts["general"])
        return self._recognize_image(image_source, prompt, False)
    
    def _recognize_image(self, image_source: str, prompt: str, return_json: bool) -> Union[str, dict]:
        """内部图片识别实现"""
        try:
            # 判断是本地文件还是远程URL
            if image_source.startswith("http://") or image_source.startswith("https://"):
                image_url = {"type": "image_url", "image_url": {"url": image_source}}
            else:
                # 本地文件处理
                if not os.path.exists(image_source):
                    raise FileNotFoundError(f"文件不存在: {image_source}")

                mime_type, _ = mimetypes.guess_type(image_source)
                if mime_type is None:
                    mime_type = "image/jpeg"  # 默认MIME类型

                with open(image_source, "rb") as f:
                    image_bytes = f.read()
                base64_image = base64.b64encode(image_bytes).decode("utf-8")
                data_url = f"data:{mime_type};base64,{base64_image}"
                image_url = {"type": "image_url", "image_url": {"url": data_url}}

            # 调用OpenAI Chat接口
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            image_url,
                        ],
                    }
                ],
                max_tokens=self.config.get('max_tokens', 1000),
            )

            # 返回值处理
            if return_json:
                return response.model_dump()
            else:
                return response.choices[0].message.content
                
        except Exception as e:
            self.logger.error(f"图片识别失败: {e}")
            raise