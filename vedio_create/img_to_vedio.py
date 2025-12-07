import os
import sys
from http import HTTPStatus
from dashscope import VideoSynthesis
import dashscope

dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'

# 从环境变量中获取 DashScope API Key（即阿里云百炼平台 API key）
api_key = "sk-063b583ef8114b21ba9dc8566b4800a8"
dashscope.api_key = api_key

img_url = "http://39350ecud139.vicp.fun:26986/images/20251206-151442.jpg"

def sample_async_call_i2v():
    # call async api, will return the task information
    # you can get task status with the returned task id.
    rsp = VideoSynthesis.async_call(model='wan2.5-i2v-preview',
                                    prompt='图中的美女在东方明珠前留影，并摆出乖萌的pose',
                                    img_url=img_url)
    print(rsp)
    if rsp.status_code == HTTPStatus.OK:
        print("task_id: %s" % rsp.output.task_id)
    else:
        print('Failed, status_code: %s, code: %s, message: %s' %
              (rsp.status_code, rsp.code, rsp.message))
   
    # get the task information include the task status.
    status = VideoSynthesis.fetch(rsp)
    if status.status_code == HTTPStatus.OK:
        print(status.output.task_status)  # check the task status
    else:
        print('Failed, status_code: %s, code: %s, message: %s' %
              (status.status_code, status.code, status.message))

    # wait the task complete, will call fetch interval, and check it's in finished status.
    rsp = VideoSynthesis.wait(rsp)
    print(rsp)
    if rsp.status_code == HTTPStatus.OK:
        print(rsp.output.video_url)
    else:
        print('Failed, status_code: %s, code: %s, message: %s' %
              (rsp.status_code, rsp.code, rsp.message))


if __name__ == '__main__':
    if not api_key:
        print("DASHSCOPE_API_KEY is not set")
        sys.exit(1)
    sample_async_call_i2v()
