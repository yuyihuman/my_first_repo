import random
import sys

# 常用汉字列表，这里简单选取了部分常用汉字
CHINESE_CHARACTERS = '的一是在不了有和人这中大为上个国我以要他时来用们生到作地于出就分对成会可主发年动同工也能下过子说产种面而方后多定行学法所民得经十三之进着等部度家电力里如水化高自二理起小物现实加量都两体制机当使点从业本去把性好应开它合还因由其些然前外天政四日那社义事平形相全表间样与关各重新线内数正心反你明看原又么利比或但质气第向道命此变条只没结解问意建月公无系军很情者最立代想已通并提直题党程展五果料象员革位入常文总次品式活设及管特件长求老头基资边流路级少图山统接知较将组见计别她手角期根论运农指几九区强放决西被干做必战先回则任取据处队南给色光门即保治北造百规热领七海口东导器压志世金增争济阶油思术极交受联什认六共权收证改清己美再采转更单风切打白教速花带安场身车例真务具万每目至达走积示议声报斗完类八离华名确才科张信马节话米整空元况今集温传土许步群广石记需段研界拉林律叫且究观越织装影算低持音众书布复容儿须际商非验连断深难近矿千周委素技备半办青省列习响约支般史感劳便团往酸历市克何除消构府称太准精值号率族维划选标写存候毛亲快效斯院查江型眼王按格养易置派层片始却专状育厂京识适属圆包火住调满县局照参红细引听该铁价严龙飞'


def generate_random_chinese_text(line_length, line_count):
    text = ""
    for _ in range(line_count):
        line = ''.join(random.choice(CHINESE_CHARACTERS) for _ in range(line_length))
        # 每行后面添加两个换行符，实现每行后有空行
        text += line + '\n\n'
    return text


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法: python script.py <每行字数> <行数>")
        sys.exit(1)

    try:
        line_length = int(sys.argv[1])
        line_count = int(sys.argv[2])
    except ValueError:
        print("输入的参数必须是有效的整数。")
        sys.exit(1)

    random_text = generate_random_chinese_text(line_length, line_count)
    with open('material', 'w', encoding='utf-8') as file:
        file.write(random_text)

    print(f"已生成随机中文文本，保存到文件 'material' 中。")