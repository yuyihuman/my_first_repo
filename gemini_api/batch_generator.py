#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量小说生成工具
用于自动化生成整本小说的各个组件
"""

import json
import os
import time
from datetime import datetime
from novel_generator import NovelGenerator
from logger_config import NovelLogger

class BatchNovelGenerator:
    """批量小说生成器"""
    
    def __init__(self, project_path: str):
        self.logger = NovelLogger.get_batch_logger()
        self.logger.info(f"初始化批量生成器，项目路径: {project_path}")
        
        self.generator = NovelGenerator()
        self.project_path = project_path
        self.config_path = os.path.join(project_path, "novel_ideas.json")
        self.novel_ideas = None
        
        # 创建必要的目录
        self.ensure_directories()
        
        # 加载配置
        self.load_config()
        
        self.logger.info("批量生成器初始化完成")
    
    def ensure_directories(self):
        """确保所有必要的目录存在"""
        directories = [
            self.project_path,
            os.path.join(self.project_path, "chapters"),
            os.path.join(self.project_path, "characters"),
            os.path.join(self.project_path, "world_building"),
            os.path.join(self.project_path, "outlines"),
            os.path.join(self.project_path, "summaries")
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                self.logger.info(f"创建目录: {directory}")
                print(f"📁 创建目录: {directory}")
    
    def load_config(self):
        """加载项目配置"""
        try:
            self.logger.info(f"加载项目配置: {self.config_path}")
            self.novel_ideas = self.generator.load_novel_ideas(self.config_path)
            title = self.novel_ideas.get('novel_config', {}).get('title', '未知')
            self.logger.info(f"配置加载成功，项目: {title}")
            print(f"✅ 配置加载成功: {self.config_path}")
        except Exception as e:
            self.logger.error(f"配置加载失败: {e}")
            print(f"❌ 配置加载失败: {e}")
            raise
    
    def generate_full_outline(self):
        """生成完整大纲"""
        print("\n📋 开始生成完整大纲...")
        
        try:
            outline = self.generator.generate_outline(self.novel_ideas)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            outline_path = os.path.join(self.project_path, "outlines", f"full_outline_{timestamp}.txt")
            
            with open(outline_path, 'w', encoding='utf-8') as f:
                f.write(outline)
            
            print(f"✅ 完整大纲已保存: {outline_path}")
            return outline_path
            
        except Exception as e:
            print(f"❌ 大纲生成失败: {e}")
            return None
    
    def generate_all_character_profiles(self):
        """生成所有角色档案"""
        print("\n👤 开始生成所有角色档案...")
        
        characters = self.novel_ideas.get('characters', {})
        generated_profiles = []
        
        # 生成主角档案
        if 'protagonist' in characters:
            try:
                print("正在生成主角档案...")
                profile = self.generator.generate_character_profile(characters['protagonist'])
                
                char_name = characters['protagonist'].get('name', 'protagonist')
                profile_path = os.path.join(self.project_path, "characters", f"{char_name}_profile.txt")
                
                with open(profile_path, 'w', encoding='utf-8') as f:
                    f.write(profile)
                
                generated_profiles.append(profile_path)
                print(f"✅ 主角档案已保存: {profile_path}")
                time.sleep(2)  # 避免API调用过于频繁
                
            except Exception as e:
                print(f"❌ 主角档案生成失败: {e}")
        
        # 生成反派档案
        if 'antagonist' in characters:
            try:
                print("正在生成反派档案...")
                profile = self.generator.generate_character_profile(characters['antagonist'])
                
                char_name = characters['antagonist'].get('name', 'antagonist')
                profile_path = os.path.join(self.project_path, "characters", f"{char_name}_profile.txt")
                
                with open(profile_path, 'w', encoding='utf-8') as f:
                    f.write(profile)
                
                generated_profiles.append(profile_path)
                print(f"✅ 反派档案已保存: {profile_path}")
                time.sleep(2)
                
            except Exception as e:
                print(f"❌ 反派档案生成失败: {e}")
        
        # 生成配角档案
        supporting_chars = characters.get('supporting_characters', [])
        for i, char in enumerate(supporting_chars):
            try:
                print(f"正在生成配角档案 {i+1}/{len(supporting_chars)}...")
                profile = self.generator.generate_character_profile(char)
                
                char_name = char.get('name', f'supporting_char_{i+1}')
                profile_path = os.path.join(self.project_path, "characters", f"{char_name}_profile.txt")
                
                with open(profile_path, 'w', encoding='utf-8') as f:
                    f.write(profile)
                
                generated_profiles.append(profile_path)
                print(f"✅ 配角档案已保存: {profile_path}")
                time.sleep(2)
                
            except Exception as e:
                print(f"❌ 配角档案生成失败: {e}")
        
        return generated_profiles
    
    def generate_world_building(self):
        """生成世界观设定"""
        print("\n🌍 开始生成世界观设定...")
        
        try:
            setting_info = self.novel_ideas.get('main_idea', {}).get('setting', {})
            world_building = self.generator.generate_world_building(setting_info)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            world_path = os.path.join(self.project_path, "world_building", f"world_setting_{timestamp}.txt")
            
            with open(world_path, 'w', encoding='utf-8') as f:
                f.write(world_building)
            
            print(f"✅ 世界观设定已保存: {world_path}")
            return world_path
            
        except Exception as e:
            print(f"❌ 世界观生成失败: {e}")
            return None
    
    def generate_chapter_outlines(self, total_chapters: int = None):
        """生成各章节详细大纲"""
        if total_chapters is None:
            total_chapters = self.novel_ideas.get('novel_config', {}).get('target_chapters', 20)
        
        print(f"\n📝 开始生成 {total_chapters} 个章节的详细大纲...")
        
        # 首先生成整体章节规划
        planning_prompt = f"""
基于以下小说设定，请为 {total_chapters} 个章节创建详细的章节规划：

小说信息：
{json.dumps(self.novel_ideas, ensure_ascii=False, indent=2)}

请为每个章节提供：
1. 章节标题
2. 主要情节内容
3. 角色发展
4. 冲突推进
5. 章节目标
6. 与前后章节的连接

请用以下格式输出：
第X章：[标题]
- 主要情节：...
- 角色发展：...
- 冲突推进：...
- 章节目标：...
- 连接说明：...

请确保整体故事结构完整，节奏合理。
"""
        
        try:
            chapter_planning = self.generator._call_gemini_api(planning_prompt, max_tokens=4000)
            
            # 保存章节规划
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            planning_path = os.path.join(self.project_path, "outlines", f"chapter_planning_{timestamp}.txt")
            
            with open(planning_path, 'w', encoding='utf-8') as f:
                f.write(chapter_planning)
            
            print(f"✅ 章节规划已保存: {planning_path}")
            return planning_path
            
        except Exception as e:
            print(f"❌ 章节规划生成失败: {e}")
            return None
    
    def generate_batch_chapters(self, start_chapter: int = 1, end_chapter: int = None, 
                               word_count_per_chapter: int = 2000):
        """批量生成章节内容"""
        if end_chapter is None:
            end_chapter = self.novel_ideas.get('novel_config', {}).get('target_chapters', 20)
        
        print(f"\n📖 开始批量生成第 {start_chapter} 到第 {end_chapter} 章...")
        
        generated_chapters = []
        
        for chapter_num in range(start_chapter, end_chapter + 1):
            try:
                print(f"\n正在生成第 {chapter_num} 章 ({chapter_num - start_chapter + 1}/{end_chapter - start_chapter + 1})...")
                
                # 构建章节大纲（这里简化处理，实际应该从详细规划中提取）
                chapter_outline = f"第{chapter_num}章的主要内容，推进故事情节发展"
                
                # 获取前情提要
                previous_summary = ""
                if chapter_num > 1:
                    summary_path = os.path.join(self.project_path, "summaries", f"chapter_{chapter_num-1}_summary.txt")
                    if os.path.exists(summary_path):
                        with open(summary_path, 'r', encoding='utf-8') as f:
                            previous_summary = f.read()
                
                # 生成章节内容
                chapter_content = self.generator.generate_chapter(
                    chapter_num, chapter_outline, previous_summary, word_count_per_chapter
                )
                
                # 保存章节
                chapter_path = os.path.join(self.project_path, "chapters", f"chapter_{chapter_num:02d}.txt")
                with open(chapter_path, 'w', encoding='utf-8') as f:
                    f.write(chapter_content)
                
                generated_chapters.append(chapter_path)
                print(f"✅ 第 {chapter_num} 章已保存: {chapter_path}")
                
                # 生成章节摘要（用于下一章的前情提要）
                summary_prompt = f"""
请为以下章节内容生成一个简洁的摘要，用于下一章的前情提要：

{chapter_content[:1000]}...

请用2-3句话概括本章的关键情节和角色发展。
"""
                
                try:
                    summary = self.generator._call_gemini_api(summary_prompt, max_tokens=200)
                    summary_path = os.path.join(self.project_path, "summaries", f"chapter_{chapter_num}_summary.txt")
                    
                    with open(summary_path, 'w', encoding='utf-8') as f:
                        f.write(summary)
                    
                    print(f"📝 第 {chapter_num} 章摘要已保存")
                    
                except Exception as e:
                    print(f"⚠️ 第 {chapter_num} 章摘要生成失败: {e}")
                
                # 避免API调用过于频繁
                time.sleep(3)
                
            except Exception as e:
                print(f"❌ 第 {chapter_num} 章生成失败: {e}")
                continue
        
        return generated_chapters
    
    def generate_complete_novel(self):
        """生成完整小说（所有组件）"""
        print("\n🎯 开始生成完整小说项目...")
        print("这可能需要较长时间，请耐心等待...")
        
        results = {
            'outline': None,
            'character_profiles': [],
            'world_building': None,
            'chapter_planning': None,
            'chapters': []
        }
        
        # 1. 生成完整大纲
        print("\n=== 步骤 1: 生成完整大纲 ===")
        results['outline'] = self.generate_full_outline()
        
        # 2. 生成角色档案
        print("\n=== 步骤 2: 生成角色档案 ===")
        results['character_profiles'] = self.generate_all_character_profiles()
        
        # 3. 生成世界观设定
        print("\n=== 步骤 3: 生成世界观设定 ===")
        results['world_building'] = self.generate_world_building()
        
        # 4. 生成章节规划
        print("\n=== 步骤 4: 生成章节规划 ===")
        results['chapter_planning'] = self.generate_chapter_outlines()
        
        # 5. 生成前几章内容（示例）
        print("\n=== 步骤 5: 生成前5章内容 ===")
        results['chapters'] = self.generate_batch_chapters(1, 5)
        
        # 生成项目报告
        self.generate_project_report(results)
        
        print("\n🎉 完整小说项目生成完成！")
        return results
    
    def generate_project_report(self, results: dict):
        """生成项目报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(self.project_path, f"project_report_{timestamp}.txt")
        
        report_content = f"""
小说项目生成报告
==================

项目路径: {self.project_path}
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

生成结果:
----------
✅ 完整大纲: {results['outline'] if results['outline'] else '❌ 失败'}
✅ 角色档案: {len(results['character_profiles'])} 个
✅ 世界观设定: {results['world_building'] if results['world_building'] else '❌ 失败'}
✅ 章节规划: {results['chapter_planning'] if results['chapter_planning'] else '❌ 失败'}
✅ 生成章节: {len(results['chapters'])} 个

角色档案列表:
{chr(10).join(f'- {profile}' for profile in results['character_profiles'])}

生成章节列表:
{chr(10).join(f'- {chapter}' for chapter in results['chapters'])}

下一步建议:
----------
1. 查看并完善生成的大纲和角色档案
2. 根据需要调整章节规划
3. 继续生成剩余章节
4. 进行内容审查和编辑
5. 整合成完整的小说文档

注意事项:
----------
- 所有生成的内容仅供参考，建议进行人工审查和编辑
- 可以根据需要重新生成任何部分
- 建议保存多个版本以便比较选择
"""
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"📊 项目报告已保存: {report_path}")

def main():
    """主函数示例"""
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法: python batch_generator.py <项目路径>")
        print("示例: python batch_generator.py projects/my_novel")
        return
    
    project_path = sys.argv[1]
    
    try:
        batch_gen = BatchNovelGenerator(project_path)
        
        print("批量生成选项:")
        print("1. 生成完整项目")
        print("2. 仅生成大纲")
        print("3. 仅生成角色档案")
        print("4. 批量生成章节")
        
        choice = input("请选择 (1-4): ").strip()
        
        if choice == "1":
            batch_gen.generate_complete_novel()
        elif choice == "2":
            batch_gen.generate_full_outline()
        elif choice == "3":
            batch_gen.generate_all_character_profiles()
        elif choice == "4":
            start = int(input("起始章节: "))
            end = int(input("结束章节: "))
            batch_gen.generate_batch_chapters(start, end)
        else:
            print("无效选择")
            
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    main()