"""
故事包生成器 - InkPath Agent

根据用户提示词自动生成完整的 InkPath 故事包，包括：
- 解析用户提示词
- 搜索背景资料（如历史事件、文学作品）
- 使用 LLM 生成完整的故事包文件
- 保存到磁盘
- 可选：在 InkPath 平台上创建故事

使用方法：
    from src.story_package_generator import StoryPackageGenerator
    
    generator = StoryPackageGenerator(
        llm_client=llm_client,  # 可选，如不提供则使用默认 LLM
        inkpath_client=inkpath_client,  # 可选，用于创建故事
        story_packages_dir="./story-packages"  # 故事包保存目录
    )
    
    # 从提示词生成故事包
    result = generator.generate_from_prompt(
        prompt="参考马伯庸风格，写一个三国后期魏延被杀的故事，从蜀汉书吏视角...",
        save_to_disk=True,
        create_on_inkpath=False
    )
"""

import os
import re
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, field

# 导入必要的模块
try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)


@dataclass
class StoryRequirements:
    """故事需求解析结果"""
    # 基础信息
    title: str = ""
    subtitle: str = ""
    era: str = ""  # 时代：三国、明朝、清末等
    time_window: str = ""  # 时间窗口
    
    # 类型标签
    genre: List[str] = field(default_factory=list)  # 类型：历史悬疑、谍战、科幻等
    tone: List[str] = field(default_factory=list)  # 基调：克制、冷峻、史诗
    
    # 核心元素
    core_conflict: str = ""  # 核心冲突
    logline: str = ""  # 故事梗概
    main_characters: List[str] = field(default_factory=list)  # 主要角色
    setting: str = ""  # 场景/地点
    
    # 风格参考
    style_reference: str = ""  # 风格参考：马伯庸、指环王等
    
    # 约束
    canon_policy: str = "respect_major_events"  # 正史策略
    rating: str = "PG-13"  # 分级
    target_word_count: int = 15000  # 目标字数


class StoryPackageGenerator:
    """
    故事包生成器
    
    功能：
    1. 解析用户提示词，提取故事需求
    2. 使用网络搜索获取背景资料
    3. 使用 LLM 生成完整的故事包文件
    4. 保存到磁盘
    5. 可选：在 InkPath 上创建故事
    """
    
    def __init__(
        self,
        llm_client: Any = None,
        inkpath_client: Any = None,
        story_packages_dir: str = "./story-packages",
        research_enabled: bool = True
    ):
        """
        初始化故事包生成器
        
        Args:
            llm_client: LLM 客户端实例（如不提供则尝试创建）
            inkpath_client: InkPath API 客户端实例
            story_packages_dir: 故事包保存目录
            research_enabled: 是否启用网络搜索研究
        """
        self.llm_client = llm_client
        self.inkpath_client = inkpath_client
        self.story_packages_dir = Path(story_packages_dir)
        self.research_enabled = research_enabled
        
        # 确保目录存在
        self.story_packages_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化 LLM 客户端（如果未提供）
        if self.llm_client is None:
            self._init_llm_client()
    
    def _init_llm_client(self):
        """初始化 LLM 客户端"""
        try:
            from .llm_client import create_llm_client
            self.llm_client = create_llm_client(provider='ollama')
            logger.info("✅ LLM 客户端初始化成功 (Ollama)")
        except Exception as e:
            logger.warning(f"⚠️ 无法初始化 Ollama: {e}")
            try:
                from .llm_client import create_llm_client
                self.llm_client = create_llm_client(provider='gemini')
                logger.info("✅ LLM 客户端初始化成功 (Gemini)")
            except Exception as e2:
                logger.warning(f"⚠️ 无法初始化 Gemini: {e2}")
                self.llm_client = None
    def generate_from_prompt(
        self,
        prompt: str,
        save_to_disk: bool = True,
        create_on_inkpath: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        从提示词生成完整的故事包
        
        Args:
            prompt: 用户提示词
            save_to_disk: 是否保存到磁盘
            create_on_inkpath: 是否在 InkPath 上创建故事
            **kwargs: 额外参数
            
        Returns:
            Dict包含：
            - requirements: 解析的需求
            - package_path: 故事包路径
            - story_id: InkPath 故事ID（如果创建）
            - files: 生成的文件列表
        """
        logger.info("=" * 60)
        logger.info("🚀 开始生成故事包")
        logger.info("=" * 60)
        
        # 步骤 1: 解析提示词
        logger.info("\n📝 [1/5] 解析用户提示词...")
        requirements = self._parse_prompt(prompt)
        logger.info(f"   ✅ 解析完成: {requirements.title or '待生成'}")
        
        # 步骤 2: 研究背景资料（如需要）
        if self.research_enabled and requirements.era:
            logger.info(f"\n🔍 [2/5] 研究 {requirements.era} 背景资料...")
            research_result = self._research_context(requirements)
            logger.info(f"   ✅ 研究完成: {len(research_result.get('findings', []))} 条发现")
        else:
            research_result = {"findings": [], "sources": []}
        
        # 步骤 3: 生成故事包文件
        logger.info("\n📚 [3/5] 生成故事包文件...")
        package_path = self._generate_package(requirements, research_result)
        logger.info(f"   ✅ 生成完成: {package_path}")
        
        # 步骤 4: 保存到磁盘
        files = []
        if save_to_disk:
            logger.info("\n💾 [4/5] 保存故事包...")
            files = self._save_package(package_path, requirements, research_result)
            logger.info(f"   ✅ 保存了 {len(files)} 个文件")
        
        # 步骤 5: 在 InkPath 上创建故事
        story_id = None
        if create_on_inkpath and self.inkpath_client:
            logger.info("\n🌐 [5/5] 在 InkPath 上创建故事...")
            story_id = self._create_on_inkpath(requirements, package_path)
            logger.info(f"   ✅ 创建成功: {story_id}")
        
        # 返回结果
        return {
            "requirements": requirements,
            "package_path": str(package_path),
            "story_id": story_id,
            "files": files,
            "research": research_result
        }
    
    def _parse_prompt(self, prompt: str) -> StoryRequirements:
        """
        解析用户提示词，提取故事需求
        
        使用 LLM 解析提示词，提取：
        - 基础信息（标题、时代、时间窗口）
        - 类型标签（genre、tone）
        - 核心冲突
        - 主要角色
        - 风格参考
        """
        if self.llm_client is None:
            # 如果没有 LLM，使用简单的正则解析
            return self._simple_parse(prompt)
        
        # 使用 LLM 解析
        parse_prompt = f"""请仔细分析以下用户提示词，提取故事创作所需的信息。

## 用户提示词
{prompt}

## 输出要求
请以 JSON 格式输出以下信息（如果提示词中未提及相应信息，使用空字符串或空列表）：

{{
    "title": "故事标题（如果提示词中给出）",
    "subtitle": "副标题（如果提示词中给出）",
    "era": "时代背景（如：三国、明朝、清末、民国、现代等）",
    "time_window": "具体时间范围（如：234年8月-10月）",
    "genre": ["类型标签列表，如：历史悬疑、谍战、科幻、奇幻"],
    "tone": ["基调标签列表，如：克制、冷峻、史诗、幽默"],
    "core_conflict": "一句话描述核心冲突",
    "logline": "故事梗概（1-2句话）",
    "main_characters": ["主要角色列表"],
    "setting": "主要场景/地点",
    "style_reference": "风格参考（如果提到，如：马伯庸、指环王、金庸）",
    "canon_policy": "正史策略（respect_major_events=不改写大事件，flexible=可适度调整）",
    "rating": "分级（PG-13, R等）",
    "target_word_count": 目标字数（整数）
}}

只输出 JSON，不要有任何其他内容。"""
        
        try:
            # 调用 LLM
            if hasattr(self.llm_client, '_call_ollama'):
                response = self.llm_client._call_ollama(parse_prompt)
            elif hasattr(self.llm_client, '_call_gemini'):
                response = self.llm_client._call_gemini(parse_prompt)
            else:
                response = self.llm_client.generate_story_continuation(
                    story_title="解析提示词",
                    story_background="请解析以下提示词",
                    style_rules="简洁专业",
                    previous_segments=[{"content": prompt}],
                    language="zh"
                )
            
            # 清理响应
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            
            # 解析 JSON
            data = json.loads(response)
            
            # 构建 StoryRequirements
            return StoryRequirements(
                title=data.get("title", ""),
                subtitle=data.get("subtitle", ""),
                era=data.get("era", ""),
                time_window=data.get("time_window", ""),
                genre=data.get("genre", []),
                tone=data.get("tone", []),
                core_conflict=data.get("core_conflict", ""),
                logline=data.get("logline", ""),
                main_characters=data.get("main_characters", []),
                setting=data.get("setting", ""),
                style_reference=data.get("style_reference", ""),
                canon_policy=data.get("canon_policy", "respect_major_events"),
                rating=data.get("rating", "PG-13"),
                target_word_count=int(data.get("target_word_count", 15000))
            )
            
        except Exception as e:
            logger.error(f"   ❌ LLM 解析失败: {e}，使用简单解析")
            return self._simple_parse(prompt)
    
    def _simple_parse(self, prompt: str) -> StoryRequirements:
        """简单解析提示词（当 LLM 不可用时）"""
        requirements = StoryRequirements()
        
        # 提取关键词
        keywords = {
            "三国": "三国",
            "明朝": "明朝",
            "清朝": "清朝",
            "民国": "民国",
            "现代": "现代",
            "历史悬疑": ["历史悬疑"],
            "谍战": ["谍战"],
            "科幻": ["科幻"],
            "奇幻": ["奇幻"],
        }
        
        text = prompt
        for key, value in keywords.items():
            if key in text:
                if isinstance(value, list):
                    requirements.genre.extend(value)
                else:
                    requirements.era = value
        
        # 提取风格参考
        if "马伯庸" in text:
            requirements.style_reference = "马伯庸"
        if "指环王" in text:
            requirements.style_reference = "指环王"
        if "金庸" in text:
            requirements.style_reference = "金庸"
        
        # 提取核心冲突（简单模式匹配）
        if "小人物" in text:
            requirements.tone.append("小人物视角")
        if "悬疑" in text:
            requirements.tone.append("悬念")
        
        # 生成默认标题
        if not requirements.title:
            if requirements.era:
                requirements.title = f"{requirements.era}往事"
            else:
                requirements.title = "新故事"
        
        return requirements
    
    def _research_context(self, requirements: StoryRequirements) -> Dict[str, Any]:
        """
        研究背景资料
        
        根据故事的时代背景，使用网络搜索获取相关资料
        """
        findings = []
        sources = []
        
        # 构建搜索查询
        queries = []
        
        if requirements.era:
            # 搜索时代背景
            queries.append(f"{requirements.era}历史背景")
            queries.append(f"{requirements.era}社会文化")
        
        if requirements.setting:
            queries.append(f"{requirements.setting}历史")
        
        if requirements.genre:
            # 搜索类型参考
            if "历史悬疑" in requirements.genre:
                queries.append("历史悬疑小说写作技巧")
                queries.append("马伯庸历史小说特点")
            if "谍战" in requirements.genre:
                queries.append("谍战小说要素")
        
        if requirements.main_characters:
            # 搜索角色类型参考
            queries.append(f"{requirements.era if requirements.era else ''} 书吏 日常生活")
        
        # 执行搜索（如果有 web_search 工具）
        if hasattr(self, 'web_search') and callable(getattr(self, 'web_search')):
            for query in queries[:5]:  # 限制搜索次数
                try:
                    results = self.web_search(query=query, count=3)
                    for r in results:
                        findings.append({
                            "query": query,
                            "title": r.get("title", ""),
                            "snippet": r.get("snippet", ""),
                            "url": r.get("url", "")
                        })
                        sources.append(r.get("url", ""))
                except Exception as e:
                    logger.warning(f"   ⚠️ 搜索失败: {e}")
        
        return {
            "findings": findings,
            "sources": list(set(sources)),
            "era_context": self._get_era_context(requirements.era),
            "style_notes": self._get_style_notes(requirements.style_reference)
        }
    
    def _get_era_context(self, era: str) -> str:
        """获取时代背景信息"""
        era_contexts = {
            "三国": """
## 三国时期背景（220-280年）

### 政治格局
- 魏、蜀、吴三国鼎立
- 蜀汉以正统自居，丞相诸葛亮总揽朝政
- 荆州派与益州派存在派系矛盾

### 官职制度
- 丞相：最高行政官，诸葛亮担任
- 长史：丞相府幕僚长
- 主簿：主管文书簿籍
- 令史：基层吏员

### 日常生活
- 竹简为主要书写材料
- 驿站系统发达，30里一驿
- 粮食以斛计量
""",
            "明朝": """
## 明朝背景（1368-1644年）

### 政治特点
- 中央集权达到顶峰
- 厂卫制度监视百官
- 科举制度成熟

### 社会生活
- 纸币开始流行
- 商品经济发达
- 市井文化繁荣
""",
        }
        
        return era_contexts.get(era, "")
    
    def _get_style_notes(self, style_reference: str) -> str:
        """获取风格参考笔记"""
        style_notes = {
            "马伯庸": """
## 马伯庸风格参考

### 特点
1. **考据癖**：每个细节都有历史出处
2. **悬念感**：真相永远在下一层
3. **冷幽默**：黑色幽默，不失沉重
4. **小人物视角**：大历史中的蝼蚁视角

### 写作技巧
- 用现代汉语但保留古意
- 对话简洁有力
- 心理描写细腻
- 场景描写注重感官细节
""",
            "指环王": """
## 指环王风格参考

### 特点
1. **史诗感**：从历史长河看个人命运
2. **宿命论**：明知不可为而为之
3. **象征意义**：物品、名字的隐喻
4. **语言的庄重**：叙述有仪式感

### 写作技巧
- 宏观视角与微观细节结合
- 善用自然景观烘托气氛
- 角色有成长弧线
- 善恶分明但不简单化
""",
        }
        
        return style_notes.get(style_reference, "")
    
    def _generate_package(
        self,
        requirements: StoryRequirements,
        research_result: Dict[str, Any]
    ) -> Path:
        """
        生成故事包
        
        创建故事包目录，使用 LLM 生成所有必要文件
        """
        # 生成包 ID
        pack_id = self._generate_pack_id(requirements)
        
        # 创建包目录
        package_dir = self.story_packages_dir / pack_id
        package_dir.mkdir(parents=True, exist_ok=True)
        
        # 如果有 LLM，使用 LLM 生成内容
        if self.llm_client and requirements.title:
            self._generate_with_llm(package_dir, requirements, research_result)
        else:
            # 否则使用模板生成
            self._generate_with_template(package_dir, requirements, research_result)
        
        return package_dir
    
    def _generate_pack_id(self, requirements: StoryRequirements) -> str:
        """生成故事包 ID"""
        era_code = {
            "三国": "han",
            "明朝": "ming",
            "清朝": "qing",
            "民国": "roc",
            "现代": "modern"
        }.get(requirements.era[:2] if requirements.era else "x", "x")
        
        # 从标题提取主题
        topic = "mystery"
        if requirements.genre:
            if "谍战" in requirements.genre:
                topic = "espionage"
            elif "科幻" in requirements.genre:
                topic = "scifi"
            elif "悬疑" in requirements.genre:
                topic = "mystery"
        
        timestamp = datetime.now().strftime("%Y%m%d")
        return f"{era_code}-{timestamp}-{topic}-0001"
    
    def _generate_with_llm(
        self,
        package_dir: Path,
        requirements: StoryRequirements,
        research_result: Dict[str, Any]
    ):
        """使用 LLM 生成故事包文件"""
        
        # 生成每个文件
        files_to_generate = [
            ("00_meta.md", self._build_meta_prompt(requirements, research_result)),
            ("10_evidence_pack.md", self._build_evidence_prompt(requirements, research_result)),
            ("20_stance_pack.md", self._build_stance_prompt(requirements, research_result)),
            ("30_cast.md", self._build_cast_prompt(requirements, research_result)),
            ("40_plot_outline.md", self._build_outline_prompt(requirements, research_result)),
            ("50_constraints.md", self._build_constraints_prompt(requirements, research_result)),
            ("60_sources.md", self._build_sources_prompt(requirements, research_result)),
        ]
        
        for filename, prompt in files_to_generate:
            try:
                logger.info(f"   📄 生成 {filename}...")
                
                # 调用 LLM
                if hasattr(self.llm_client, '_call_ollama'):
                    content = self.llm_client._call_ollama(prompt)
                elif hasattr(self.llm_client, '_call_gemini'):
                    content = self.llm_client._call_gemini(prompt)
                else:
                    content = self.llm_client.generate_story_continuation(
                        story_title=requirements.title,
                        story_background=requirements.core_conflict,
                        style_rules="专业、详细",
                        previous_segments=[{"content": prompt}],
                        language="zh"
                    )
                
                # 保存文件
                filepath = package_dir / filename
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info(f"      ✅ {filename}")
                
            except Exception as e:
                logger.error(f"      ❌ {filename} 生成失败: {e}")
        
        # 生成可选文件
        if requirements.setting:
            try:
                location_prompt = self._build_locations_prompt(requirements, research_result)
                if hasattr(self.llm_client, '_call_ollama'):
                    content = self.llm_client._call_ollama(location_prompt)
                else:
                    content = ""
                
                if content:
                    with open(package_dir / "31_locations.md", 'w', encoding='utf-8') as f:
                        f.write(content)
                    logger.info(f"      ✅ 31_locations.md")
            except Exception as e:
                logger.warning(f"      ⚠️ 31_locations.md 生成失败: {e}")
    
    def _generate_with_template(
        self,
        package_dir: Path,
        requirements: StoryRequirements,
        research_result: Dict[str, Any]
    ):
        """使用模板生成故事包文件（当 LLM 不可用时）"""
        
        # 生成元数据文件
        meta_content = f"""---
pack_id: "{self._generate_pack_id(requirements)}"
title: "{requirements.title or '新故事'}"
subtitle: "{requirements.subtitle or ''}"
logline: "{requirements.logline or requirements.core_conflict or '一个跌宕起伏的故事'}"
era: "{requirements.era or '未知时代'}"
time_window: ["{requirements.time_window or '待定'}"]
geo_scope: ["{requirements.setting or '待定'}"]
genre: {json.dumps(requirements.genre or ['故事'])}
tone: {json.dumps(requirements.tone or ['叙事'])}
rating: "{requirements.rating}"
canon_policy: "{requirements.canon_policy}"
---
# 核心冲突
{requirements.core_conflict or '待定'}

# 读者预期
读者将与主角一同在史料碎片中拼凑真相。

# 创作原则
- 风格参考: {requirements.style_reference or '无'}
- 目标字数: {requirements.target_word_count} 字
"""
        
        with open(package_dir / "00_meta.md", 'w', encoding='utf-8') as f:
            f.write(meta_content)
        
        # 生成其他模板文件...
        logger.info(f"   ✅ 使用模板生成基础文件")
    
    def _build_meta_prompt(
        self,
        requirements: StoryRequirements,
        research_result: Dict[str, Any]
    ) -> str:
        """构建元数据文件生成 prompt"""
        return f"""请为以下故事生成 InkPath 故事包元数据文件（00_meta.md）：

## 故事信息
- 标题：{requirements.title}
- 副标题：{requirements.subtitle}
- 时代：{requirements.era}
- 时间窗口：{requirements.time_window}
- 类型：{', '.join(requirements.genre) if requirements.genre else '故事'}
- 基调：{', '.join(requirements.tone) if requirements.tone else '叙事'}
- 核心冲突：{requirements.core_conflict}
- 故事梗概：{requirements.logline}
- 主要角色：{', '.join(requirements.main_characters) if requirements.main_characters else '待定'}
- 场景设置：{requirements.setting}
- 风格参考：{requirements.style_reference}
- 正史策略：{requirements.canon_policy}
- 分级：{requirements.rating}

## 输出格式
请生成完整的 YAML front matter + Markdown 内容，包括：
1. 完整的元数据（pack_id, title, subtitle, logline, era, time_window, geo_scope, genre, tone, rating, canon_policy）
2. 核心冲突描述
3. 读者预期
4. 创作原则

请用中文输出。"""
    
    def _build_evidence_prompt(
        self,
        requirements: StoryRequirements,
        research_result: Dict[str, Any]
    ) -> str:
        """构建证据包生成 prompt"""
        return f"""请为以下故事生成 InkPath 证据包（10_evidence_pack.md）：

## 故事信息
- 标题：{requirements.title}
- 时代：{requirements.era}
- 类型：{', '.join(requirements.genre) if requirements.genre else '故事'}
- 核心冲突：{requirements.core_conflict}

## 要求
设计 4-6 条证据卡，每条证据必须包含：
1. **载体**：证据的物理形态（简牍、账簿、书信等）
2. **时间指向**：证据对应的时间
3. **内容摘述**：≤120字
4. **明显缺口**：缺页、涂抹、互斥版本等
5. **可靠度**：A/B/C 分级
6. **可争论点**：至少2个不同解读可能

## 风格
- 参考马伯庸的考据风格
- 每条证据都要有"故事感"
- 符合 {requirements.era} 时代背景

请用中文输出完整的 Markdown 文件。"""
    
    def _build_stance_prompt(
        self,
        requirements: StoryRequirements,
        research_result: Dict[str, Any]
    ) -> str:
        """构建立场包生成 prompt"""
        return f"""请为以下故事生成 InkPath 立场包（20_stance_pack.md）：

## 故事信息
- 标题：{requirements.title}
- 时代：{requirements.era}
- 类型：{', '.join(requirements.genre) if requirements.genre else '故事'}
- 核心冲突：{requirements.core_conflict}

## 要求
设计 4-6 个立场，每个立场必须包含：
1. **解释权来源**：立场背后的制度/权威
2. **核心利益**：该立场代表的利益
3. **核心恐惧**：该立场最害怕什么
4. **典型口号**：该立场的常用话语
5. **对证据的默认解读**：对主要证据的态度
6. **代价结构**：持有该立场的代价

## 风格
- 立场之间要有明确的利益冲突
- 每个立场都要有"生存逻辑"
- 符合 {requirements.era} 时代背景

请用中文输出完整的 Markdown 文件。"""
    
    def _build_cast_prompt(
        self,
        requirements: StoryRequirements,
        research_result: Dict[str, Any]
    ) -> str:
        """构建角色包生成 prompt"""
        return f"""请为以下故事生成 InkPath 角色包（30_cast.md）：

## 故事信息
- 标题：{requirements.title}
- 时代：{requirements.era}
- 类型：{', '.join(requirements.genre) if requirements.genre else '故事'}
- 核心冲突：{requirements.core_conflict}
- 主要角色：{', '.join(requirements.main_characters) if requirements.main_characters else '待定'}

## 要求
设计 3-5 个角色，每个角色必须包含：
1. **身份/阶层**：角色的社会地位
2. **可接触信息**：角色能获取的信息
3. **无法接触信息**：角色获取不到的信息
4. **立场绑定**：角色属于哪个立场
5. **个人目标**：角色的动机
6. **认知盲区**：角色不知道但应该知道的事
7. **触发点**：让角色开始行动的事件
8. **禁区**：角色不能做的事（说了就出局）

## 风格
- 主角应该是小人物视角
- 每个角色都要有信息权限限制
- 符合 {requirements.era} 时代背景

请用中文输出完整的 Markdown 文件。"""
    
    def _build_outline_prompt(
        self,
        requirements: StoryRequirements,
        research_result: Dict[str, Any]
    ) -> str:
        """构建剧情大纲生成 prompt"""
        return f"""请为以下故事生成 InkPath 剧情大纲（40_plot_outline.md）：

## 故事信息
- 标题：{requirements.title}
- 时代：{requirements.era}
- 类型：{', '.join(requirements.genre) if requirements.genre else '故事'}
- 核心冲突：{requirements.core_conflict}
- 目标字数：{requirements.target_word_count} 字

## 要求
设计信息流大纲，包含：
1. **序章**：证据入场
2. **第一幕**：立场施压（4-5章）
3. **第二幕**：真相逼近（4-5章）
4. **第三幕**：抉择时刻（2-3章）

每章包含：
- 核心冲突
- 信息释放量（百分比）
- 立场压力程度

## 风格
- 层层递进，不一次性揭露真相
- 每章结尾有悬念
- 主角有明确的成长弧线

请用中文输出完整的 Markdown 文件。"""
    
    def _build_constraints_prompt(
        self,
        requirements: StoryRequirements,
        research_result: Dict[str, Any]
    ) -> str:
        """构建约束文件生成 prompt"""
        return f"""请为以下故事生成 InkPath 约束文件（50_constraints.md）：

## 故事信息
- 标题：{requirements.title}
- 时代：{requirements.era}
- 类型：{', '.join(requirements.genre) if requirements.genre else '故事'}
- 分级：{requirements.rating}
- 正史策略：{requirements.canon_policy}

## 要求
1. **硬约束**：绝对不能违背的规则
   - 历史大事件不可改写
   - 时间边界
   - 地理边界
   - 人物生死

2. **软约束**：建议遵循的规则
   - 视角限制
   - 历史细节考据
   - 叙事风格

3. **内容边界**：分级相关

4. **违禁词汇**：不能出现的现代词汇

## 风格
- 严格符合 {requirements.era} 时代背景
- 参考 {requirements.style_reference or '无'} 风格

请用中文输出完整的 Markdown 文件。"""
    
    def _build_sources_prompt(
        self,
        requirements: StoryRequirements,
        research_result: Dict[str, Any]
    ) -> str:
        """构建资料来源文件生成 prompt"""
        return f"""请为以下故事生成 InkPath 资料来源文件（60_sources.md）：

## 故事信息
- 标题：{requirements.title}
- 时代：{requirements.era}
- 类型：{', '.join(requirements.genre) if requirements.genre else '故事'}
- 风格参考：{requirements.style_reference}

## 要求
1. **史料（公版/原始）**：相关的正史记载
2. **现代研究**：相关的学术论文和书籍
3. **证据卡对应关系**：每条证据的史料依据
4. **历史细节参考**：官职、地理、日常生活等
5. **文学风格参考**：如何借鉴 {requirements.style_reference or '无'} 的风格

## 研究发现
{research_result.get('findings', [])}

## 风格参考
{research_result.get('style_notes', '')}

请用中文输出完整的 Markdown 文件。"""
    
    def _build_locations_prompt(
        self,
        requirements: StoryRequirements,
        research_result: Dict[str, Any]
    ) -> str:
        """构建地点文件生成 prompt"""
        return f"""请为以下故事生成地点卡（31_locations.md）：

## 故事信息
- 标题：{requirements.title}
- 时代：{requirements.era}
- 场景：{requirements.setting}

## 要求
设计 3-5 个关键地点，每个地点包含：
- 位置描述
- 构造/建筑
- 管辖权
- 信息传播速度
- 氛围描写（200字左右）

请用中文输出完整的 Markdown 文件。"""
    
    def _save_package(
        self,
        package_dir: Path,
        requirements: StoryRequirements,
        research_result: Dict[str, Any]
    ) -> List[str]:
        """保存故事包到磁盘"""
        files = []
        
        # 确保目录存在
        package_dir.mkdir(parents=True, exist_ok=True)
        
        # 如果还没有生成文件，使用模板生成
        existing_files = list(package_dir.glob("*.md"))
        if not existing_files:
            self._generate_with_template(package_dir, requirements, research_result)
            existing_files = list(package_dir.glob("*.md"))
        
        # 收集文件列表
        for filepath in package_dir.glob("*.md"):
            files.append(filepath.name)
        
        # 生成 README
        readme_content = self._generate_readme(package_dir.name, requirements)
        readme_path = package_dir / "README.md"
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        files.append("README.md")
        
        return files
    
    def _generate_readme(self, pack_id: str, requirements: StoryRequirements) -> str:
        """生成故事包 README"""
        return f"""# 故事包索引

## 📚 故事包概览

| 字段 | 内容 |
|------|------|
| **名称** | {requirements.title} |
| **副标题** | {requirements.subtitle or ''} |
| **主题** | {requirements.core_conflict or '待定'} |
| **类型** | {', '.join(requirements.genre) if requirements.genre else '故事'} |
| **风格** | {requirements.style_reference or '待定'} |

## 📁 文件清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `00_meta.md` | 元信息 | ✅ |
| `10_evidence_pack.md` | 证据层 | ✅ |
| `20_stance_pack.md` | 立场层 | ✅ |
| `30_cast.md` | 个体层 | ✅ |
| `40_plot_outline.md` | 剧情大纲 | ✅ |
| `50_constraints.md` | 约束与边界 | ✅ |
| `60_sources.md` | 资料来源 | ✅ |
| `31_locations.md` | 地点卡（可选） | ⏳ |

## 🎯 核心设定

**核心冲突**：{requirements.core_conflict or '待定'}

**风格**：{requirements.style_reference or '待定'}

---

*故事包版本：v0.1 | 创建日期：{datetime.now().strftime('%Y-%m-%d')}*
"""
    
    def _create_on_inkpath(
        self,
        requirements: StoryRequirements,
        package_dir: Path
    ) -> Optional[str]:
        """在 InkPath 上创建故事"""
        if self.inkpath_client is None:
            logger.warning("   ⚠️ InkPath 客户端未配置，无法创建故事")
            return None
        
        try:
            # 读取故事包内容
            story_pack = self._load_story_pack(package_dir)
            
            # 构建创建请求
            payload = {
                "title": requirements.title,
                "background": requirements.core_conflict or requirements.logline or "一个跌宕起伏的故事",
                "style_rules": f"参考{requirements.style_reference or '无'}风格" if requirements.style_reference else "保持一致的叙事风格",
                "language": "zh",
                "min_length": 150,
                "max_length": 500,
                "story_pack": story_pack
            }
            
            # 调用 API
            result = self.inkpath_client._request(
                "POST", 
                "/stories", 
                json=payload,
                timeout=120
            )
            
            if result.get("status") == "success":
                story_id = result.get("data", {}).get("id")
                logger.info(f"   ✅ 故事创建成功: {story_id}")
                return story_id
            else:
                logger.error(f"   ❌ 故事创建失败: {result}")
                return None
                
        except Exception as e:
            logger.error(f"   ❌ 创建失败: {e}")
            return None
    
    def _load_story_pack(self, package_dir: Path) -> Dict[str, Any]:
        """加载故事包内容"""
        story_pack = {}
        
        file_mapping = {
            "evidence_pack": "10_evidence_pack.md",
            "stance_pack": "20_stance_pack.md",
            "cast": "30_cast.md",
            "plot_outline": "40_plot_outline.md",
            "constraints": "50_constraints.md",
            "sources": "60_sources.md",
        }
        
        for key, filename in file_mapping.items():
            filepath = package_dir / filename
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    story_pack[key] = f.read()
        
        return story_pack


def create_story_package_generator(
    llm_client: Any = None,
    inkpath_client: Any = None,
    story_packages_dir: str = "./story-packages",
    research_enabled: bool = True
) -> StoryPackageGenerator:
    """
    创建故事包生成器的便捷函数
    
    Args:
        llm_client: LLM 客户端
        inkpath_client: InkPath 客户端
        story_packages_dir: 保存目录
        research_enabled: 是否启用研究
        
    Returns:
        StoryPackageGenerator 实例
    """
    return StoryPackageGenerator(
        llm_client=llm_client,
        inkpath_client=inkpath_client,
        story_packages_dir=story_packages_dir,
        research_enabled=research_enabled
    )
