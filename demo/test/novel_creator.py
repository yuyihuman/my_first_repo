# -*- coding: utf-8 -*-
import os
import json
from openai import OpenAI
from typing import Dict, List, Tuple

class NovelArchitect:
    """
    长篇小说架构生成系统
    功能：
    - 自动分卷分章
    - 保持跨卷连续性
    - 关键伏笔跟踪
    - 人物发展轨迹管理
    """
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        self.blueprint = {
            "title": "《都市恋曲》",
            "total_volumes": 5,
            "chapters_per_volume": 20,
            "current_progress": {
                "volume": 1,
                "chapter": 1
            },
            "character_arcs": {},
            "core_symbols": [],
            "volumes": []
        }
        self.style_params = {
            "pacing": "moderate",  # slow/moderate/fast
            "romantic_tension_level": 0.7  # 0.0~1.0
        }

    def generate_full_outline(self):
        """全流程生成入口"""
        self._initialize_core_elements()
        
        for vol in range(1, self.blueprint["total_volumes"] + 1):
            volume = self._generate_volume(vol)
            self.blueprint["volumes"].append(volume)
            self._save_progress()
        
        self._export_markdown()

    def _initialize_core_elements(self):
        """带人工修复的初始化"""
        chars_prompt = """创建都市爱情小说核心人物：
        （你的内容...）
        输出严格遵循以下JSON格式，不要包含任何额外文字：
        {
            "女主": {"姓名":"", "职业":"", "核心冲突":""},
            "男主": {"姓名":"", "秘密":"", "成长目标":""},
            "配角": [
                {"姓名":"", "作用":""},
                {"姓名":"", "作用":""}
            ]
        }"""  # 明确格式要求
        
        response = self._safe_api_call(chars_prompt, max_tokens=500)
        print(f"[DEBUG] API响应：{response}")
        
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            print("自动解析失败，进入人工修复模式")
            while True:
                try:
                    manual_input = input("请粘贴修正后的JSON：")
                    data = json.loads(manual_input)
                    break
                except:
                    print("仍然无效，请检查格式")
        
        self.blueprint.update(data)

    def _generate_volume(self, vol_num: int) -> Dict:
        """生成单卷细纲（修复版本）"""
        volume = {
            "title": f"第{vol_num}卷",
            "theme": self._generate_volume_theme(vol_num),  # 先生成主题
            "chapters": [],
            "foreshadowing": []
        }
        
        # 生成章节明细（此时theme已存在）
        for chap in range(1, self.blueprint["chapters_per_volume"] + 1):
            chapter = self._generate_chapter(vol_num, chap, volume["theme"])  # 传入当前卷主题
            volume["chapters"].append(chapter)
            
            if chap % 5 == 0:
                self._update_progress(vol_num, chap)
                self._save_progress()
        
        return volume
    
    def _generate_volume_theme(self, vol_num: int) -> str:
        """独立生成卷主题"""
        theme_prompt = f"""生成第{vol_num}卷主题..."""  # 原prompt内容
        theme_data = json.loads(self._safe_api_call(theme_prompt))
        return theme_data["theme"]

    def _generate_chapter(self, vol: int, chap: int, current_theme: str) -> Dict:
        """修改后的章节生成（接收当前主题参数）"""
        context = self._build_context(vol, chap)
        
        prompt = f"""作为小说架构师，撰写第{vol}卷第{chap}章详细纲要：
        当前卷主题：{current_theme}  # 使用传入参数
        ...其他内容保持不变..."""
        
        return json.loads(self._safe_api_call(prompt, temp=0.6))

    def _build_context(self, vol: int, chap: int) -> str:
        """上下文构建优化"""
        context = []
        
        # 当前卷内部前情
        if chap > 1:
            prev_chap = self.blueprint["volumes"][vol-1]["chapters"][chap-2] if vol <= len(self.blueprint["volumes"]) else {}
        
        # 跨卷关联（仅在非首卷时生效）
        if vol > 1 and chap < 5:
            prev_vol = self.blueprint["volumes"][vol-2]
            context.append(f"前卷遗留伏笔：{prev_vol['foreshadowing'][-2:]}") 
        
        return "\n".join(context)

    def _safe_api_call(self, prompt: str, **params) -> str:
        """带格式清洗的API调用"""
        retry = 3
        while retry > 0:
            try:
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "你输出严格规范的JSON"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,  # 降低随机性
                    max_tokens=params.get("max_tokens", 600),
                    top_p=0.9
                )
                raw = response.choices[0].message.content
                
                # 提取JSON部分
                start = raw.find('{')
                end = raw.rfind('}') + 1
                if start == -1 or end == 0:
                    raise ValueError("未检测到JSON结构")
                
                json_str = raw[start:end]
                # 预验证
                json.loads(json_str)
                return json_str
                
            except Exception as e:
                print(f"格式错误: {str(e)}，剩余重试次数：{retry-1}")
                retry -= 1
        return "{}"

    def _update_progress(self, vol: int, chap: int):
        """更新进度"""
        self.blueprint["current_progress"] = {
            "volume": vol,
            "chapter": chap
        }

    def _save_progress(self):
        """保存进度"""
        with open("novel_progress.json", "w", encoding="utf-8") as f:
            json.dump(self.blueprint, f, ensure_ascii=False, indent=2)

    def _export_markdown(self):
        """导出为Markdown"""
        md = [f"# {self.blueprint['title']}"]
        
        for vol in self.blueprint["volumes"]:
            md.append(f"\n## {vol['title']} - {vol['theme']}")
            md.append(f"**核心象征**：{'、'.join(vol['symbol_usage'])}\n")
            
            for idx, chap in enumerate(vol["chapters"], 1):
                md.append(f"### 第{idx}章 {chap['title']}")
                md.append("#### 场景设计")
                for scene in chap["scenes"]:
                    md.append(f"- **地点**：{scene['location']}  ")
                    md.append(f"  - 作用：{scene['purpose']}  ")
                    md.append(f"  - 冲突强度：{'★' * scene['conflict_level']}")
                md.append(f"#### 伏笔铺垫\n- " + "\n- ".join(chap["foreshadowing"]))
        
        with open("novel_outline.md", "w", encoding="utf-8") as f:
            f.write("\n".join(md))

if __name__ == "__main__":
    architect = NovelArchitect(api_key="sk-f54652922efa4939954a19ab03e748e1")
    architect.generate_full_outline()