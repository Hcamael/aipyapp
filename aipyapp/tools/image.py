import openai
import base64
import mimetypes
import os

openai.api_key = "your-api-key"

def recognize_image(
    image_source: str,
    prompt: str = "请描述这张图片的内容。",
    return_json: bool = False
) -> str | dict:
    """
    使用 GPT-4-Vision 模型识别图片内容，可接受本地路径或图片 URL。

    参数:
        image_source: 本地图片路径或远程图片 URL
        prompt: 提示词，如“请描述这张图片”
        return_json: 若为 True，返回完整 JSON 响应；否则仅返回文本内容

    返回:
        字符串描述或 JSON 响应
    """

    # 判断是本地文件还是远程 URL
    if image_source.startswith("http://") or image_source.startswith("https://"):
        image_url = {"type": "image_url", "image_url": {"url": image_source}}
    else:
        # 本地文件处理
        if not os.path.exists(image_source):
            raise FileNotFoundError(f"文件不存在: {image_source}")

        mime_type, _ = mimetypes.guess_type(image_source)
        if mime_type is None:
            mime_type = "image/jpeg"  # 默认 MIME 类型

        with open(image_source, "rb") as f:
            image_bytes = f.read()
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:{mime_type};base64,{base64_image}"
        image_url = {"type": "image_url", "image_url": {"url": data_url}}

    # 调用 OpenAI ChatCompletion 接口
    response = openai.ChatCompletion.create(
        model="gpt-4-vision-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    image_url,
                ],
            }
        ],
        max_tokens=1000,
    )

    # 返回值处理
    if return_json:
        return response.to_dict()
    else:
        return response.choices[0].message["content"]
