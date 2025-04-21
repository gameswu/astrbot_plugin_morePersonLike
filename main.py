from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp
from astrbot.api.all import *

@register("morePersonLike", "gameswu", "用于帮助缺少多模态能力的llm更加拟人化，仅支持QQ平台", "0.1.0b", "https://github.com/gameswu/astrbot_plugin_morePersonLike")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        logger.info("戳一戳响应插件已初始化")

    @event_message_type(EventMessageType.GROUP_MESSAGE)
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
                # bot被戳，调用LLM接口生成拒绝回应
                logger.info(f"机器人被用户 {sender_id} 戳了，正在生成回应...")
                
                # 构建提示词引导LLM生成拒绝被戳的回应
                prompt = "请以可爱的语气，生成一句被人戳了的拒绝回应，表现出些许娇嗔或不满，但整体保持可爱风格。不要超过30个字。"
                
                try:
                    # 调用AstrBot的LLM接口
                    llm_response = await self.context.get_using_provider(prompt)
                    
                    # 确保回应不为空
                    if llm_response and len(llm_response.strip()) > 0:
                        response_text = llm_response.strip()
                    else:
                        # 备用回应
                        response_text = "哼！不要随便戳我啦，人家会生气的！"
                    
                    logger.info(f"生成的回应: {response_text}")
                    
                    # 发送回应消息
                    yield event.chain_result([
                        Comp.At(sender_id),
                        Comp.Plain(" "),
                        Comp.Plain(response_text)
                    ])
                    
                except Exception as e:
                    logger.error(f"调用LLM接口失败: {str(e)}")
                    # 出错时使用备用回应
                    yield event.chain_result([
                        Comp.At(sender_id),
                        Comp.Plain(" 不要戳我啦！好痒的说~")
                    ])
    
    async def terminate(self):
        logger.info("戳一戳响应插件已终止")
