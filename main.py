from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp
from astrbot.api.all import *
import random

@register("morePersonLike", "gameswu", "用于帮助缺少多模态能力的llm更加拟人化，仅支持QQ平台", "0.1.0b", "https://github.com/gameswu/astrbot_plugin_morePersonLike")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
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
        logger.info("戳一戳响应插件已初始化")

    @event_message_type(EventMessageType.ALL)
    async def on_poke(self, event: AstrMessageEvent):
        """
        处理戳一戳事件
        """
        message_data = event.message_obj.raw_message

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
                    # 构建提示词引导LLM生成拒绝被戳的回应
                    prompt = "请以可爱的语气，生成一句被人戳了的拒绝回应，表现出些许娇嗔或不满，但整体保持可爱风格。不要超过30个字。"
                    
                    # 尝试获取LLM提供者
                    provider = self.context.get_using_provider()
                    
                    # 如果成功获取提供者，则请求生成回应
                    if provider:
                        llm_response = await provider.text_chat(prompt=prompt)
                        
                        # 确保回应不为空
                        if llm_response and len(llm_response.strip()) > 0:
                            response_text = llm_response.strip()
                        else:
                            # 备用回应
                            response_text = random.choice(self.fallback_responses)
                        
                        logger.info(f"生成的回应: {response_text}")
                    else:
                        # 如果无法获取提供者，使用备用回应
                        response_text = random.choice(self.fallback_responses)
                        logger.warning("无法获取LLM提供者，使用备用回应")
                    
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
    
    async def terminate(self):
        logger.info("戳一戳响应插件已终止")
