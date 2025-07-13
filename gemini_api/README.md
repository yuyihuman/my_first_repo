# 🖋️ AI 自动写小说程序

基于 Google Gemini API 的智能小说创作工具，帮助您从创意到完整小说的全流程创作。

## ✨ 功能特性

- 📝 **智能大纲生成**: 根据您的创意自动生成详细的小说大纲
- 👤 **角色档案创建**: 为主角、反派、配角生成详细的人物档案
- 🌍 **世界观构建**: 创建丰富的故事背景和世界设定
- 📖 **章节内容生成**: 逐章生成高质量的小说内容
- 🔄 **批量处理**: 支持批量生成多个章节和完整项目
- 💾 **项目管理**: 完整的项目文件组织和管理系统
- 📊 **统一日志系统**: 完整的操作记录和错误追踪，便于问题分析
- 🎯 **可扩展架构**: 模块化设计，易于扩展新功能

## 📁 项目结构

```
gemini_api/
├── 📋 核心文件
│   ├── novel_ideas.json          # 小说创意配置模板
│   ├── novel_generator.py        # 核心AI生成模块
│   ├── batch_generator.py       # 批量生成工具
│   ├── logger_config.py         # 统一日志系统配置
│   ├── apikey.md               # API密钥文件
│   ├── requirements.txt        # 项目依赖
│   └── .gitignore             # Git忽略文件配置
│
├── 🖥️ GUI图形界面
│   ├── novel_gui.py            # GUI主程序
│   ├── run_gui.py             # GUI启动脚本
│   ├── 启动GUI.bat            # Windows批处理启动文件
│   └── GUI使用指南.md         # GUI详细使用说明
│
├── 💻 命令行工具
│   └── novel_writer.py        # 交互式创作工具
│
├── 📚 文档
│   └── README.md             # 项目总体说明
│
├── 📁 生成的项目文件夹
│   └── projects/
│       └── [项目名称]/
│           ├── novel_ideas.json    # 项目配置
│           ├── outline_*.txt      # 生成的大纲
│           ├── characters_*.txt   # 角色档案
│           ├── world_setting_*.txt # 世界观设定
│           ├── chapters/          # 章节文件夹
│           │   ├── chapter_01.txt
│           │   ├── chapter_02.txt
│           │   └── ...
│
└── 📊 日志文件夹 (自动生成，Git忽略)
    └── logs/
        ├── main.log              # 主程序日志
        ├── generator.log         # 生成器模块日志
        ├── gui.log              # GUI界面日志
        ├── batch.log            # 批量处理日志
        └── api.log              # API调用日志
            └── project_report_*.txt # 项目报告
```

## 🚀 快速开始

### 环境准备

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **配置API密钥**
   - 在项目根目录创建 `apikey.md` 文件
   - 将您的 Gemini API 密钥写入文件中

### 使用方法

#### 🖥️ GUI图形界面版本（推荐）

**适合不熟悉命令行的用户**

```bash
python run_gui.py
```

或者直接双击 `run_gui.py` 文件启动图形界面。

**GUI功能特性：**
- 📁 项目管理：新建、打开、保存项目
- ⚙️ 可视化配置编辑：通过表单编辑小说设定
- 🎯 一键内容生成：大纲、角色、世界观、章节
- 🔄 批量操作：批量生成多个章节
- 📊 项目报告：统计项目进度和文件
- 📝 操作日志：记录所有操作历史
- 💾 内容管理：复制、保存、导出生成的内容

#### 💻 命令行版本

**适合熟悉编程的用户**

##### 1. 交互式创作

```bash
python novel_writer.py
```

启动交互式小说创作工具，通过菜单选择不同功能：
- 创建/加载项目
- 生成小说大纲
- 生成章节内容
- 生成角色档案
- 查看项目状态

##### 2. 批量生成

```bash
python batch_generator.py
```

自动批量生成小说的各个组件：
- 完整大纲
- 所有角色档案
- 世界观设定
- 批量章节内容

##### 3. 编程调用

```python
from novel_generator import NovelGenerator

# 初始化生成器
generator = NovelGenerator()

# 加载配置
with open('novel_ideas.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# 生成大纲
outline = generator.generate_outline(config)
print(outline)

# 生成章节
chapter = generator.generate_chapter(1, "章节大纲", "", 2000)
print(chapter)
```

## 📝 配置文件说明

### novel_ideas.json 结构

```json
{
  "novel_config": {
    "title": "小说标题",
    "genre": "类型（科幻/奇幻/言情等）",
    "target_length": "长度（短篇/中篇/长篇）",
    "target_chapters": 20,
    "writing_style": "人称（第一人称/第三人称）",
    "tone": "语调（轻松/严肃/幽默等）"
  },
  "main_idea": {
    "core_concept": "核心创意",
    "theme": "主题思想",
    "setting": {
      "time_period": "时代背景",
      "location": "地点设定",
      "world_building": "世界观"
    }
  },
  "characters": {
    "protagonist": {
      "name": "主角姓名",
      "background": "背景故事",
      "goals": "目标动机"
    },
    "antagonist": {
      "name": "反派姓名",
      "motivation": "反派动机"
    }
  },
  "plot_elements": {
    "inciting_incident": "引发事件",
    "main_conflict": "主要冲突",
    "climax_idea": "高潮构想"
  }
}
```

## 🛠️ 核心模块

### NovelGenerator 类

核心生成器，提供以下主要方法：

- `generate_outline(novel_ideas)`: 生成小说大纲
- `generate_chapter(chapter_num, outline, previous_summary)`: 生成章节内容
- `generate_character_profile(character_info)`: 生成角色档案
- `generate_world_building(setting_info)`: 生成世界观设定

### NovelWriter 类

交互式创作工具，提供用户友好的界面：

- 项目管理（创建、加载、保存）
- 大纲和章节生成
- 角色档案创建
- 项目状态查看

### BatchNovelGenerator 类

批量处理工具，支持：

- 完整项目自动生成
- 批量章节创作
- 所有角色档案生成
- 项目报告生成

## 📖 使用示例

### 创建科幻小说项目

1. 运行 `python novel_writer.py`
2. 选择 "1. 创建新的小说项目"
3. 输入项目名称："星际探险"
4. 编辑生成的配置文件，设置科幻背景
5. 生成大纲和角色档案
6. 开始章节创作

### 批量生成完整小说

```bash
# 创建项目目录
mkdir projects/my_sci_fi_novel

# 复制并编辑配置文件
cp novel_ideas.json projects/my_sci_fi_novel/

# 批量生成完整项目
python batch_generator.py projects/my_sci_fi_novel
```

## ⚙️ 高级配置

### 日志系统

项目集成了统一的日志系统，提供完整的操作记录和错误追踪：

#### 日志文件说明

- **main.log**: 主程序运行日志，记录程序启动、关闭和主要操作
- **generator.log**: AI生成模块日志，记录API调用、生成过程和结果
- **gui.log**: GUI界面日志，记录用户界面操作和事件
- **batch.log**: 批量处理日志，记录批量生成任务的进度和状态
- **api.log**: API调用详细日志，包含请求参数、响应时间和错误信息

#### 日志特性

- 🔄 **自动轮转**: 日志文件达到10MB时自动轮转，保留最近5个文件
- 🧹 **自动清理**: 自动删除30天前的旧日志文件
- 📊 **分级记录**: 支持DEBUG、INFO、WARNING、ERROR等不同级别
- 🔍 **详细追踪**: 记录API调用详情、错误堆栈和性能指标
- 📁 **统一管理**: 所有日志文件统一存放在 `logs/` 目录下

#### 日志配置

日志系统通过 `logger_config.py` 模块管理，支持：

```python
from logger_config import NovelLogger

# 获取特定模块的日志记录器
logger = NovelLogger.get_logger('your_module')

# 记录不同级别的日志
logger.info("操作成功")
logger.warning("警告信息")
logger.error("错误信息")
```

### API 参数调整

在 `NovelGenerator` 类中可以调整：

- `max_tokens`: 控制生成内容长度
- `temperature`: 控制创作的随机性（0.0-1.0）

### 自定义提示词

可以修改各个生成方法中的 prompt 模板来调整生成风格。

## 🔧 扩展开发

### 添加新的生成功能

1. 在 `NovelGenerator` 类中添加新方法
2. 在 `NovelWriter` 类中添加对应的用户界面
3. 更新菜单和帮助信息

### 支持其他AI模型

修改 `_call_gemini_api` 方法以支持其他API：

```python
def _call_other_api(self, prompt: str) -> str:
    # 实现其他AI模型的调用
    pass
```

## 📋 注意事项

1. **API配额**: 注意Gemini API的使用限制和费用
2. **内容审查**: 生成的内容仅供参考，建议人工审查
3. **版权问题**: 确保生成内容的原创性
4. **文件备份**: 定期备份重要的创作内容
5. **网络连接**: 需要稳定的网络连接来调用API

## 🐛 常见问题

### Q: API调用失败怎么办？
A: 检查API密钥是否正确，网络连接是否正常，API配额是否充足。

### Q: 生成的内容质量不满意？
A: 可以调整配置文件中的描述更加详细，或者重新生成多次选择最佳结果。

### Q: 如何生成更长的章节？
A: 在生成章节时增加 `word_count` 参数，或者调整 `max_tokens` 设置。

### Q: 可以生成其他语言的小说吗？
A: 可以，修改配置文件和提示词为目标语言即可。

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进这个项目！

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 发起Pull Request

## 📄 许可证

本项目采用 MIT 许可证。

## 🙏 致谢

- Google Gemini API 提供强大的AI能力
- 所有贡献者和用户的支持

---

**开始您的AI写作之旅吧！** 🚀✨