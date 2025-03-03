import cv2
import base64
import time
import os
from zhipuai import ZhipuAI
from typing import Union
import json
import re

class VideoPostureAnalyzer:
    def __init__(self, api_key: str, interval_sec: int = 2, output_dir: str = "output"):
        """
        初始化参数
        :param api_key: 智谱API密钥
        :param interval_sec: 采样间隔（秒）
        :param output_dir: 结果输出目录
        """
        self.api_key = api_key
        self.interval_sec = interval_sec
        self.output_dir = output_dir
        self.client = ZhipuAI(api_key=api_key)
        os.makedirs(output_dir, exist_ok=True)  # 创建输出目录

    def _process_frame(self, frame: cv2.Mat) -> str:
        """处理单帧图像：压缩+Base64编码"""
        # 压缩图像（调整分辨率为720p，质量80%）
        frame = cv2.resize(frame, (1280, 720))
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return base64.b64encode(buffer).decode('utf-8')

    def _call_glm_api(self, image_base64: str) -> str:
        """调用GLM-4V-Flash API"""
        response = self.client.chat.completions.create(
            model="glm-4v",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "请分析学生坐姿，检查以下问题：1. 眼睛距离桌面是否过近（<30cm）；2. 肩膀是否倾斜或头歪；3. 背部是否弯曲。若存在以上问题，请以JSON格式返回评分（1-10分）和具体建议。数据返回固定json格式，score字段为评分，advice字段为建议。"
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                    }
                ]
            }]
        )
        return response.choices[0].message.content

    def analyze_video(self, video_source: Union[str, int]):
        """主分析流程"""
        cap = cv2.VideoCapture(video_source)
        if not cap.isOpened():
            raise ValueError("无法打开视频源")

        last_capture_time = 0  # 记录上次采样时间
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            current_time = time.time()
            # 达到采样间隔时处理
            if current_time - last_capture_time >= self.interval_sec:
                # 1. 处理图像
                image_base64 = self._process_frame(frame)
                last_capture_time = current_time
                frame_count += 1
                # 2. 调用API
                # try:
                result = self._call_glm_api(image_base64)
                print(f"[{time.strftime('%H:%M:%S')}] 检测结果: {result}")

                # ```json

                # {
                #     "score": 5,
                #     "advice": "眼睛应保持与电脑屏幕至少一臂的距离，肩膀应保持直立，背部应挺直。"
                # }

                # ```

                pattern = r'```json\n(.*?)\n```'
                match = re.search(pattern, result, re.DOTALL)
                if match:
                    json_str = match.group(1)

                    rt_json = json.loads(json_str)
                    # select the score that is under 6分, then output the result
                    if rt_json["score"] <= 6:
                        print(f"检测到问题：建议：{rt_json['advice']}")

                    # cv2.imshow('Current Frame', frame)
                    # if cv2.waitKey(1) & 0xFF == ord('q'):
                    #     break

                # 保存截图和日志
                # timestamp = int(current_time)
                # cv2.imwrite(f"{self.output_dir}/frame_{timestamp}.jpg", frame)
                # with open(f"{self.output_dir}/results.log", "a") as f:
                #     f.write(f"{timestamp},{result}\n")
                # except Exception as e:
                #    print(f"API调用失败: {str(e)}")
                

        cap.release()
        print(f"分析完成，共处理{frame_count}帧")

if __name__ == "__main__":
    # 使用示例
    analyzer = VideoPostureAnalyzer(
        api_key="YOUR_GLM_API_KEY",
        interval_sec=2,  # 每n秒采样一次
        output_dir="detection_results"
    )
    analyzer.analyze_video("input_video.mp4")  # 支持视频文件路径或摄像头ID（例如0）