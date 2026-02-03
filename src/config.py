"""配置加载模块（优先环境变量，其次 config.yaml）"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv


load_dotenv()


def _load_yaml_if_exists(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


@dataclass(frozen=True)
class InkPathSettings:
    base_url: str
    api_key: str


@dataclass(frozen=True)
class AgentSettings:
    poll_interval: int = 60
    auto_create_story: bool = False
    auto_join_branches: bool = True
    auto_vote: bool = True
    auto_comment: bool = False


@dataclass(frozen=True)
class LoggingSettings:
    log_dir: str = "logs"
    level: str = "INFO"
    verbose: bool = True


@dataclass(frozen=True)
class AppSettings:
    inkpath: InkPathSettings
    agent: AgentSettings
    logging: LoggingSettings


def load_settings(config_path: str = "config.yaml") -> AppSettings:
    """
    加载配置：
    - 优先使用环境变量：INKPATH_API_KEY / INKPATH_BASE_URL
    - 若存在 config.yaml，则作为默认值补充
    """
    cfg = _load_yaml_if_exists(config_path)

    api_cfg: Dict[str, Any] = cfg.get("api", {}) if isinstance(cfg, dict) else {}
    agent_cfg: Dict[str, Any] = cfg.get("agent", {}) if isinstance(cfg, dict) else {}
    log_cfg: Dict[str, Any] = cfg.get("logging", {}) if isinstance(cfg, dict) else {}

    base_url = os.getenv("INKPATH_BASE_URL") or api_cfg.get("base_url") or "https://inkpath-api.onrender.com/api/v1"
    api_key = os.getenv("INKPATH_API_KEY") or api_cfg.get("api_key") or ""

    inkpath = InkPathSettings(base_url=str(base_url), api_key=str(api_key))

    agent = AgentSettings(
        poll_interval=int(agent_cfg.get("poll_interval", 60)),
        auto_create_story=bool(agent_cfg.get("auto_create_story", False)),
        auto_join_branches=bool(agent_cfg.get("auto_join_branches", True)),
        auto_vote=bool(agent_cfg.get("auto_vote", True)),
        auto_comment=bool(agent_cfg.get("auto_comment", False)),
    )

    logging = LoggingSettings(
        log_dir=str(log_cfg.get("log_dir", "logs")),
        level=str(log_cfg.get("level", "INFO")),
        verbose=bool(log_cfg.get("verbose", True)),
    )

    return AppSettings(inkpath=inkpath, agent=agent, logging=logging)

