"""
morePersonLikePlugin 的设置文件
包含插件的所有默认配置
"""

# 备用回复，以防LLM调用失败
FALLBACK_RESPONSES = [
    "哼！不要随便戳我啦，人家会生气的！",
    "啊呜~被戳到了，好痒呀！请不要再戳啦~",
    "再戳我的话，我就...我就生气了！",
    "主人~不要老是戳我嘛，人家会害羞的~",
    "呜呜，被戳到敏感部位了啦>//<",
    "喵呜~ 被戳的感觉好奇怪呀"
]

# 戳一戳功能默认配置
DEFAULT_POKE_CONFIG = {
    "is_enable": False,
    "poke_prompt": "请以可爱的语气，生成一句被人戳了的拒绝回应，表现出些许娇嗔或不满，但整体保持可爱风格。",
    "pokeback_probability": 0.2,
    "pokeback_prompt": "请以可爱的语气，生成一句主动戳别人的回应，表现出顽皮或调皮的态度，但整体保持可爱风格。"
}

# 主动消息功能默认配置
DEFAULT_ACTIVE_MESSAGE_CONFIG = {
    "is_enable": False,
    "active_message_prompt": "长时间没有人搭理你，因此请你以可爱的语气，生成一条消息寻求大家陪你聊天或玩耍，表现出些许娇嗔或不满，但整体保持可爱风格。",
    "time_interval": 3600
}

# QQ表情替换功能配置
DEFAULT_QQ_EMOJI_CONFIG = {
    "is_enable": True
    }

def load_config(config):
    """
    从AstrBotConfig加载配置，并合并默认配置
    """
    result = {}
    
    # 获取戳一戳配置
    poke_config = config.get("on_poke", {})
    result["poke_config"] = {
        "is_enable": poke_config.get("is_enable", DEFAULT_POKE_CONFIG["is_enable"]),
        "poke_prompt": poke_config.get("poke_prompt", DEFAULT_POKE_CONFIG["poke_prompt"]),
        "pokeback_probability": poke_config.get("pokeback_probability", DEFAULT_POKE_CONFIG["pokeback_probability"]),
        "pokeback_prompt": poke_config.get("pokeback_prompt", DEFAULT_POKE_CONFIG["pokeback_prompt"])
    }
    
    # 获取主动消息配置
    active_message_config = config.get("active_message", {})
    result["active_message_config"] = {
        "is_enable": active_message_config.get("is_enable", DEFAULT_ACTIVE_MESSAGE_CONFIG["is_enable"]),
        "active_message_prompt": active_message_config.get("active_message_prompt", DEFAULT_ACTIVE_MESSAGE_CONFIG["active_message_prompt"]),
        "time_interval": active_message_config.get("time_interval", DEFAULT_ACTIVE_MESSAGE_CONFIG["time_interval"])
    }
    
    # 获取QQ表情配置
    qq_emoji_config = config.get("qq_emoji", {})
    result["qq_emoji_config"] = {
        "is_enable": qq_emoji_config.get("is_enable", DEFAULT_QQ_EMOJI_CONFIG["is_enable"])
    }
    
    return result