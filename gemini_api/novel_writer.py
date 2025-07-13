#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交互式小说创作工具
提供用户友好的界面来使用小说生成功能
"""

import json
import os
from datetime import datetime
from novel_generator import NovelGenerator
from logger_config import NovelLogger

class NovelWriter:
    """交互式小说创作工具"""
    
    def __init__(self):
        self.logger = NovelLogger.get_main_logger()
        self.logger.info("初始化交互式小说创作工具")
        
        self.generator = NovelGenerator()
        self.current_project = None
        self.project_dir = "projects"
        
        self.logger.info("交互式创作工具初始化完成")
        
    def show_menu(self):
        """显示主菜单"""
        print("\n" + "="*50)
        print("🖋️  AI 小说创作助手")
        print("="*50)
        print("1. 📝 创建新的小说项目")
        print("2. 📂 加载现有项目")
        print("3. 📋 生成小说大纲")
        print("4. ✍️  生成章节内容")
        print("5. 👤 生成角色档案")
        print("6. 🌍 生成世界观设定")
        print("7. 📊 查看项目状态")
        print("8. 💾 保存项目")
        print("9. ❓ 帮助")
        print("0. 🚪 退出")
        print("="*50)
    
    def create_new_project(self):
        """创建新项目"""
        print("\n📝 创建新的小说项目")
        print("-" * 30)
        
        project_name = input("请输入项目名称: ").strip()
        if not project_name:
            print("❌ 项目名称不能为空")
            return
        
        # 创建项目目录
        if not os.path.exists(self.project_dir):
            os.makedirs(self.project_dir)
        
        project_path = os.path.join(self.project_dir, project_name)
        if os.path.exists(project_path):
            print(f"❌ 项目 '{project_name}' 已存在")
            return
        
        os.makedirs(project_path)
        
        # 复制模板配置文件
        template_path = "novel_ideas.json"
        project_config_path = os.path.join(project_path, "novel_ideas.json")
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            with open(project_config_path, 'w', encoding='utf-8') as f:
                f.write(template_content)
            
            self.current_project = project_path
            print(f"✅ 项目 '{project_name}' 创建成功!")
            print(f"📁 项目路径: {project_path}")
            print(f"💡 请编辑 {project_config_path} 文件来设置你的小说创意")
            
        except Exception as e:
            print(f"❌ 创建项目失败: {e}")
    
    def load_project(self):
        """加载现有项目"""
        print("\n📂 加载现有项目")
        print("-" * 30)
        
        if not os.path.exists(self.project_dir):
            print("❌ 没有找到任何项目")
            return
        
        projects = [d for d in os.listdir(self.project_dir) 
                   if os.path.isdir(os.path.join(self.project_dir, d))]
        
        if not projects:
            print("❌ 没有找到任何项目")
            return
        
        print("可用项目:")
        for i, project in enumerate(projects, 1):
            print(f"{i}. {project}")
        
        try:
            choice = int(input("\n请选择项目编号: ")) - 1
            if 0 <= choice < len(projects):
                self.current_project = os.path.join(self.project_dir, projects[choice])
                print(f"✅ 已加载项目: {projects[choice]}")
            else:
                print("❌ 无效的选择")
        except ValueError:
            print("❌ 请输入有效的数字")
    
    def generate_outline(self):
        """生成小说大纲"""
        if not self.current_project:
            print("❌ 请先创建或加载一个项目")
            return
        
        config_path = os.path.join(self.current_project, "novel_ideas.json")
        if not os.path.exists(config_path):
            print("❌ 找不到项目配置文件")
            return
        
        try:
            print("\n📋 正在生成小说大纲...")
            novel_ideas = self.generator.load_novel_ideas(config_path)
            outline = self.generator.generate_outline(novel_ideas)
            
            # 保存大纲
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            outline_path = os.path.join(self.current_project, f"outline_{timestamp}.txt")
            
            with open(outline_path, 'w', encoding='utf-8') as f:
                f.write(outline)
            
            print(f"✅ 大纲生成完成并保存到: {outline_path}")
            print("\n📋 大纲预览:")
            print("-" * 50)
            print(outline[:800] + "..." if len(outline) > 800 else outline)
            
        except Exception as e:
            print(f"❌ 生成大纲失败: {e}")
    
    def generate_chapter(self):
        """生成章节内容"""
        if not self.current_project:
            print("❌ 请先创建或加载一个项目")
            return
        
        try:
            chapter_num = int(input("请输入章节编号: "))
            chapter_outline = input("请输入本章节的大纲描述: ").strip()
            
            if not chapter_outline:
                print("❌ 章节大纲不能为空")
                return
            
            word_count = input("请输入目标字数 (默认2000): ").strip()
            word_count = int(word_count) if word_count.isdigit() else 2000
            
            print(f"\n✍️  正在生成第{chapter_num}章内容...")
            
            # 查找前情提要
            previous_summary = ""
            chapters_dir = os.path.join(self.current_project, "chapters")
            if os.path.exists(chapters_dir) and chapter_num > 1:
                summary_file = os.path.join(chapters_dir, f"chapter_{chapter_num-1}_summary.txt")
                if os.path.exists(summary_file):
                    with open(summary_file, 'r', encoding='utf-8') as f:
                        previous_summary = f.read()
            
            chapter_content = self.generator.generate_chapter(
                chapter_num, chapter_outline, previous_summary, word_count
            )
            
            # 保存章节
            if not os.path.exists(chapters_dir):
                os.makedirs(chapters_dir)
            
            chapter_path = os.path.join(chapters_dir, f"chapter_{chapter_num}.txt")
            with open(chapter_path, 'w', encoding='utf-8') as f:
                f.write(chapter_content)
            
            print(f"✅ 第{chapter_num}章生成完成并保存到: {chapter_path}")
            print("\n📖 章节预览:")
            print("-" * 50)
            print(chapter_content[:500] + "..." if len(chapter_content) > 500 else chapter_content)
            
        except ValueError:
            print("❌ 请输入有效的章节编号")
        except Exception as e:
            print(f"❌ 生成章节失败: {e}")
    
    def generate_character_profile(self):
        """生成角色档案"""
        if not self.current_project:
            print("❌ 请先创建或加载一个项目")
            return
        
        config_path = os.path.join(self.current_project, "novel_ideas.json")
        if not os.path.exists(config_path):
            print("❌ 找不到项目配置文件")
            return
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                novel_ideas = json.load(f)
            
            characters = novel_ideas.get('characters', {})
            
            print("\n👤 可用角色:")
            print("1. 主角")
            print("2. 反派")
            print("3. 配角")
            
            choice = input("请选择要生成档案的角色类型: ").strip()
            
            character_info = None
            if choice == "1":
                character_info = characters.get('protagonist', {})
            elif choice == "2":
                character_info = characters.get('antagonist', {})
            elif choice == "3":
                supporting = characters.get('supporting_characters', [])
                if supporting:
                    for i, char in enumerate(supporting):
                        print(f"{i+1}. {char.get('name', '未命名')}")
                    try:
                        idx = int(input("请选择配角编号: ")) - 1
                        if 0 <= idx < len(supporting):
                            character_info = supporting[idx]
                    except ValueError:
                        print("❌ 无效的选择")
                        return
            
            if not character_info:
                print("❌ 找不到角色信息")
                return
            
            print("\n👤 正在生成角色档案...")
            profile = self.generator.generate_character_profile(character_info)
            
            # 保存角色档案
            profiles_dir = os.path.join(self.current_project, "characters")
            if not os.path.exists(profiles_dir):
                os.makedirs(profiles_dir)
            
            char_name = character_info.get('name', 'unknown')
            profile_path = os.path.join(profiles_dir, f"{char_name}_profile.txt")
            
            with open(profile_path, 'w', encoding='utf-8') as f:
                f.write(profile)
            
            print(f"✅ 角色档案生成完成并保存到: {profile_path}")
            print("\n👤 档案预览:")
            print("-" * 50)
            print(profile[:600] + "..." if len(profile) > 600 else profile)
            
        except Exception as e:
            print(f"❌ 生成角色档案失败: {e}")
    
    def show_project_status(self):
        """显示项目状态"""
        if not self.current_project:
            print("❌ 没有加载任何项目")
            return
        
        print(f"\n📊 项目状态: {os.path.basename(self.current_project)}")
        print("-" * 50)
        
        # 检查各种文件
        config_path = os.path.join(self.current_project, "novel_ideas.json")
        print(f"📝 配置文件: {'✅' if os.path.exists(config_path) else '❌'}")
        
        outline_files = [f for f in os.listdir(self.current_project) if f.startswith('outline_')]
        print(f"📋 大纲文件: {len(outline_files)} 个")
        
        chapters_dir = os.path.join(self.current_project, "chapters")
        if os.path.exists(chapters_dir):
            chapters = [f for f in os.listdir(chapters_dir) if f.startswith('chapter_') and f.endswith('.txt')]
            print(f"📖 章节文件: {len(chapters)} 个")
        else:
            print("📖 章节文件: 0 个")
        
        characters_dir = os.path.join(self.current_project, "characters")
        if os.path.exists(characters_dir):
            profiles = [f for f in os.listdir(characters_dir) if f.endswith('_profile.txt')]
            print(f"👤 角色档案: {len(profiles)} 个")
        else:
            print("👤 角色档案: 0 个")
    
    def show_help(self):
        """显示帮助信息"""
        print("\n❓ 使用帮助")
        print("="*50)
        print("1. 首先创建一个新项目或加载现有项目")
        print("2. 编辑项目中的 novel_ideas.json 文件，填入你的创意")
        print("3. 生成小说大纲作为创作基础")
        print("4. 根据大纲逐章生成内容")
        print("5. 可以生成详细的角色档案和世界观设定")
        print("\n💡 提示:")
        print("- 所有生成的内容都会保存在项目目录中")
        print("- 可以随时查看项目状态了解进度")
        print("- 建议先完善配置文件再开始生成内容")
        print("="*50)
    
    def run(self):
        """运行主程序"""
        print("🎉 欢迎使用 AI 小说创作助手!")
        
        while True:
            self.show_menu()
            
            try:
                choice = input("\n请选择功能 (0-9): ").strip()
                
                if choice == "1":
                    self.create_new_project()
                elif choice == "2":
                    self.load_project()
                elif choice == "3":
                    self.generate_outline()
                elif choice == "4":
                    self.generate_chapter()
                elif choice == "5":
                    self.generate_character_profile()
                elif choice == "6":
                    print("🌍 世界观生成功能开发中...")
                elif choice == "7":
                    self.show_project_status()
                elif choice == "8":
                    print("💾 项目自动保存中...")
                elif choice == "9":
                    self.show_help()
                elif choice == "0":
                    print("👋 感谢使用 AI 小说创作助手，再见!")
                    break
                else:
                    print("❌ 无效的选择，请重新输入")
                    
            except KeyboardInterrupt:
                print("\n\n👋 程序已退出")
                break
            except Exception as e:
                print(f"❌ 发生错误: {e}")

if __name__ == "__main__":
    writer = NovelWriter()
    writer.run()