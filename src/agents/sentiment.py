from langchain_core.messages import HumanMessage
from src.agents.state import AgentState, show_agent_reasoning, show_workflow_status
from src.tools.news_crawler import get_stock_news, get_news_sentiment
from src.utils.logging_config import setup_logger
import json
from datetime import datetime, timedelta

# 设置日志记录
logger = setup_logger('sentiment_agent')


def sentiment_agent(state: AgentState):
    """负责进行市场情感分析"""
    logger.info("="*50)
    logger.info("开始执行 情感分析师")
    logger.info("="*50)
    show_workflow_status("情感分析师")
    show_reasoning = state["metadata"]["show_reasoning"]
    data = state["data"]
    symbol = data["ticker"]
    logger.info(f"正在分析股票: {symbol}")
    
    # 从命令行参数获取新闻数量，默认为5条
    num_of_news = data.get("num_of_news", 5)
    logger.info(f"设定获取新闻数量: {num_of_news}条")

    # 获取新闻数据并分析情感
    logger.info(f"开始获取 {symbol} 的相关新闻...")
    news_list = get_stock_news(symbol, max_news=num_of_news)  # 确保获取足够的新闻
    logger.info(f"成功获取新闻数量: {len(news_list)}条")
    
    if len(news_list) == 0:
        logger.warning(f"未找到与 {symbol} 相关的新闻")
        sentiment_score = 0
        recent_news = []
    else:
        # 过滤7天内的新闻
        cutoff_date = datetime.now() - timedelta(days=7)
        logger.info(f"筛选最近7天内的新闻 (截止日期: {cutoff_date.strftime('%Y-%m-%d')})")
        recent_news = [news for news in news_list
                       if datetime.strptime(news['publish_time'], '%Y-%m-%d %H:%M:%S') > cutoff_date]
        logger.info(f"最近7天内的新闻数量: {len(recent_news)}条")
        
        # 记录新闻标题
        if len(recent_news) > 0:
            logger.info("最近新闻标题:")
            for i, news in enumerate(recent_news[:min(5, len(recent_news))]):
                publish_time = news.get('publish_time', '未知时间')
                title = news.get('title', '无标题')
                logger.info(f"  {i+1}. [{publish_time}] {title}")
            
            if len(recent_news) > 5:
                logger.info(f"  ... 及其他 {len(recent_news) - 5} 条新闻")
        
        # 分析情感
        logger.info("开始进行情感分析...")
        sentiment_score = get_news_sentiment(recent_news, num_of_news=num_of_news)
        logger.info(f"情感分析得分: {sentiment_score:.4f} (-1为极度负面, 1为极度正面)")

    # 根据情感分数生成交易信号和置信度
    logger.info("根据情感分数生成交易信号...")
    if sentiment_score >= 0.5:
        signal = "bullish"
        confidence = round(abs(sentiment_score) * 100)
        logger.info(f"情感信号: 看涨 (得分 {sentiment_score:.2f} >= 0.5)")
    elif sentiment_score <= -0.5:
        signal = "bearish"
        confidence = round(abs(sentiment_score) * 100)
        logger.info(f"情感信号: 看跌 (得分 {sentiment_score:.2f} <= -0.5)")
    else:
        signal = "neutral"
        confidence = round((1 - abs(sentiment_score)) * 100)
        logger.info(f"情感信号: 中性 (-0.5 < 得分 {sentiment_score:.2f} < 0.5)")
    
    logger.info(f"情感分析置信度: {confidence}%")

    # 生成分析结果
    message_content = {
        "signal": signal,
        "confidence": str(confidence) + "%",
        "reasoning": f"Based on {len(recent_news)} recent news articles, sentiment score: {sentiment_score:.2f}"
    }

    # 如果需要显示推理过程
    if show_reasoning:
        show_agent_reasoning(message_content, "情感分析师")

    # 创建消息
    message = HumanMessage(
        content=json.dumps(message_content),
        name="sentiment_agent",
    )

    show_workflow_status("情感分析师", "completed")
    logger.info("情感分析完成")
    logger.info("="*50)
    
    return {
        "messages": [message],
        "data": {
            **data,
            "sentiment_analysis": sentiment_score
        }
    }
