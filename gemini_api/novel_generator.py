import json
import requests
import os
from datetime import datetime
from typing import Dict, List, Optional
from logger_config import NovelLogger

class NovelGenerator:
    """自动小说生成器核心类"""
    
    def __init__(self, api_key_file: str = 'apikey.md'):
        """初始化生成器"""
        self.logger = NovelLogger.get_generator_logger()
        self.api_logger = NovelLogger.get_api_logger()
        
        self.logger.info("初始化小说生成器")
        self.api_key = self._load_api_key(api_key_file)
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        self.headers = {'Content-Type': 'application/json'}
        self.logger.info("小说生成器初始化完成")
        
    def _load_api_key(self, api_key_file: str) -> str:
        """加载API密钥"""
        try:
            self.logger.info(f"加载API密钥文件: {api_key_file}")
            with open(api_key_file, 'r', encoding='utf-8') as f:
                api_key = f.read().strip()
                self.logger.info("API密钥加载成功")
                return api_key
        except FileNotFoundError as e:
            self.logger.error(f"API密钥文件未找到: {api_key_file}")
            raise FileNotFoundError(f"API密钥文件 {api_key_file} 未找到")
    
    def _call_gemini_api(self, prompt: str, max_tokens: int = 2000) -> str:
        """调用Gemini API"""
        url = f"{self.base_url}?key={self.api_key}"
        
        data = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": 0.8
            }
        }
        
        try:
            self.api_logger.info(f"发起API请求，最大令牌数: {max_tokens}")
            NovelLogger.log_api_call(self.api_logger, "Gemini API", {"max_tokens": max_tokens})
            
            response = requests.post(url, headers=self.headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    response_text = result['candidates'][0]['content']['parts'][0]['text']
                    self.api_logger.info(f"API请求成功，响应长度: {len(response_text)} 字符")
                    NovelLogger.log_api_call(self.api_logger, "Gemini API", response_size=len(response_text))
                    return response_text
                else:
                    error_msg = "API返回格式异常"
                    self.api_logger.error(error_msg)
                    raise Exception(error_msg)
            else:
                error_msg = f"API请求失败: {response.status_code} - {response.text}"
                self.api_logger.error(error_msg)
                raise Exception(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"网络请求错误: {e}"
            NovelLogger.log_error_with_context(self.api_logger, e, "API网络请求")
            raise Exception(error_msg)
    
    def load_novel_ideas(self, ideas_file: str = 'novel_ideas.json') -> Dict:
        """加载小说创意配置"""
        try:
            self.logger.info(f"加载小说创意配置文件: {ideas_file}")
            with open(ideas_file, 'r', encoding='utf-8') as f:
                ideas = json.load(f)
                self.logger.info(f"创意配置加载成功，小说标题: {ideas.get('novel_config', {}).get('title', '未知')}")
                return ideas
        except FileNotFoundError as e:
            self.logger.error(f"创意文件未找到: {ideas_file}")
            raise FileNotFoundError(f"创意文件 {ideas_file} 未找到")
        except json.JSONDecodeError as e:
            NovelLogger.log_error_with_context(self.logger, e, f"解析创意文件 {ideas_file}")
            raise ValueError(f"创意文件 {ideas_file} 格式错误")
    
    def generate_outline(self, novel_ideas: Dict) -> str:
        """生成小说大纲"""
        title = novel_ideas.get('novel_config', {}).get('title', '未知小说')
        self.logger.info(f"开始生成小说大纲: {title}")
        
        prompt = f"""
请根据以下信息创建一个详细的小说大纲：

小说配置：
- 标题：{novel_ideas['novel_config']['title']}
- 类型：{novel_ideas['novel_config']['genre']}
- 长度：{novel_ideas['novel_config']['target_length']}
- 目标章节数：{novel_ideas['novel_config']['target_chapters']}
- 写作风格：{novel_ideas['novel_config']['writing_style']}
- 语调：{novel_ideas['novel_config']['tone']}

核心创意：
- 核心概念：{novel_ideas['main_idea']['core_concept']}
- 主题：{novel_ideas['main_idea']['theme']}
- 时代背景：{novel_ideas['main_idea']['setting']['time_period']}
- 地点：{novel_ideas['main_idea']['setting']['location']}
- 世界观：{novel_ideas['main_idea']['setting']['world_building']}

主要角色：
- 主角：{novel_ideas['characters']['protagonist']['name']} - {novel_ideas['characters']['protagonist']['background']}
- 主角目标：{novel_ideas['characters']['protagonist']['goals']}
- 反派：{novel_ideas['characters']['antagonist']['name']} - {novel_ideas['characters']['antagonist']['motivation']}

情节要素：
- 引发事件：{novel_ideas['plot_elements']['inciting_incident']}
- 主要冲突：{novel_ideas['plot_elements']['main_conflict']}
- 高潮构想：{novel_ideas['plot_elements']['climax_idea']}
- 结局方向：{novel_ideas['plot_elements']['resolution_direction']}

请创建一个包含以下内容的详细大纲：
1. 故事概述
2. 三幕结构划分
3. 每章节的主要内容和目标
4. 角色发展弧线
5. 主要冲突的发展脉络

请用中文回答，格式清晰，便于后续章节创作。
"""
        
        print("正在生成小说大纲...")
        self.logger.info("调用API生成小说大纲")
        outline = self._call_gemini_api(prompt, max_tokens=3000)
        self.logger.info(f"小说大纲生成完成，长度: {len(outline)} 字符")
        return outline
    
    def generate_chapter(self, chapter_num: int, chapter_outline: str, 
                        previous_summary: str = "", word_count: int = 2000) -> str:
        """生成具体章节内容"""
        self.logger.info(f"开始生成第{chapter_num}章内容，目标字数: {word_count}")
        
        prompt = f"""
请根据以下信息写作第{chapter_num}章的内容：

章节大纲：
{chapter_outline}

前情提要：
{previous_summary}

写作要求：
- 目标字数：约{word_count}字
- 保持故事连贯性
- 注重人物对话和心理描写
- 营造适当的氛围和节奏
- 在章节结尾留下适当的悬念或转折

请用中文创作，文笔流畅，情节生动。
"""
        
        print(f"正在生成第{chapter_num}章内容...")
        self.logger.info(f"调用API生成第{chapter_num}章内容")
        chapter_content = self._call_gemini_api(prompt, max_tokens=3000)
        self.logger.info(f"第{chapter_num}章内容生成完成，长度: {len(chapter_content)} 字符")
        return chapter_content
    
    def save_content(self, content: str, filename: str, output_dir: str = 'output'):
        """保存生成的内容到文件"""
        try:
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                self.logger.info(f"创建输出目录: {output_dir}")
            
            filepath = os.path.join(output_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.logger.info(f"内容已保存到文件: {filepath}，大小: {len(content)} 字符")
            print(f"内容已保存到: {filepath}")
        except Exception as e:
            NovelLogger.log_error_with_context(self.logger, e, f"保存文件 {filename}")
            raise
    
    def generate_character_profile(self, character_info: Dict) -> str:
        """生成角色详细档案"""
        character_name = character_info.get('name', '未知角色')
        self.logger.info(f"开始生成角色档案: {character_name}")
        
        prompt = f"""
请根据以下基础信息，创建一个详细的角色档案：

角色基础信息：
{json.dumps(character_info, ensure_ascii=False, indent=2)}

请详细描述：
1. 外貌描述
2. 详细的性格分析
3. 成长背景和重要经历
4. 说话方式和行为习惯
5. 内心恐惧和渴望
6. 与其他角色的关系网络
7. 在故事中的成长轨迹

请用中文回答，内容丰富且符合角色设定。
"""
        
        print(f"正在生成角色档案: {character_name}...")
        self.logger.info(f"调用API生成角色档案: {character_name}")
        profile = self._call_gemini_api(prompt, max_tokens=2000)
        self.logger.info(f"角色档案生成完成: {character_name}，长度: {len(profile)} 字符")
        return profile
    
    def generate_world_building(self, setting_info: Dict) -> str:
        """生成世界观设定"""
        world_name = setting_info.get('location', '未知世界')
        self.logger.info(f"开始生成世界观设定: {world_name}")
        
        prompt = f"""
请根据以下设定信息，创建详细的世界观：

基础设定：
{json.dumps(setting_info, ensure_ascii=False, indent=2)}

请详细描述：
1. 世界的历史背景
2. 社会结构和政治体系
3. 经济体系和货币制度
4. 文化传统和宗教信仰
5. 科技水平或魔法体系
6. 地理环境和重要地点
7. 重要的历史事件
8. 当前的社会问题和矛盾

请用中文回答，内容详实且逻辑自洽。
"""
        
        print("正在生成世界观设定...")
        self.logger.info("调用API生成世界观设定")
        world_building = self._call_gemini_api(prompt, max_tokens=3000)
        self.logger.info(f"世界观设定生成完成，长度: {len(world_building)} 字符")
        return world_building

def main():
    """主函数示例"""
    logger = NovelLogger.get_main_logger()
    NovelLogger.log_session_start(logger, "小说生成器主程序")
    
    try:
        # 初始化生成器
        generator = NovelGenerator()
        
        # 加载创意配置
        novel_ideas = generator.load_novel_ideas()
        
        # 生成大纲
        outline = generator.generate_outline(novel_ideas)
        
        # 保存大纲
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        generator.save_content(outline, f"novel_outline_{timestamp}.txt")
        
        print("\n=== 小说大纲生成完成 ===")
        print(outline[:500] + "..." if len(outline) > 500 else outline)
        
        logger.info("小说大纲生成任务完成")
        
    except Exception as e:
        NovelLogger.log_error_with_context(logger, e, "主程序执行")
        print(f"错误: {e}")
    finally:
        NovelLogger.log_session_end(logger, "小说生成器主程序")

if __name__ == "__main__":
    main()