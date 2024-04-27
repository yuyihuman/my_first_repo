import requests
import time

code = "111222"
timestamp = time.strftime("%Y-%m-%d-%H:%M", time.localtime())
overview = f'**code**: {code}\n'
header = {
    "title":{
        "tag":"plain_text",
        "content": f'{timestamp}'
        },
    "template":"green"
}

def gen_json_text():
    json_text = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode":True
            },
            "header": header,
            "elements":[
            {
                "tag":"div",
                "text":{
                    "tag":"lark_md",
                    "content": f'{overview}'
                }
            }
            ]
        }
    }

    return json_text

def send_result():
    header = {'Content-Type': 'application/json;charset=utf-8'}
    bot_url_risk = "https://open.feishu.cn/open-apis/bot/v2/hook/f85d86c8-69c6-48c8-876e-2351b9c8bae2"
    retry_time = 5
    for _ in range(retry_time):
        try:
            requests.post(bot_url_risk, json = gen_json_text(), headers=header)
            break
        except Exception as e:
            print("create feishu tag failed, reason is {}".format(e))
            time.sleep(5)

send_result()