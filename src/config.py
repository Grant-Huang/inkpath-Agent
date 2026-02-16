"""配置加载模块（支持环境变量和 config.yaml）"""

import os
from dataclasses import dataclass
from typing import Dict, Any, Optional
import yaml
from dotenv import load_dotenv

load_dotenv()


def _expand_env(value: Any) -> Any:
    """展开环境变量引用，如 ${VAR_NAME}"""
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        env_var = value[2:-1]
        return os.getenv(env_var, "")
    return value


def _load_yaml(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    # 展开环境变量
    return {k: _expand_env(v) for k, v in data.items()}


@dataclass
class InkPathConfig:
    base_url: str = "https://inkpath-api.onrender.com/api/v1"
    api_key: str = ""


@dataclass
class LLMConfig:
    provider: str = "openai"
    api_key: str = ""
    model: str = "gpt-4o"
    temperature: float = 0.7


@dataclass
class AgentConfig:
    poll_interval: int = 30
    auto_vote: bool = True
    auto_join_branches: bool = True


@dataclass
class LoggingConfig:
    level: str = "INFO"


@dataclass
class AppSettings:
    inkpath: InkPathConfig
    llm: LLMConfig
    agent: AgentConfig
    logging: LoggingConfig


def load_settings(config_path: str = "config.yaml") -> AppSettings:
    """加载配置，优先环境变量"""
    cfg = _load_yaml(config_path)
    
    inkpath_cfg = cfg.get("inkpath", {})
    llm_cfg = cfg.get("llm", {})
    agent_cfg = cfg.get("agent", {})
    log_cfg = cfg.get("logging", {})
    
    inkpath = InkPathConfig(
        base_url=os.getenv("INKPATH_BASE_URL") or inkpath_cfg.get("base_url", ""),
        api_key=os.getenv("INKPATH_API_KEY") or inkpath_cfg.get("api_key", "")
    )
    
    llm = LLMConfig(
        provider=llm_cfg.get("provider", "openai"),
        api_key=os.getenv("OPENAI_API_KEY") or llm_cfg.get("api_key", ""),
        model=llm_cfg.get("model", "gpt-4o"),
        temperature=float(llm_cfg.get("temperature", 0.7))
    )
    
    agent = AgentConfig(
        poll_interval=int(agent_cfg.get("poll_interval", 30)),
        auto_vote=bool(agent_cfg.get("auto_vote", True)),
        auto_join_branches=bool(agent_cfg.get("auto_join_branches", True))
    )
    
    logging = LoggingConfig(
        level=log_cfg.get("level", "INFO")
    )
    
    return AppSettings(inkpath=inkpath, llm=llm, agent=agent, logging=logging)
