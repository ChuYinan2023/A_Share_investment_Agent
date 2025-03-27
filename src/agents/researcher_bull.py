from langchain_core.messages import HumanMessage
from src.agents.state import AgentState, show_agent_reasoning, show_workflow_status
import json
import ast
from src.utils.logging_config import setup_logger

# 设置日志记录
logger = setup_logger('researcher_bull_agent')


def researcher_bull_agent(state: AgentState):
    """负责从乐观角度分析信号并生成看涨投资论点"""
    logger.info("="*50)
    logger.info("开始执行 看涨研究员")
    logger.info("="*50)
    show_workflow_status("看涨研究员")
    show_reasoning = state["metadata"]["show_reasoning"]
    
    symbol = state["data"]["ticker"]
    logger.info(f"正在从看涨角度分析股票: {symbol}")

    # Fetch messages from analysts
    logger.info("获取各分析师的信号...")
    technical_message = next(
        msg for msg in state["messages"] if msg.name == "technical_analyst_agent")
    fundamentals_message = next(
        msg for msg in state["messages"] if msg.name == "fundamentals_agent")
    sentiment_message = next(
        msg for msg in state["messages"] if msg.name == "sentiment_agent")
    valuation_message = next(
        msg for msg in state["messages"] if msg.name == "valuation_agent")

    try:
        logger.info("解析分析师信号数据...")
        fundamental_signals = json.loads(fundamentals_message.content)
        technical_signals = json.loads(technical_message.content)
        sentiment_signals = json.loads(sentiment_message.content)
        valuation_signals = json.loads(valuation_message.content)
    except Exception as e:
        logger.warning(f"JSON解析失败，尝试使用ast.literal_eval: {e}")
        fundamental_signals = ast.literal_eval(fundamentals_message.content)
        technical_signals = ast.literal_eval(technical_message.content)
        sentiment_signals = ast.literal_eval(sentiment_message.content)
        valuation_signals = ast.literal_eval(valuation_message.content)

    logger.info("各分析师信号概览:")
    logger.info(f"- 技术分析: {technical_signals['signal']} (置信度: {technical_signals['confidence']})")
    logger.info(f"- 基本面分析: {fundamental_signals['signal']} (置信度: {fundamental_signals['confidence']})")
    logger.info(f"- 情感分析: {sentiment_signals['signal']} (置信度: {sentiment_signals['confidence']})")
    logger.info(f"- 估值分析: {valuation_signals['signal']} (置信度: {valuation_signals['confidence']})")

    # Analyze from bullish perspective
    logger.info("开始从看涨角度分析各信号...")
    bullish_points = []
    confidence_scores = []

    # Technical Analysis
    logger.info("分析技术指标...")
    if technical_signals["signal"] == "bullish":
        point = f"Technical indicators show bullish momentum with {technical_signals['confidence']} confidence"
        bullish_points.append(point)
        confidence = float(str(technical_signals["confidence"]).replace("%", "")) / 100
        confidence_scores.append(confidence)
        logger.info(f"✓ 看涨技术指标: {point} (置信度: {confidence:.2f})")
    else:
        point = "Technical indicators may be conservative, presenting buying opportunities"
        bullish_points.append(point)
        confidence_scores.append(0.3)
        logger.info(f"✓ 技术指标非看涨，但提供看涨观点: {point} (置信度: 0.30)")

    # Fundamental Analysis
    logger.info("分析基本面指标...")
    if fundamental_signals["signal"] == "bullish":
        point = f"Strong fundamentals with {fundamental_signals['confidence']} confidence"
        bullish_points.append(point)
        confidence = float(str(fundamental_signals["confidence"]).replace("%", "")) / 100
        confidence_scores.append(confidence)
        logger.info(f"✓ 看涨基本面: {point} (置信度: {confidence:.2f})")
    else:
        point = "Company fundamentals show potential for improvement"
        bullish_points.append(point)
        confidence_scores.append(0.3)
        logger.info(f"✓ 基本面非看涨，但提供看涨观点: {point} (置信度: 0.30)")

    # Sentiment Analysis
    logger.info("分析市场情感...")
    if sentiment_signals["signal"] == "bullish":
        point = f"Positive market sentiment with {sentiment_signals['confidence']} confidence"
        bullish_points.append(point)
        confidence = float(str(sentiment_signals["confidence"]).replace("%", "")) / 100
        confidence_scores.append(confidence)
        logger.info(f"✓ 看涨市场情感: {point} (置信度: {confidence:.2f})")
    else:
        point = "Market sentiment may be overly pessimistic, creating value opportunities"
        bullish_points.append(point)
        confidence_scores.append(0.3)
        logger.info(f"✓ 市场情感非看涨，但提供看涨观点: {point} (置信度: 0.30)")

    # Valuation Analysis
    logger.info("分析估值情况...")
    if valuation_signals["signal"] == "bullish":
        point = f"Stock appears undervalued with {valuation_signals['confidence']} confidence"
        bullish_points.append(point)
        confidence = float(str(valuation_signals["confidence"]).replace("%", "")) / 100
        confidence_scores.append(confidence)
        logger.info(f"✓ 看涨估值: {point} (置信度: {confidence:.2f})")
    else:
        point = "Current valuation may not fully reflect growth potential"
        bullish_points.append(point)
        confidence_scores.append(0.3)
        logger.info(f"✓ 估值非看涨，但提供看涨观点: {point} (置信度: 0.30)")

    # Calculate overall bullish confidence
    avg_confidence = sum(confidence_scores) / len(confidence_scores)
    logger.info(f"计算看涨总体置信度: {avg_confidence:.2f}")

    message_content = {
        "perspective": "bullish",
        "confidence": avg_confidence,
        "thesis_points": bullish_points,
        "reasoning": "Bullish thesis based on comprehensive analysis of technical, fundamental, sentiment, and valuation factors"
    }

    logger.info("生成看涨投资论点:")
    for i, point in enumerate(bullish_points):
        logger.info(f"  {i+1}. {point}")

    message = HumanMessage(
        content=json.dumps(message_content),
        name="researcher_bull_agent",
    )

    if show_reasoning:
        show_agent_reasoning(message_content, "看涨研究员")

    show_workflow_status("看涨研究员", "completed")
    logger.info("看涨研究员分析完成")
    logger.info("="*50)
    
    return {
        "messages": state["messages"] + [message],
        "data": state["data"],
    }
