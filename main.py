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
import os
from typing import List, Dict, Any, Optional

# 导入设置文件
from .setting import FALLBACK_RESPONSES, load_config

@register("morePersonLike", "gameswu", "用于帮助缺少多模态能力的llm更加拟人化", "0.1.3b", "https://github.com/gameswu/astrbot_plugin_morePersonLike")
class morePersonLikePlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        # 从设置文件加载备用回复
        self.fallback_responses = FALLBACK_RESPONSES
        
        # 初始化一个空的emoji映射表，将在initialize方法中从文件加载
        self.emoji_map = {}

    async def initialize(self):
        logger.info("插件已初始化")
        
        # 从设置文件加载配置
        settings = load_config(self.config)
        
        # 获取戳一戳配置
        poke_settings = settings["poke_config"]
        self.poke_enabled = poke_settings["is_enable"]
        self.poke_prompt = poke_settings["poke_prompt"]
        self.pokeback_probability = poke_settings["pokeback_probability"]
        self.pokeback_prompt = poke_settings["pokeback_prompt"]
        
        logger.info(f"戳一戳功能状态: {'启用' if self.poke_enabled else '禁用'}，戳回概率: {self.pokeback_probability}")

        # 获取主动消息配置
        active_settings = settings["active_message_config"]
        self.active_message_enabled = active_settings["is_enable"]
        self.active_message_prompt = active_settings["active_message_prompt"]
        self.time_interval = active_settings["time_interval"]
        
        logger.info(f"主动消息功能状态: {'启用' if self.active_message_enabled else '禁用'}，时间间隔: {self.time_interval}秒")
        
        # 获取QQ表情配置
        emoji_settings = settings["qq_emoji_config"]
        self.emoji_enabled = emoji_settings["is_enable"]
        emoji_file_path = "data/qq_emoji.json"  # 默认的emoji json文件路径

        # 获取好感度配置
        self.favorability_enabled = settings["favorability_config"]["is_enable"]
        self.favorability_change_value = settings["favorability_config"]["change_value"]
        self.favorability_initial = settings["favorability_config"]["initial"]
        self.favorability_max_value = settings["favorability_config"]["max_value"]
        self.favorability_min_value = settings["favorability_config"]["min_value"]
        
        # 确保好感度数据目录存在
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(current_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        
        self.favorability_file_path = os.path.join(current_dir, "data", "favorability.json")
        
        # 初始化好感度文件，如果文件不存在
        if not os.path.exists(self.favorability_file_path):
            try:
                with open(self.favorability_file_path, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=4)
                logger.info(f"已创建好感度数据文件: {self.favorability_file_path}")
            except Exception as e:
                logger.error(f"创建好感度数据文件失败: {str(e)}")
        
        logger.info(f"好感度功能状态: {'启用' if self.favorability_enabled else '禁用'}，初始值: {self.favorability_initial}，最大值: {self.favorability_max_value}，最小值: {self.favorability_min_value}，概率: {self.favorability_probability}")
        
        # 从JSON文件加载emoji映射表
        try:
            # 获取当前文件所在目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # 构建emoji json文件的路径
            emoji_file_path = os.path.join(current_dir, emoji_file_path)
            
            # 检查文件是否存在
            if not os.path.exists(emoji_file_path):
                logger.error(f"QQ表情映射文件不存在: {emoji_file_path}")
                # 如果文件不存在，保持emoji_map为空字典
            else:
                # 从文件加载数据
                with open(emoji_file_path, 'r', encoding='utf-8') as f:
                    self.emoji_map = json.load(f)
                logger.info(f"成功从文件加载了 {len(self.emoji_map)} 个QQ表情映射")
        except Exception as e:
            logger.error(f"加载QQ表情映射文件时出错: {str(e)}")

        # 用于跟踪每个群的最后消息时间
        self.group_last_message_time = {}

    @llm_tool(name="send_qq_emoji")
    async def send_qq_emoji(self, event: AstrMessageEvent, emoji: str):
        """发送QQ表情

        Args:
            emoji(string): qq表情的名称
        """
        # 如果QQ表情功能被禁用，直接返回
        if not self.emoji_enabled:
            return
        
        # 检查emoji是否在映射表中
        if emoji in self.emoji_map:
            # 获取对应的QQ表情ID
            emoji_id = self.emoji_map[emoji]
            logger.info(f"发送QQ表情: {emoji} (ID: {emoji_id})")
            
            # 发送QQ表情消息
            try:
                yield event.chain_result([Comp.Face(id=emoji_id)])
                logger.info(f"成功发送QQ表情: {emoji}")
            except Exception as e:
                logger.error(f"发送QQ表情失败: {str(e)}")
        else:
            logger.warning(f"未找到QQ表情映射: {emoji}")
            
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
                            if group_id is None:
                                payloads = {"user_id": sender_id}
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

    @llm_tool(name="read_group_notice")
    async def read_group_notice(self, event: AstrMessageEvent):
        """读取QQ群公告
        """
        # 读取群组通知的逻辑
        try:
            group_id = event.get_group_id()
            if group_id:
                # 获取群组通知
                notice = await event.bot.api.call_action('_get_group_notice', group_id=group_id)
                return notice
            else:
                logger.warning("未能获取到有效的群组ID")
        except Exception as e:
            logger.error(f"读取群组通知失败: {str(e)}")

    @filter.on_llm_request()
    async def add_favorability_prompt(self, event: AstrMessageEvent, req: ProviderRequest):
        """
        增加好感度评价的prompt
        """
        # 如果好感度功能被禁用，直接返回
        if not self.favorability_enabled:
            return
        req.system_prompt += f"请你首先利用相应的函数工具查询你与用户之间的好感值并根据分数高低给出相应情绪的回应，请注意好感度总分范围为0到{self.favorability_max_value}。并以自己的视角对此前用户的用语评价好感度的变化，范围为从{-self.favorability_change_value}到{self.favorability_change_value}的整数，并使用相应的函数工具记录评分结果。"

    @filter.llm_tool(name="add_favorability")
    async def add_favorability(self, event: AstrMessageEvent, favorability: int):
        """增加好感度

        Args:
            favorability(number): 好感度评分
        """
        # 如果好感度功能被禁用，直接返回
        if not self.favorability_enabled:
            return
        
        # 获取用户ID
        user_id = event.get_sender_id()
        if not user_id:
            logger.warning("无法获取用户ID，好感度更新失败")
            return
            
        # 确保好感度变化值在合理范围内
        favorability = max(min(favorability, self.favorability_change_value), -self.favorability_change_value)
        
        # 读取并更新好感度数据
        try:
            favorability_data = {}
            
            # 尝试读取现有的好感度数据
            if os.path.exists(self.favorability_file_path):
                try:
                    with open(self.favorability_file_path, 'r', encoding='utf-8') as f:
                        favorability_data = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError) as e:
                    logger.error(f"读取好感度数据失败，将创建新文件: {str(e)}")
                    favorability_data = {}
            
            # 获取用户当前好感度，如果用户不存在则使用初始值
            user_id_str = str(user_id)  # 确保用户ID是字符串类型
            current_favorability = favorability_data.get(user_id_str)
            
            # 如果用户不存在，初始化好感度值
            if current_favorability is None:
                current_favorability = self.favorability_initial
                logger.info(f"用户 {user_id} 首次获取好感度，初始化为 {self.favorability_initial}")
            
            # 计算新的好感度值，确保在合理范围内
            new_favorability = min(max(current_favorability + favorability, self.favorability_min_value), self.favorability_max_value)
            
            # 更新好感度数据
            favorability_data[user_id_str] = new_favorability
            
            # 保存更新后的好感度数据
            with open(self.favorability_file_path, 'w', encoding='utf-8') as f:
                json.dump(favorability_data, f, ensure_ascii=False, indent=4)
            
            change_type = "增加" if favorability > 0 else "减少"
            logger.info(f"用户 {user_id} 的好感度{change_type}了 {abs(favorability)}，当前好感度: {new_favorability}")
            
        except Exception as e:
            logger.error(f"更新好感度时出错: {str(e)}")
    
    @filter.llm_tool(name="get_favorability")
    async def get_favorability(self, event: AstrMessageEvent):
        """获取当前用户的好感度值"""
        # 如果好感度功能被禁用，直接返回
        if not self.favorability_enabled:
            return {"favorability": self.favorability_initial, "status": "disabled"}
        
        # 获取用户ID
        user_id = event.get_sender_id()
        if not user_id:
            logger.warning("无法获取用户ID，好感度查询失败")
            return {"favorability": self.favorability_initial, "status": "error", "message": "无法获取用户ID"}
        
        try:
            favorability_data = {}
            
            # 尝试读取现有的好感度数据
            if os.path.exists(self.favorability_file_path):
                try:
                    with open(self.favorability_file_path, 'r', encoding='utf-8') as f:
                        favorability_data = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError) as e:
                    logger.error(f"读取好感度数据失败: {str(e)}")
                    return {"favorability": self.favorability_initial, "status": "error", "message": f"读取好感度数据失败: {str(e)}"}
            
            # 获取用户当前好感度，如果用户不存在则使用初始值
            user_id_str = str(user_id)
            current_favorability = favorability_data.get(user_id_str, self.favorability_initial)
            
            # 如果用户不存在，将用户添加到好感度数据中
            if user_id_str not in favorability_data:
                favorability_data[user_id_str] = self.favorability_initial
                logger.info(f"用户 {user_id} 首次查询好感度，初始化为 {self.favorability_initial}")
                
                # 保存更新后的好感度数据
                with open(self.favorability_file_path, 'w', encoding='utf-8') as f:
                    json.dump(favorability_data, f, ensure_ascii=False, indent=4)
            
            logger.info(f"用户 {user_id} 的当前好感度: {current_favorability}")
            return {"favorability": current_favorability, "status": "success"}
            
        except Exception as e:
            logger.error(f"查询好感度时出错: {str(e)}")
            return {"favorability": self.favorability_initial, "status": "error", "message": f"查询好感度时出错: {str(e)}"}

    async def terminate(self):
        logger.info("插件已终止")
        return await super().terminate()
