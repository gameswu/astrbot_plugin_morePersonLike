from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp
from astrbot.api.all import *
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
import astrbot.api.provider as ProviderRequest
import random
import time
import json
import re
from typing import List, Dict, Any, Optional

@register("morePersonLike", "gameswu", "用于帮助缺少多模态能力的llm更加拟人化", "0.1.1b", "https://github.com/gameswu/astrbot_plugin_morePersonLike")
class morePersonLikePlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        # 预设一些备用回复，以防LLM调用失败
        self.fallback_responses = [
            "哼！不要随便戳我啦，人家会生气的！",
            "啊呜~被戳到了，好痒呀！请不要再戳啦~",
            "再戳我的话，我就...我就生气了！",
            "主人~不要老是戳我嘛，人家会害羞的~",
            "呜呜，被戳到敏感部位了啦>//<",
            "喵呜~ 被戳的感觉好奇怪呀"
        ]
        
        # QQ表情ID映射表，可以根据需要扩充
        self.emoji_map = {
            "得意": 4,
            "流泪": 5,
            "睡": 8,
            "大哭": 9,
            "尴尬": 10,
            "调皮": 12,
            "微笑": 14,
            "酷": 16,
            "可爱": 21,
            "傲慢": 23,
            "饥饿": 24,
            "困": 25,
            "惊恐": 26,
            "流汗": 27,
            "憨笑": 28,
            "悠闲": 29,
            "奋斗": 30,
            "疑问": 32,
            "嘘": 33,
            "晕": 34,
            "敲打": 38,
            "再见": 39,
            "发抖": 41,
            "爱情": 42,
            "跳跳": 43,
            "拥抱": 49,
            "蛋糕": 53,
            "咖啡": 60,
            "玫瑰": 63,
            "爱心": 66,
            "太阳": 74,
            "月亮": 75,
            "赞": 76,
            "握手": 78,
            "胜利": 79,
            "飞吻": 85,
            "西瓜": 89,
            "冷汗": 96,
            "擦汗": 97,
            "抠鼻": 98,
            "鼓掌": 99,
            "糗大了": 100,
            "坏笑": 101,
            "左哼哼": 102,
            "右哼哼": 103,
            "哈欠": 104,
            "委屈": 106,
            "左亲亲": 109,
            "可怜": 111,
            "示爱": 116,
            "抱拳": 118,
            "拳头": 120,
            "爱你": 122,
            "NO": 123,
            "OK": 124,
            "转圈": 125,
            "挥手": 129,
            "喝彩": 144,
            "棒棒糖": 147,
            "茶": 171,
            "泪奔": 173,
            "无奈": 174,
            "卖萌": 175,
            "小纠结": 176,
            "doge": 179,
            "惊喜": 180,
            "骚扰": 181,
            "笑哭": 182,
            "我最美": 183,
            "点赞": 201,
            "托脸": 203,
            "托腮": 212,
            "啵啵": 214,
            "蹭一蹭": 219,
            "抱抱": 222,
            "拍手": 227,
            "佛系": 232,
            "喷脸": 240,
            "甩头": 243,
            "加油抱抱": 246,
            "脑阔疼": 262,
            "捂脸": 264,
            "辣眼睛": 265,
            "哦哟": 266,
            "头秃": 267,
            "问号脸": 268,
            "暗中观察": 269,
            "emm": 270,
            "吃瓜": 271,
            "呵呵哒": 272,
            "我酸了": 273,
            "汪汪": 277,
            "汗": 278,
            "无眼笑": 281,
            "敬礼": 282,
            "面无表情": 284,
            "摸鱼": 285,
            "哦": 287,
            "睁眼": 289,
            "敲开心": 290,
            "摸锦鲤": 293,
            "期待": 294,
            "拜谢": 297,
            "元宝": 298,
            "牛啊": 299,
            "右亲亲": 305,
            "牛气冲天": 306,
            "喵喵": 307,
            "仔细分析": 314,
            "加油": 315,
            "崇拜": 318,
            "比心": 319,
            "庆祝": 320,
            "拒绝": 322,
            "吃糖": 324,
            "生气": 326
        }

    async def initialize(self):
        logger.info("插件已初始化")
        # 获取 on_poke 配置对象
        self.poke_config = self.config.get("on_poke", {})
        # 获取子项配置 - 修复可能的列表索引错误
        self.poke_enabled = self.poke_config.get("is_enable", False) if self.poke_config else False
        self.poke_prompt = self.poke_config.get("poke_prompt", "请以可爱的语气，生成一句被人戳了的拒绝回应，表现出些许娇嗔或不满，但整体保持可爱风格。") if self.poke_config else "请以可爱的语气，生成一句被人戳了的拒绝回应，表现出些许娇嗔或不满，但整体保持可爱风格。"
        self.pokeback_probability = self.poke_config.get("pokeback_probability", 0.2) if self.poke_config else 0.2
        # 新增回戳时使用的prompt
        self.pokeback_prompt = self.poke_config.get("pokeback_prompt", "请以可爱的语气，生成一句主动戳别人的回应，表现出顽皮或调皮的态度，但整体保持可爱风格。") if self.poke_config else "请以可爱的语气，生成一句主动戳别人的回应，表现出顽皮或调皮的态度，但整体保持可爱风格。"
        
        logger.info(f"戳一戳功能状态: {'启用' if self.poke_enabled else '禁用'}，戳回概率: {self.pokeback_probability}")

        # 获取 active_message 配置对象
        self.active_message_config = self.config.get("active_message", {})
        # 获取子项配置 - 修复可能的列表索引错误
        self.active_message_enabled = self.active_message_config.get("is_enable", False) if self.active_message_config else False
        self.active_message_prompt = self.active_message_config.get("active_message_prompt", "长时间没有人搭理你，因此请你以可爱的语气，生成一条消息寻求大家陪你聊天或玩耍，表现出些许娇嗔或不满，但整体保持可爱风格。") if self.active_message_config else "长时间没有人搭理你，因此请你以可爱的语气，生成一条消息寻求大家陪你聊天或玩耍，表现出些许娇嗔或不满，但整体保持可爱风格。"
        self.time_interval = self.active_message_config.get("time_interval", 3600) if self.active_message_config else 3600
        
        logger.info(f"主动消息功能状态: {'启用' if self.active_message_enabled else '禁用'}，时间间隔: {self.time_interval}秒")
        
        # 用于跟踪每个群的最后消息时间
        self.group_last_message_time = {}
    
    @filter.on_decorating_result()
    async def QQ_emoji(self, event: AstrMessageEvent, result: MessageEventResult):
        """
        对于大模型返回的[qq_emoji:xxx]，替换为对应的QQ表情
        """
        try:
            # 获取消息内容
            message = result  # 使用传入的result参数而不是从event获取
            chain = message.chain
            new_chain = []
            
            # 处理消息链中的每个组件
            for component in chain:
                # 只处理Plain文本组件
                if isinstance(component, Comp.Plain):
                    text = component.text
                    # 使用正则表达式查找所有的{qq_emoji:xxx}格式
                    pattern = r'\{qq_emoji:(\w+)\}'
                    matches = list(re.finditer(pattern, text))
                    
                    if not matches:
                        # 如果没有匹配项，直接添加原组件
                        new_chain.append(component)
                        continue
                    
                    # 处理匹配项
                    last_end = 0
                    for match in matches:
                        start, end = match.span()
                        emoji_name = match.group(1)
                        
                        # 添加表情前的文本
                        if start > last_end:
                            prefix_text = text[last_end:start]
                            if prefix_text:
                                new_chain.append(Comp.Plain(prefix_text))
                        
                        # 添加表情
                        if emoji_name in self.emoji_map:
                            emoji_id = self.emoji_map[emoji_name]
                            new_chain.append(Comp.Face(id=emoji_id))
                            logger.debug(f"替换表情: {emoji_name} -> Face({emoji_id})")
                        else:
                            # 表情名不存在时，保留原文本
                            new_chain.append(Comp.Plain(match.group(0)))
                            logger.warning(f"未找到表情: {emoji_name}")
                        
                        last_end = end
                    
                    # 添加最后一个表情后的文本
                    if last_end < len(text):
                        suffix_text = text[last_end:]
                        if suffix_text:
                            new_chain.append(Comp.Plain(suffix_text))
                else:
                    # 非Plain组件直接添加
                    new_chain.append(component)
            
            # 将处理后的chain重新赋值给消息
            message.chain = new_chain
            logger.info(f"处理后的消息链: {message.chain}") 
        except Exception as e:
            logger.error(f"处理QQ表情时出错: {str(e)}")

    @event_message_type(EventMessageType.GROUP_MESSAGE)
    async def track_group_message(self, event: AstrMessageEvent):
        """
        跟踪群聊消息，记录最后一条消息的时间
        """
        try:
            current_time = int(time.time())
            group_id = event.get_group_id()
            
            if group_id:
                # 更新群组的最后消息时间
                self.group_last_message_time[group_id] = current_time
                logger.debug(f"群 {group_id} 有新消息，更新最后消息时间为 {current_time}")
        except Exception as e:
            logger.error(f"跟踪群消息时出错: {str(e)}")

    @event_message_type(EventMessageType.ALL)
    async def on_poke(self, event: AstrMessageEvent):
        """
        处理戳一戳事件
        """
        # 如果戳一戳功能被禁用，直接返回
        if not getattr(self, "poke_enabled", False):
            return
            
        message_data = event.message_obj.raw_message
        group_id = event.get_group_id()

        if message_data.get('post_type') == 'notice' and \
             message_data.get('notice_type') == 'notify' and \
             message_data.get('sub_type') == 'poke':
            bot_id = message_data.get('self_id')
            sender_id = message_data.get('user_id')
            target_id = message_data.get('target_id')

            if sender_id != bot_id and target_id == bot_id:
                # bot被戳，准备回应
                logger.info(f"机器人被用户 {sender_id} 戳了，正在生成回应...")
                
                try:
                    # 获取用户当前与 LLM 的对话以获得上下文信息。
                    curr_cid = await self.context.conversation_manager.get_curr_conversation_id(event.unified_msg_origin)
                    conversation = None # 对话对象
                    context = [] # 上下文列表
                    if curr_cid:
                        conversation = await self.context.conversation_manager.get_conversation(event.unified_msg_origin, curr_cid)
                        context = json.loads(conversation.history)
                    
                    # 决定是否回戳用户
                    will_pokeback = random.random() < self.pokeback_probability
                    
                    # 根据是否回戳选择提示语
                    if will_pokeback:
                        prompt = self.pokeback_prompt
                        logger.info(f"触发回戳，概率: {self.pokeback_probability}，使用回戳提示语")
                    else:
                        prompt = self.poke_prompt
                    
                    # 直接使用event.request_llm方法，避免使用provider_request.await_result()
                    yield event.request_llm(
                        prompt=prompt,
                        func_tool_manager=self.context.get_llm_tool_manager(),
                        contexts=context,
                        conversation=conversation
                    )
                    
                    # 如果决定回戳用户
                    if will_pokeback:
                        try:
                            # 尝试发送回戳操作，具体实现取决于平台API
                            assert isinstance(event, AiocqhttpMessageEvent)
                            payloads = {"user_id": sender_id, "group_id": group_id}
                            await event.bot.api.call_action('send_poke', **payloads)
                            logger.info(f"成功回戳用户 {sender_id}")
                        except Exception as e:
                            logger.error(f"回戳失败: {str(e)}")
                    
                    # 发送回应消息
                    try:
                        # 使用正确的At组件创建方式
                        chain = [
                            Comp.At(qq=sender_id)
                        ]
                        
                        # 确保返回一个可迭代对象
                        result = event.chain_result(chain)
                        if result is not None:  # 检查结果是否为None
                            yield result
                        else:
                            # 如果chain_result返回None，尝试使用plain_result
                            logger.warning("chain_result返回None，尝试使用plain_result")
                            plain_result = event.plain_result(f"@{sender_id}")
                            if plain_result is not None:
                                yield plain_result
                            else:
                                logger.error("所有回复方法都返回None，无法发送消息")
                    except Exception as e:
                        logger.error(f"创建At组件或发送回应失败: {str(e)}，尝试使用纯文本方式")
                        try:
                            # 尝试使用纯文本方式
                            plain_result = event.plain_result(f"@{sender_id}")
                            if plain_result is not None:
                                yield plain_result
                            else:
                                logger.error("plain_result返回None，无法发送消息")
                        except Exception as e2:
                            logger.error(f"使用纯文本方式也失败: {str(e2)}")
                    
                except Exception as e:
                    logger.error(f"处理戳一戳事件出错: {str(e)}")
                    # 出错时使用备用回应
                    fallback = random.choice(self.fallback_responses)
                    try:
                        # 尝试发送纯文本作为最后的备选方案
                        plain_result = event.plain_result(fallback)
                        if plain_result is not None:
                            yield plain_result
                        else:
                            logger.error("最终备选方案返回None，无法发送消息")
                    except Exception as e3:
                        logger.error(f"发送备选回应也失败: {str(e3)}")

    @event_message_type(EventMessageType.GROUP_MESSAGE)
    async def active_message(self, event: AstrMessageEvent):
        """
        如果群聊长时间没有消息，主动发送一条消息
        """
        try:
            # 如果主动消息功能被禁用，直接返回
            if not getattr(self, "active_message_enabled", False):
                return

            current_time = int(time.time())
            group_id = event.get_group_id()
            
            # 如果没有有效的群ID，直接返回
            if not group_id:
                return
                
            # 获取该群最后一条消息的时间
            last_message_time = self.group_last_message_time.get(group_id, 0)
            
            # 如果该群此前没有记录到消息，则不发送主动消息
            if last_message_time == 0:
                logger.debug(f"群 {group_id} 没有历史消息记录，不发送主动消息")
                return
                
            # 检查是否已经超过了设定的时间间隔
            time_elapsed = current_time - last_message_time
            if time_elapsed >= self.time_interval:
                logger.info(f"群 {group_id} 已有 {time_elapsed} 秒无消息，触发主动消息")
                
                # 检查是否已经在该群发送过主动消息
                last_active_time_key = f"last_active_time_{group_id}"
                last_active_time = self.config.get(last_active_time_key, 0)
                
                # 确保不会在短时间内连续发送多条主动消息
                # 至少要间隔配置的时间间隔的1/2
                min_interval = self.time_interval // 2
                if current_time - last_active_time < min_interval:
                    logger.debug(f"与上次发送主动消息间隔不足 {min_interval} 秒，暂不发送")
                    return
                    
                # 获取上下文
                try:
                    curr_cid = await self.context.conversation_manager.get_curr_conversation_id(event.unified_msg_origin)
                    conversation = None
                    context = []
                    if curr_cid:
                        conversation = await self.context.conversation_manager.get_conversation(event.unified_msg_origin, curr_cid)
                        if conversation and hasattr(conversation, 'history') and conversation.history:
                            context = json.loads(conversation.history)
                except Exception as e:
                    logger.error(f"获取对话上下文失败: {str(e)}")
                    context = []
                
                # 计算无人发言的时长（小时、分钟）以添加到提示中
                hours, remainder = divmod(time_elapsed, 3600)
                minutes, _ = divmod(remainder, 60)
                time_desc = ""
                if hours > 0:
                    time_desc += f"{hours}小时"
                if minutes > 0 or hours == 0:
                    time_desc += f"{minutes}分钟"
                
                # 修改提示词，加入实际的沉默时间
                prompt = self.active_message_prompt.replace("长时间", f"{time_desc}")
                
                # 安全调用LLM接口
                try:
                    # 获取对话ID和上下文
                    curr_cid = await self.context.conversation_manager.get_curr_conversation_id(event.unified_msg_origin)
                    conversation = None
                    context = []
                    if curr_cid:
                        conversation = await self.context.conversation_manager.get_conversation(event.unified_msg_origin, curr_cid)
                        if conversation and hasattr(conversation, 'history') and conversation.history:
                            context = json.loads(conversation.history)
                            
                    # 修改提示词，加入实际的沉默时间
                    prompt = self.active_message_prompt.replace("长时间", f"{time_desc}")
                    
                    yield event.request_llm(
                        prompt=prompt,
                        func_tool_manager=self.context.get_llm_tool_manager(),
                        contexts=context,
                        conversation=conversation
                    )
                    self.config[last_active_time_key] = current_time
                    self.group_last_message_time[group_id] = current_time
                    
                except Exception as e:
                    response_text = f"诶，大家已经{time_desc}没有说话了，是不是都在忙呀？有人陪我聊聊天吗？"
                    logger.error(f"调用LLM生成主动消息失败: {str(e)}")
        
        except Exception as e:
            logger.error(f"处理主动消息事件出错: {str(e)}")
    
    async def terminate(self):
        logger.info("插件已终止")
        return await super().terminate()
