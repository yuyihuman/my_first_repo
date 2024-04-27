import requests
import time

def gen_json_text(code):
    json_text = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode":True
            },
            "header": {
                "title":{
                    "tag":"plain_text",
                    "content": f'{time.strftime("%Y-%m-%d-%H:%M", time.localtime())}'
                    },
                "template":"green"
            },
            "elements":[
            {
                "tag":"div",
                "text":{
                    "tag":"lark_md",
                    "content": f'**code**: {code}\n'
                }
            }
            ]
        }
    }
    return json_text

def send_result(code):
    header = {'Content-Type': 'application/json;charset=utf-8'}
    bot_url_risk = "https://open.feishu.cn/open-apis/bot/v2/hook/f85d86c8-69c6-48c8-876e-2351b9c8bae2"
    retry_time = 5
    for _ in range(retry_time):
        try:
            requests.post(bot_url_risk, json = gen_json_text(code), headers=header)
            break
        except Exception as e:
            print("create feishu tag failed, reason is {}".format(e))
            time.sleep(5)

send_result("123456")