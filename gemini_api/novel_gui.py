#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI小说创作助手 - GUI版本
为不熟悉命令行的用户提供图形化界面
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext, simpledialog
import json
import os
import threading
from datetime import datetime
from novel_generator import NovelGenerator
from batch_generator import BatchNovelGenerator
from logger_config import NovelLogger

class NovelGUI:
    """小说创作助手GUI主类"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("🖋️ AI小说创作助手")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f0f0f0')
        
        # 初始化日志系统
        self.logger = NovelLogger.get_gui_logger()
        NovelLogger.log_session_start(self.logger, "GUI界面")
        
        # 初始化变量
        self.generator = None
        self.current_project = None
        self.project_config = None
        
        # 创建界面
        self.create_widgets()
        
        # 尝试初始化生成器
        self.init_generator()
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def init_generator(self):
        """初始化AI生成器"""
        try:
            self.logger.info("开始初始化AI生成器")
            self.generator = NovelGenerator()
            self.status_var.set("✅ AI生成器初始化成功")
            self.logger.info("AI生成器初始化成功")
        except Exception as e:
            error_msg = f"AI生成器初始化失败: {e}"
            self.status_var.set(f"❌ {error_msg}")
            NovelLogger.log_error_with_context(self.logger, e, "初始化AI生成器")
            messagebox.showerror("错误", f"AI生成器初始化失败:\n{e}\n\n请检查API密钥配置")
    
    def create_widgets(self):
        """创建GUI组件"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # 创建左侧控制面板
        self.create_control_panel(main_frame)
        
        # 创建右侧内容区域
        self.create_content_area(main_frame)
        
        # 创建底部状态栏
        self.create_status_bar(main_frame)
    
    def create_control_panel(self, parent):
        """创建左侧控制面板"""
        control_frame = ttk.LabelFrame(parent, text="📋 控制面板", padding="10")
        control_frame.grid(row=0, column=0, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # 项目管理区域
        project_frame = ttk.LabelFrame(control_frame, text="📁 项目管理", padding="5")
        project_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(project_frame, text="🆕 新建项目", command=self.new_project).pack(fill=tk.X, pady=2)
        ttk.Button(project_frame, text="📂 打开项目", command=self.open_project).pack(fill=tk.X, pady=2)
        ttk.Button(project_frame, text="💾 保存项目", command=self.save_project).pack(fill=tk.X, pady=2)
        
        # 当前项目信息
        self.project_info_var = tk.StringVar(value="未选择项目")
        ttk.Label(project_frame, textvariable=self.project_info_var, wraplength=200).pack(fill=tk.X, pady=5)
        
        # 配置编辑区域
        config_frame = ttk.LabelFrame(control_frame, text="⚙️ 配置编辑", padding="5")
        config_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(config_frame, text="📝 编辑配置", command=self.edit_config).pack(fill=tk.X, pady=2)
        ttk.Button(config_frame, text="🔄 重新加载", command=self.reload_config).pack(fill=tk.X, pady=2)
        
        # 内容生成区域
        generate_frame = ttk.LabelFrame(control_frame, text="🎯 内容生成", padding="5")
        generate_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(generate_frame, text="📋 生成大纲", command=self.generate_outline).pack(fill=tk.X, pady=2)
        ttk.Button(generate_frame, text="👤 生成角色档案", command=self.generate_characters).pack(fill=tk.X, pady=2)
        ttk.Button(generate_frame, text="🌍 生成世界观", command=self.generate_world).pack(fill=tk.X, pady=2)
        ttk.Button(generate_frame, text="📖 生成章节", command=self.generate_chapter).pack(fill=tk.X, pady=2)
        
        # 批量操作区域
        batch_frame = ttk.LabelFrame(control_frame, text="🔄 批量操作", padding="5")
        batch_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(batch_frame, text="🚀 批量生成章节", command=self.batch_generate_chapters).pack(fill=tk.X, pady=2)
        ttk.Button(batch_frame, text="📊 生成项目报告", command=self.generate_report).pack(fill=tk.X, pady=2)
        
        # 工具区域
        tools_frame = ttk.LabelFrame(control_frame, text="🛠️ 工具", padding="5")
        tools_frame.pack(fill=tk.X)
        
        ttk.Button(tools_frame, text="📁 打开项目文件夹", command=self.open_project_folder).pack(fill=tk.X, pady=2)
        ttk.Button(tools_frame, text="❓ 帮助", command=self.show_help).pack(fill=tk.X, pady=2)
    
    def create_content_area(self, parent):
        """创建右侧内容区域"""
        content_frame = ttk.LabelFrame(parent, text="📄 内容区域", padding="10")
        content_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        # 创建标签页
        self.notebook = ttk.Notebook(content_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置编辑标签页
        self.create_config_tab()
        
        # 内容查看标签页
        self.create_content_tab()
        
        # 日志标签页
        self.create_log_tab()
    
    def create_config_tab(self):
        """创建配置编辑标签页"""
        config_tab = ttk.Frame(self.notebook)
        self.notebook.add(config_tab, text="⚙️ 项目配置")
        
        # 创建配置表单
        canvas = tk.Canvas(config_tab)
        scrollbar = ttk.Scrollbar(config_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 配置表单字段
        self.config_vars = {}
        self.create_config_form(scrollable_frame)
    
    def create_config_form(self, parent):
        """创建配置表单"""
        # 小说基本配置
        basic_frame = ttk.LabelFrame(parent, text="📚 小说基本信息", padding="10")
        basic_frame.pack(fill=tk.X, pady=5)
        
        self.config_vars['title'] = tk.StringVar()
        ttk.Label(basic_frame, text="小说标题:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(basic_frame, textvariable=self.config_vars['title'], width=40).grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2)
        
        self.config_vars['genre'] = tk.StringVar()
        ttk.Label(basic_frame, text="小说类型:").grid(row=1, column=0, sticky=tk.W, pady=2)
        genre_combo = ttk.Combobox(basic_frame, textvariable=self.config_vars['genre'], width=37)
        genre_combo['values'] = ('科幻', '奇幻', '言情', '悬疑', '历史', '现实', '武侠', '都市', '其他')
        genre_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2)
        
        self.config_vars['target_chapters'] = tk.StringVar()
        ttk.Label(basic_frame, text="目标章节数:").grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Entry(basic_frame, textvariable=self.config_vars['target_chapters'], width=40).grid(row=2, column=1, sticky=(tk.W, tk.E), pady=2)
        
        basic_frame.columnconfigure(1, weight=1)
        
        # 故事创意
        idea_frame = ttk.LabelFrame(parent, text="💡 故事创意", padding="10")
        idea_frame.pack(fill=tk.X, pady=5)
        
        self.config_vars['core_concept'] = tk.Text(idea_frame, height=3, width=50)
        ttk.Label(idea_frame, text="核心创意:").pack(anchor=tk.W)
        self.config_vars['core_concept'].pack(fill=tk.X, pady=2)
        
        self.config_vars['theme'] = tk.Text(idea_frame, height=2, width=50)
        ttk.Label(idea_frame, text="主题思想:").pack(anchor=tk.W, pady=(10, 0))
        self.config_vars['theme'].pack(fill=tk.X, pady=2)
        
        # 角色信息
        char_frame = ttk.LabelFrame(parent, text="👤 主要角色", padding="10")
        char_frame.pack(fill=tk.X, pady=5)
        
        # 主角信息
        ttk.Label(char_frame, text="主角姓名:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.config_vars['protagonist_name'] = tk.StringVar()
        ttk.Entry(char_frame, textvariable=self.config_vars['protagonist_name'], width=20).grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2)
        
        ttk.Label(char_frame, text="主角背景:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.config_vars['protagonist_background'] = tk.Text(char_frame, height=2, width=30)
        self.config_vars['protagonist_background'].grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2)
        
        char_frame.columnconfigure(1, weight=1)
        
        # 保存按钮
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=10)
        ttk.Button(button_frame, text="💾 保存配置", command=self.save_config).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="🔄 重置", command=self.reset_config).pack(side=tk.RIGHT, padx=(0, 10))
    
    def create_content_tab(self):
        """创建内容查看标签页"""
        content_tab = ttk.Frame(self.notebook)
        self.notebook.add(content_tab, text="📖 生成内容")
        
        # 创建内容显示区域
        self.content_text = scrolledtext.ScrolledText(content_tab, wrap=tk.WORD, width=80, height=30)
        self.content_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 内容操作按钮
        content_buttons = ttk.Frame(content_tab)
        content_buttons.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(content_buttons, text="📋 复制内容", command=self.copy_content).pack(side=tk.LEFT)
        ttk.Button(content_buttons, text="💾 保存到文件", command=self.save_content_to_file).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Button(content_buttons, text="🗑️ 清空内容", command=self.clear_content).pack(side=tk.LEFT, padx=(10, 0))
    
    def create_log_tab(self):
        """创建日志标签页"""
        log_tab = ttk.Frame(self.notebook)
        self.notebook.add(log_tab, text="📝 操作日志")
        
        self.log_text = scrolledtext.ScrolledText(log_tab, wrap=tk.WORD, width=80, height=30)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 日志操作按钮
        log_buttons = ttk.Frame(log_tab)
        log_buttons.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(log_buttons, text="🗑️ 清空日志", command=self.clear_log).pack(side=tk.LEFT)
        ttk.Button(log_buttons, text="💾 保存日志", command=self.save_log).pack(side=tk.LEFT, padx=(10, 0))
    
    def create_status_bar(self, parent):
        """创建状态栏"""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.status_var = tk.StringVar(value="准备就绪")
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.pack(side=tk.LEFT)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var, length=200)
        self.progress_bar.pack(side=tk.RIGHT)
    
    def log_message(self, message):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def new_project(self):
        """创建新项目"""
        project_name = tk.simpledialog.askstring("新建项目", "请输入项目名称:")
        if not project_name:
            return
        
        projects_dir = "projects"
        if not os.path.exists(projects_dir):
            os.makedirs(projects_dir)
        
        project_path = os.path.join(projects_dir, project_name)
        if os.path.exists(project_path):
            messagebox.showerror("错误", f"项目 '{project_name}' 已存在")
            return
        
        try:
            os.makedirs(project_path)
            
            # 复制模板配置
            template_path = "novel_ideas.json"
            config_path = os.path.join(project_path, "novel_ideas.json")
            
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(template_content)
            
            self.current_project = project_path
            self.project_info_var.set(f"当前项目: {project_name}")
            self.load_project_config()
            
            self.log_message(f"✅ 项目 '{project_name}' 创建成功")
            self.status_var.set(f"项目 '{project_name}' 已创建")
            
        except Exception as e:
            messagebox.showerror("错误", f"创建项目失败: {e}")
            self.log_message(f"❌ 创建项目失败: {e}")
    
    def open_project(self):
        """打开现有项目"""
        projects_dir = "projects"
        if not os.path.exists(projects_dir):
            messagebox.showinfo("提示", "没有找到任何项目")
            return
        
        project_path = filedialog.askdirectory(
            title="选择项目文件夹",
            initialdir=projects_dir
        )
        
        if not project_path:
            return
        
        config_path = os.path.join(project_path, "novel_ideas.json")
        if not os.path.exists(config_path):
            messagebox.showerror("错误", "所选文件夹不是有效的项目目录")
            return
        
        self.current_project = project_path
        project_name = os.path.basename(project_path)
        self.project_info_var.set(f"当前项目: {project_name}")
        self.load_project_config()
        
        self.log_message(f"✅ 项目 '{project_name}' 加载成功")
        self.status_var.set(f"项目 '{project_name}' 已加载")
    
    def load_project_config(self):
        """加载项目配置到表单"""
        if not self.current_project:
            return
        
        config_path = os.path.join(self.current_project, "novel_ideas.json")
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.project_config = json.load(f)
            
            # 填充表单
            novel_config = self.project_config.get('novel_config', {})
            self.config_vars['title'].set(novel_config.get('title', ''))
            self.config_vars['genre'].set(novel_config.get('genre', ''))
            self.config_vars['target_chapters'].set(str(novel_config.get('target_chapters', '')))
            
            main_idea = self.project_config.get('main_idea', {})
            self.config_vars['core_concept'].delete('1.0', tk.END)
            self.config_vars['core_concept'].insert('1.0', main_idea.get('core_concept', ''))
            self.config_vars['theme'].delete('1.0', tk.END)
            self.config_vars['theme'].insert('1.0', main_idea.get('theme', ''))
            
            protagonist = self.project_config.get('characters', {}).get('protagonist', {})
            self.config_vars['protagonist_name'].set(protagonist.get('name', ''))
            self.config_vars['protagonist_background'].delete('1.0', tk.END)
            self.config_vars['protagonist_background'].insert('1.0', protagonist.get('background', ''))
            
        except Exception as e:
            messagebox.showerror("错误", f"加载配置失败: {e}")
            self.log_message(f"❌ 加载配置失败: {e}")
    
    def save_config(self):
        """保存配置"""
        if not self.current_project:
            messagebox.showwarning("警告", "请先创建或打开一个项目")
            return
        
        try:
            # 更新配置数据
            if not self.project_config:
                self.project_config = {}
            
            # 更新小说配置
            novel_config = self.project_config.setdefault('novel_config', {})
            novel_config['title'] = self.config_vars['title'].get()
            novel_config['genre'] = self.config_vars['genre'].get()
            try:
                novel_config['target_chapters'] = int(self.config_vars['target_chapters'].get())
            except ValueError:
                novel_config['target_chapters'] = 20
            
            # 更新主要创意
            main_idea = self.project_config.setdefault('main_idea', {})
            main_idea['core_concept'] = self.config_vars['core_concept'].get('1.0', tk.END).strip()
            main_idea['theme'] = self.config_vars['theme'].get('1.0', tk.END).strip()
            
            # 更新角色信息
            characters = self.project_config.setdefault('characters', {})
            protagonist = characters.setdefault('protagonist', {})
            protagonist['name'] = self.config_vars['protagonist_name'].get()
            protagonist['background'] = self.config_vars['protagonist_background'].get('1.0', tk.END).strip()
            
            # 保存到文件
            config_path = os.path.join(self.current_project, "novel_ideas.json")
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.project_config, f, ensure_ascii=False, indent=2)
            
            self.log_message("✅ 配置保存成功")
            self.status_var.set("配置已保存")
            messagebox.showinfo("成功", "配置保存成功")
            
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {e}")
            self.log_message(f"❌ 保存配置失败: {e}")
    
    def generate_outline(self):
        """生成小说大纲"""
        if not self.check_project_and_generator():
            return
        
        def generate():
            try:
                self.status_var.set("正在生成大纲...")
                self.progress_var.set(50)
                
                outline = self.generator.generate_outline(self.project_config)
                
                # 保存大纲
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                outline_path = os.path.join(self.current_project, f"outline_{timestamp}.txt")
                
                with open(outline_path, 'w', encoding='utf-8') as f:
                    f.write(outline)
                
                # 显示内容
                self.content_text.delete('1.0', tk.END)
                self.content_text.insert('1.0', outline)
                self.notebook.select(1)  # 切换到内容标签页
                
                self.progress_var.set(100)
                self.status_var.set("大纲生成完成")
                self.log_message(f"✅ 大纲生成完成，已保存到: {outline_path}")
                
            except Exception as e:
                self.progress_var.set(0)
                self.status_var.set("大纲生成失败")
                self.log_message(f"❌ 大纲生成失败: {e}")
                messagebox.showerror("错误", f"大纲生成失败: {e}")
        
        # 在后台线程中执行
        threading.Thread(target=generate, daemon=True).start()
    
    def generate_characters(self):
        """生成角色档案"""
        if not self.check_project_and_generator():
            return
        
        def generate():
            try:
                self.status_var.set("正在生成角色档案...")
                self.progress_var.set(50)
                
                characters = self.generator.generate_character_profiles(self.project_config)
                
                # 保存角色档案
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                characters_path = os.path.join(self.current_project, f"characters_{timestamp}.txt")
                
                with open(characters_path, 'w', encoding='utf-8') as f:
                    f.write(characters)
                
                # 显示内容
                self.content_text.delete('1.0', tk.END)
                self.content_text.insert('1.0', characters)
                self.notebook.select(1)
                
                self.progress_var.set(100)
                self.status_var.set("角色档案生成完成")
                self.log_message(f"✅ 角色档案生成完成，已保存到: {characters_path}")
                
            except Exception as e:
                self.progress_var.set(0)
                self.status_var.set("角色档案生成失败")
                self.log_message(f"❌ 角色档案生成失败: {e}")
                messagebox.showerror("错误", f"角色档案生成失败: {e}")
        
        threading.Thread(target=generate, daemon=True).start()
    
    def generate_world(self):
        """生成世界观设定"""
        if not self.check_project_and_generator():
            return
        
        def generate():
            try:
                self.status_var.set("正在生成世界观设定...")
                self.progress_var.set(50)
                
                world_setting = self.generator.generate_world_setting(self.project_config)
                
                # 保存世界观设定
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                world_path = os.path.join(self.current_project, f"world_setting_{timestamp}.txt")
                
                with open(world_path, 'w', encoding='utf-8') as f:
                    f.write(world_setting)
                
                # 显示内容
                self.content_text.delete('1.0', tk.END)
                self.content_text.insert('1.0', world_setting)
                self.notebook.select(1)
                
                self.progress_var.set(100)
                self.status_var.set("世界观设定生成完成")
                self.log_message(f"✅ 世界观设定生成完成，已保存到: {world_path}")
                
            except Exception as e:
                self.progress_var.set(0)
                self.status_var.set("世界观设定生成失败")
                self.log_message(f"❌ 世界观设定生成失败: {e}")
                messagebox.showerror("错误", f"世界观设定生成失败: {e}")
        
        threading.Thread(target=generate, daemon=True).start()
    
    def generate_chapter(self):
        """生成章节内容"""
        if not self.check_project_and_generator():
            return
        
        # 获取章节信息
        dialog = ChapterDialog(self.root)
        if not dialog.result:
            return
        
        chapter_num, chapter_outline, word_count = dialog.result
        
        def generate():
            try:
                self.status_var.set(f"正在生成第{chapter_num}章...")
                self.progress_var.set(50)
                
                chapter_content = self.generator.generate_chapter(
                    chapter_num, chapter_outline, "", word_count
                )
                
                # 保存章节
                chapters_dir = os.path.join(self.current_project, "chapters")
                if not os.path.exists(chapters_dir):
                    os.makedirs(chapters_dir)
                
                chapter_path = os.path.join(chapters_dir, f"chapter_{chapter_num:02d}.txt")
                with open(chapter_path, 'w', encoding='utf-8') as f:
                    f.write(chapter_content)
                
                # 显示内容
                self.content_text.delete('1.0', tk.END)
                self.content_text.insert('1.0', chapter_content)
                self.notebook.select(1)
                
                self.progress_var.set(100)
                self.status_var.set(f"第{chapter_num}章生成完成")
                self.log_message(f"✅ 第{chapter_num}章生成完成，已保存到: {chapter_path}")
                
            except Exception as e:
                self.progress_var.set(0)
                self.status_var.set("章节生成失败")
                self.log_message(f"❌ 第{chapter_num}章生成失败: {e}")
                messagebox.showerror("错误", f"章节生成失败: {e}")
        
        threading.Thread(target=generate, daemon=True).start()
    
    def batch_generate_chapters(self):
        """批量生成章节"""
        if not self.check_project_and_generator():
            return
        
        # 获取批量生成参数
        dialog = BatchChapterDialog(self.root)
        if not dialog.result:
            return
        
        start_chapter, end_chapter = dialog.result
        
        def generate():
            try:
                batch_generator = BatchNovelGenerator()
                
                for chapter_num in range(start_chapter, end_chapter + 1):
                    self.status_var.set(f"正在生成第{chapter_num}章... ({chapter_num - start_chapter + 1}/{end_chapter - start_chapter + 1})")
                    progress = ((chapter_num - start_chapter + 1) / (end_chapter - start_chapter + 1)) * 100
                    self.progress_var.set(progress)
                    
                    # 生成章节大纲
                    outline = f"第{chapter_num}章大纲（自动生成）"
                    
                    # 生成章节内容
                    chapter_content = self.generator.generate_chapter(
                        chapter_num, outline, "", 2000
                    )
                    
                    # 保存章节
                    chapters_dir = os.path.join(self.current_project, "chapters")
                    if not os.path.exists(chapters_dir):
                        os.makedirs(chapters_dir)
                    
                    chapter_path = os.path.join(chapters_dir, f"chapter_{chapter_num:02d}.txt")
                    with open(chapter_path, 'w', encoding='utf-8') as f:
                        f.write(chapter_content)
                    
                    self.log_message(f"✅ 第{chapter_num}章生成完成")
                
                self.progress_var.set(100)
                self.status_var.set(f"批量生成完成 (第{start_chapter}-{end_chapter}章)")
                self.log_message(f"✅ 批量生成完成，共生成 {end_chapter - start_chapter + 1} 章")
                messagebox.showinfo("完成", f"批量生成完成！\n共生成 {end_chapter - start_chapter + 1} 章节")
                
            except Exception as e:
                self.progress_var.set(0)
                self.status_var.set("批量生成失败")
                self.log_message(f"❌ 批量生成失败: {e}")
                messagebox.showerror("错误", f"批量生成失败: {e}")
        
        threading.Thread(target=generate, daemon=True).start()
    
    def generate_report(self):
        """生成项目报告"""
        if not self.current_project:
            messagebox.showwarning("警告", "请先创建或打开一个项目")
            return
        
        try:
            # 统计项目信息
            project_name = os.path.basename(self.current_project)
            chapters_dir = os.path.join(self.current_project, "chapters")
            
            chapter_count = 0
            total_words = 0
            
            if os.path.exists(chapters_dir):
                for filename in os.listdir(chapters_dir):
                    if filename.endswith('.txt'):
                        chapter_count += 1
                        filepath = os.path.join(chapters_dir, filename)
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                            total_words += len(content)
            
            # 生成报告
            report = f"""
📊 项目报告

项目名称: {project_name}
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📈 统计信息:
- 已生成章节数: {chapter_count}
- 总字符数: {total_words:,}
- 平均每章字符数: {total_words // chapter_count if chapter_count > 0 else 0:,}

📁 项目文件:
"""
            
            # 列出项目文件
            for root, dirs, files in os.walk(self.current_project):
                level = root.replace(self.current_project, '').count(os.sep)
                indent = '  ' * level
                report += f"{indent}- {os.path.basename(root)}/\n"
                subindent = '  ' * (level + 1)
                for file in files:
                    report += f"{subindent}- {file}\n"
            
            # 显示报告
            self.content_text.delete('1.0', tk.END)
            self.content_text.insert('1.0', report)
            self.notebook.select(1)
            
            # 保存报告
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = os.path.join(self.current_project, f"project_report_{timestamp}.txt")
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            
            self.status_var.set("项目报告生成完成")
            self.log_message(f"✅ 项目报告生成完成，已保存到: {report_path}")
            
        except Exception as e:
            self.log_message(f"❌ 生成项目报告失败: {e}")
            messagebox.showerror("错误", f"生成项目报告失败: {e}")
    
    def check_project_and_generator(self):
        """检查项目和生成器状态"""
        if not self.current_project:
            messagebox.showwarning("警告", "请先创建或打开一个项目")
            return False
        
        if not self.generator:
            messagebox.showerror("错误", "AI生成器未初始化，请检查API配置")
            return False
        
        if not self.project_config:
            messagebox.showwarning("警告", "请先配置项目信息")
            return False
        
        return True
    
    def copy_content(self):
        """复制内容到剪贴板"""
        content = self.content_text.get('1.0', tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self.status_var.set("内容已复制到剪贴板")
    
    def save_content_to_file(self):
        """保存内容到文件"""
        content = self.content_text.get('1.0', tk.END).strip()
        if not content:
            messagebox.showwarning("警告", "没有内容可保存")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.status_var.set(f"内容已保存到: {filename}")
                self.log_message(f"✅ 内容已保存到: {filename}")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {e}")
    
    def clear_content(self):
        """清空内容"""
        self.content_text.delete('1.0', tk.END)
        self.status_var.set("内容已清空")
    
    def clear_log(self):
        """清空日志"""
        self.log_text.delete('1.0', tk.END)
        self.status_var.set("日志已清空")
    
    def save_log(self):
        """保存日志"""
        log_content = self.log_text.get('1.0', tk.END).strip()
        if not log_content:
            messagebox.showwarning("警告", "没有日志可保存")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            initialfilename=f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                self.status_var.set(f"日志已保存到: {filename}")
                self.log_message(f"✅ 日志已保存到: {filename}")
            except Exception as e:
                messagebox.showerror("错误", f"保存日志失败: {e}")
    
    def edit_config(self):
        """编辑配置"""
        if not self.current_project:
            messagebox.showwarning("警告", "请先创建或打开一个项目")
            return
        
        # 切换到配置标签页
        self.notebook.select(0)
        self.status_var.set("请在配置标签页中编辑项目配置")
    
    def reload_config(self):
        """重新加载配置"""
        if not self.current_project:
            messagebox.showwarning("警告", "请先创建或打开一个项目")
            return
        
        self.load_project_config()
        self.status_var.set("配置已重新加载")
        self.log_message("✅ 配置已重新加载")
    
    def save_project(self):
        """保存项目"""
        if not self.current_project:
            messagebox.showwarning("警告", "请先创建或打开一个项目")
            return
        
        # 保存配置
        self.save_config()
        
        # 可以在这里添加其他需要保存的项目数据
        self.status_var.set("项目已保存")
        self.log_message("✅ 项目已保存")
    
    def open_project_folder(self):
        """打开项目文件夹"""
        if not self.current_project:
            messagebox.showwarning("警告", "请先创建或打开一个项目")
            return
        
        try:
            # Windows系统打开文件夹
            os.startfile(self.current_project)
            self.status_var.set("项目文件夹已打开")
        except Exception as e:
            messagebox.showerror("错误", f"打开文件夹失败: {e}")
    
    def reset_config(self):
        """重置配置表单"""
        for var in self.config_vars.values():
            if isinstance(var, tk.StringVar):
                var.set('')
            elif isinstance(var, tk.Text):
                var.delete('1.0', tk.END)
        
        self.status_var.set("配置表单已重置")
    
    def show_help(self):
        """显示帮助信息"""
        help_text = """
🖋️ AI小说创作助手使用指南

1. 项目管理:
   - 新建项目: 创建一个新的小说项目
   - 打开项目: 加载现有的项目
   - 保存项目: 保存当前项目的所有更改

2. 配置编辑:
   - 在"项目配置"标签页中填写小说的基本信息
   - 包括标题、类型、角色设定等
   - 点击"保存配置"保存更改

3. 内容生成:
   - 生成大纲: 根据配置生成详细的小说大纲
   - 生成角色档案: 为主要角色创建详细档案
   - 生成章节: 根据大纲生成具体章节内容

4. 查看结果:
   - 在"生成内容"标签页查看AI生成的内容
   - 可以复制、保存或清空内容

5. 操作日志:
   - 在"操作日志"标签页查看所有操作记录
   - 可以保存日志用于问题排查

注意事项:
- 确保API密钥配置正确
- 生成内容需要网络连接
- 建议先完善项目配置再开始生成
"""
        
        help_window = tk.Toplevel(self.root)
        help_window.title("帮助")
        help_window.geometry("600x500")
        
        help_text_widget = scrolledtext.ScrolledText(help_window, wrap=tk.WORD)
        help_text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        help_text_widget.insert('1.0', help_text)
        help_text_widget.config(state=tk.DISABLED)

class ChapterDialog:
    """章节生成对话框"""
    
    def __init__(self, parent):
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("生成章节")
        self.dialog.geometry("400x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 居中显示
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self.create_widgets()
        
        # 等待对话框关闭
        self.dialog.wait_window()
    
    def create_widgets(self):
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 章节编号
        ttk.Label(main_frame, text="章节编号:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.chapter_num_var = tk.StringVar(value="1")
        ttk.Entry(main_frame, textvariable=self.chapter_num_var, width=10).grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # 章节大纲
        ttk.Label(main_frame, text="章节大纲:").grid(row=1, column=0, sticky=(tk.W, tk.N), pady=5)
        self.outline_text = tk.Text(main_frame, height=8, width=40)
        self.outline_text.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # 目标字数
        ttk.Label(main_frame, text="目标字数:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.word_count_var = tk.StringVar(value="2000")
        ttk.Entry(main_frame, textvariable=self.word_count_var, width=10).grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # 按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=20)
        
        ttk.Button(button_frame, text="生成", command=self.ok_clicked).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=self.cancel_clicked).pack(side=tk.LEFT, padx=5)
        
        main_frame.columnconfigure(1, weight=1)
    
    def ok_clicked(self):
        try:
            chapter_num = int(self.chapter_num_var.get())
            chapter_outline = self.outline_text.get('1.0', tk.END).strip()
            word_count = int(self.word_count_var.get())
            
            if not chapter_outline:
                messagebox.showwarning("警告", "请输入章节大纲")
                return
            
            self.result = (chapter_num, chapter_outline, word_count)
            self.dialog.destroy()
            
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
    
    def cancel_clicked(self):
        self.dialog.destroy()

class BatchChapterDialog:
    """批量章节生成对话框"""
    
    def __init__(self, parent):
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("批量生成章节")
        self.dialog.geometry("350x200")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 居中显示
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self.create_widgets()
        
        # 等待对话框关闭
        self.dialog.wait_window()
    
    def create_widgets(self):
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 起始章节
        ttk.Label(main_frame, text="起始章节:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.start_chapter_var = tk.StringVar(value="1")
        ttk.Entry(main_frame, textvariable=self.start_chapter_var, width=10).grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # 结束章节
        ttk.Label(main_frame, text="结束章节:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.end_chapter_var = tk.StringVar(value="5")
        ttk.Entry(main_frame, textvariable=self.end_chapter_var, width=10).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # 提示信息
        info_label = ttk.Label(main_frame, text="注意：批量生成将使用自动生成的章节大纲\n每章约2000字，请确保有足够的API配额", 
                              foreground="gray", wraplength=300)
        info_label.grid(row=2, column=0, columnspan=2, pady=10)
        
        # 按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="开始生成", command=self.ok_clicked).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=self.cancel_clicked).pack(side=tk.LEFT, padx=5)
    
    def ok_clicked(self):
        try:
            start_chapter = int(self.start_chapter_var.get())
            end_chapter = int(self.end_chapter_var.get())
            
            if start_chapter < 1 or end_chapter < 1:
                messagebox.showerror("错误", "章节编号必须大于0")
                return
            
            if start_chapter > end_chapter:
                messagebox.showerror("错误", "起始章节不能大于结束章节")
                return
            
            if end_chapter - start_chapter + 1 > 20:
                if not messagebox.askyesno("确认", f"您要生成 {end_chapter - start_chapter + 1} 章内容，这可能需要较长时间和大量API调用。\n确定要继续吗？"):
                    return
            
            self.result = (start_chapter, end_chapter)
            self.dialog.destroy()
            
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
    
    def cancel_clicked(self):
        self.dialog.destroy()

    def on_closing(self):
        """程序关闭时的清理工作"""
        try:
            self.logger.info("用户关闭GUI界面")
            NovelLogger.log_session_end(self.logger, "GUI界面")
        except:
            pass  # 避免关闭时的日志错误影响程序退出
        finally:
            self.root.destroy()

def main():
    """主函数"""
    logger = NovelLogger.get_main_logger()
    NovelLogger.log_session_start(logger, "GUI主程序")
    
    try:
        logger.info("启动GUI界面")
        root = tk.Tk()
        app = NovelGUI(root)
        root.mainloop()
        logger.info("GUI程序正常退出")
    except Exception as e:
        NovelLogger.log_error_with_context(logger, e, "GUI主程序")
        print(f"GUI程序错误: {e}")
    finally:
        NovelLogger.log_session_end(logger, "GUI主程序")

if __name__ == "__main__":
    main()