import base64
from zhipuai import ZhipuAI
from PIL import Image

def compress_image(image_path, output_path, max_size=1024):
    img = Image.open(image_path)
    img.thumbnail((max_size, max_size))  # 保持比例缩小长边
    img.save(output_path, optimize=True, quality=85)  # 压缩质量到85%

def analyze_posture(image_path, api_key):
    # 读取图片并编码为base64
    with open(image_path, "rb") as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode("utf-8")
    
    # 调用GLM-4V-Flash模型
    client = ZhipuAI(api_key=api_key)
    response = client.chat.completions.create(
        model="glm-4v",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "请分析学生坐姿，检查以下问题：1. 眼睛距离桌面是否过近（<30cm）；2. 肩膀是否倾斜或头歪；3. 背部是否弯曲。若存在以上问题，请以JSON格式返回评分（1-10分）和具体建议。"
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                    }
                ]
            }
        ]
    )
    return response.choices[0].message.content

if __name__ == "__main__":
    api_key = "YOUR_GLM_API_KEY"  # 替换为智谱平台申请的API Key
    image_path = "test.jpg"   # 替换为测试图片路径
    compressed_image_path = "compressed.jpg"
    compress_image(image_path, compressed_image_path)
    result = analyze_posture(compressed_image_path, api_key)
    print("分析结果：\n", result)