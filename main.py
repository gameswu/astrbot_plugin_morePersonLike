from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp
from astrbot.api.all import *
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
import random
import time
import json

@register("morePersonLike", "gameswu", "用于帮助缺少多模态能力的llm更加拟人化，仅支持QQ平台", "0.1.0b", "https://github.com/gameswu/astrbot_plugin_morePersonLike")
class MorePersonLike(Star):
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

    async def initialize(self):
        logger.info("插件已初始化")
        # 获取 on_poke 配置对象
        self.poke_config = self.config.get("on_poke", {})
        # 获取子项配置 - 修复可能的列表索引错误
        self.poke_enabled = self.poke_config.get("is_enable", False) if self.poke_config else False
        self.poke_prompt = self.poke_config.get("poke_prompt", "请以可爱的语气，生成一句被人戳了的拒绝回应，表现出些许娇嗔或不满，但整体保持可爱风格。") if self.poke_config else "请以可爱的语气，生成一句被人戳了的拒绝回应，表现出些许娇嗔或不满，但整体保持可爱风格。"
        self.pokeback_probability = self.poke_config.get("pokeback_probability", 0.2) if self.poke_config else 0.2
        
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

    @event_message_type(EventMessageType.GROUP_MESSAGE)
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
                    # 使用配置中的提示语
                    prompt = self.poke_prompt
                    
                    llm_response = await self.context.get_using_provider().text_chat(prompt=prompt, contexts=context)
                        
                    # 确保回应不为空
                    if llm_response and len(llm_response.completion_text.strip()) > 0:
                        response_text = llm_response.completion_text.strip()
                        logger.info(f"LLM生成的回应: {response_text}")
                    else:
                        # 备用回应
                        response_text = random.choice(self.fallback_responses)
                        
                    logger.info(f"生成的回应: {response_text}")
                    
                    # 根据概率决定是否回戳用户
                    if random.random() < self.pokeback_probability:
                        logger.info(f"触发回戳，概率: {self.pokeback_probability}")
                        # 这里添加回戳用户的代码，如果API支持的话
                        try:
                            # 尝试发送回戳操作，具体实现取决于平台API
                            # 如果不支持程序化戳一戳，可以在消息中说明"戳了戳你"
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
                            Comp.At(qq=sender_id),
                            Comp.Plain(response_text)
                        ]
                        
                        # 确保返回一个可迭代对象
                        result = event.chain_result(chain)
                        if result is not None:  # 检查结果是否为None
                            yield result
                        else:
                            # 如果chain_result返回None，尝试使用plain_result
                            logger.warning("chain_result返回None，尝试使用plain_result")
                            plain_result = event.plain_result(f"@{sender_id} {response_text}")
                            if plain_result is not None:
                                yield plain_result
                            else:
                                logger.error("所有回复方法都返回None，无法发送消息")
                    except Exception as e:
                        logger.error(f"创建At组件或发送回应失败: {str(e)}，尝试使用纯文本方式")
                        try:
                            # 尝试使用纯文本方式
                            plain_result = event.plain_result(f"@{sender_id} {response_text}")
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
                    provider = self.context.get_using_provider()
                    if provider:
                        llm_response = await provider.text_chat(prompt=prompt, contexts=context)
                        if llm_response and hasattr(llm_response, 'completion_text'):
                            response_text = llm_response.completion_text.strip()
                            logger.info(f"LLM生成的主动消息: {response_text}")
                        else:
                            response_text = f"诶，大家已经{time_desc}没有说话了，是不是都在忙呀？有人陪我聊聊天吗？"
                            logger.warning("LLM响应无效，使用备用回复")
                    else:
                        response_text = f"诶，大家已经{time_desc}没有说话了，是不是都在忙呀？有人陪我聊聊天吗？"
                        logger.warning("无法获取LLM提供者，使用备用回复")
                except Exception as e:
                    response_text = f"诶，大家已经{time_desc}没有说话了，是不是都在忙呀？有人陪我聊聊天吗？"
                    logger.error(f"调用LLM生成主动消息失败: {str(e)}")
                
                # 发送主动消息
                try:
                    result = event.plain_result(response_text)
                    if result is not None:
                        yield result
                        # 更新该群的最后主动消息时间
                        self.config[last_active_time_key] = current_time
                        # 同时更新最后消息时间（防止短时间内再次触发）
                        self.group_last_message_time[group_id] = current_time
                    else:
                        logger.error("主动消息发送失败，返回None")
                except Exception as e:
                    logger.error(f"发送主动消息失败: {str(e)}")
        
        except Exception as e:
            logger.error(f"处理主动消息事件出错: {str(e)}")
    
    async def terminate(self):
        logger.info("插件已终止")
