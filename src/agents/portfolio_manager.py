from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from src.tools.openrouter_config import get_chat_completion
import json
import ast
from src.utils.logging_config import setup_logger

from src.agents.state import AgentState, show_agent_reasoning, show_workflow_status


##### Portfolio Management Agent #####
# 设置日志记录器
logger = setup_logger('portfolio_manager')

def portfolio_management_agent(state: AgentState):
    """负责投资组合管理和最终交易决策"""
    logger.info("="*50)
    logger.info("开始执行 投资组合管理员")
    logger.info("="*50)
    show_workflow_status("投资组合管理员")
    show_reasoning = state["metadata"]["show_reasoning"]
    portfolio = state["data"]["portfolio"]
    
    symbol = state["data"]["ticker"]
    logger.info(f"开始为股票 {symbol} 制定投资组合决策...")
    logger.info(f"当前投资组合: 现金={portfolio['cash']:.2f}, 持股={portfolio['stock']}")

    # Get the technical analyst, fundamentals agent, and risk management agent messages
    logger.info("获取各分析师和风险管理员的信号...")
    technical_message = next(
        msg for msg in state["messages"] if msg.name == "technical_analyst_agent")
    fundamentals_message = next(
        msg for msg in state["messages"] if msg.name == "fundamentals_agent")
    sentiment_message = next(
        msg for msg in state["messages"] if msg.name == "sentiment_agent")
    valuation_message = next(
        msg for msg in state["messages"] if msg.name == "valuation_agent")
    risk_message = next(
        msg for msg in state["messages"] if msg.name == "risk_management_agent")

    # 解析风险管理信息
    try:
        logger.info("解析风险管理信息...")
        risk_data = json.loads(risk_message.content)
        logger.info(f"风险评分: {risk_data.get('risk_score', 'N/A')}/10, 建议交易行动: {risk_data.get('trading_action', 'N/A')}")
        logger.info(f"最大仓位限制: {risk_data.get('max_position_size', 0):.2f}")
    except Exception as e:
        logger.warning(f"解析风险管理信息失败: {e}")
        try:
            risk_data = ast.literal_eval(risk_message.content)
        except:
            logger.error("无法解析风险管理信息，使用默认值")
            risk_data = {"risk_score": 5, "trading_action": "hold", "max_position_size": 0}

    # Create the system message
    logger.info("构建系统提示...")
    system_message = {
        "role": "system",
        "content": """You are a portfolio manager making final trading decisions.
            Your job is to make a trading decision based on the team's analysis while strictly adhering
            to risk management constraints.

            RISK MANAGEMENT CONSTRAINTS:
            - You MUST NOT exceed the max_position_size specified by the risk manager
            - You MUST follow the trading_action (buy/sell/hold) recommended by risk management
            - These are hard constraints that cannot be overridden by other signals

            When weighing the different signals for direction and timing:
            1. Valuation Analysis (35% weight)
               - Primary driver of fair value assessment
               - Determines if price offers good entry/exit point
            
            2. Fundamental Analysis (30% weight)
               - Business quality and growth assessment
               - Determines conviction in long-term potential
            
            3. Technical Analysis (25% weight)
               - Secondary confirmation
               - Helps with entry/exit timing
            
            4. Sentiment Analysis (10% weight)
               - Final consideration
               - Can influence sizing within risk limits
            
            The decision process should be:
            1. First check risk management constraints
            2. Then evaluate valuation signal
            3. Then evaluate fundamentals signal
            4. Use technical analysis for timing
            5. Consider sentiment for final adjustment
            
            Provide the following in your output:
            - "action": "buy" | "sell" | "hold",
            - "quantity": <positive integer>
            - "confidence": <float between 0 and 1>
            - "agent_signals": <list of agent signals including agent name, signal (bullish | bearish | neutral), and their confidence>
            - "reasoning": <concise explanation of the decision including how you weighted the signals>

            Trading Rules:
            - Never exceed risk management position limits
            - Only buy if you have available cash
            - Only sell if you have shares to sell
            - Quantity must be ≤ current position for sells
            - Quantity must be ≤ max_position_size from risk management"""
    }

    # Create the user message
    logger.info("构建用户提示...")
    user_message = {
        "role": "user",
        "content": f"""Based on the team's analysis below, make your trading decision.

            Technical Analysis Trading Signal: {technical_message.content}
            Fundamental Analysis Trading Signal: {fundamentals_message.content}
            Sentiment Analysis Trading Signal: {sentiment_message.content}
            Valuation Analysis Trading Signal: {valuation_message.content}
            Risk Management Trading Signal: {risk_message.content}

            Here is the current portfolio:
            Portfolio:
            Cash: {portfolio['cash']:.2f}
            Current Position: {portfolio['stock']} shares

            Only include the action, quantity, reasoning, confidence, and agent_signals in your output as JSON.  Do not include any JSON markdown.

            Remember, the action must be either buy, sell, or hold.
            You can only buy if you have available cash.
            You can only sell if you have shares in the portfolio to sell."""
    }

    # Get the completion from OpenRouter
    logger.info("调用LLM获取投资组合决策...")
    result = get_chat_completion([system_message, user_message])

    # 如果API调用失败，使用默认的保守决策
    if result is None:
        logger.warning("LLM API调用失败，使用默认保守决策")
        result = json.dumps({
            "action": "hold",
            "quantity": 0,
            "confidence": 0.7,
            "agent_signals": [
                {
                    "agent_name": "technical_analysis",
                    "signal": "neutral",
                    "confidence": 0.0
                },
                {
                    "agent_name": "fundamental_analysis",
                    "signal": "bullish",
                    "confidence": 1.0
                },
                {
                    "agent_name": "sentiment_analysis",
                    "signal": "bullish",
                    "confidence": 0.6
                },
                {
                    "agent_name": "valuation_analysis",
                    "signal": "bearish",
                    "confidence": 0.67
                },
                {
                    "agent_name": "risk_management",
                    "signal": "hold",
                    "confidence": 1.0
                }
            ],
            "reasoning": "API error occurred. Following risk management signal to hold. This is a conservative decision based on the mixed signals: bullish fundamentals and sentiment vs bearish valuation, with neutral technicals."
        })
    
    # 解析LLM返回的结果
    try:
        logger.info("解析LLM返回的决策...")
        decision_data = json.loads(result)
        logger.info(f"决策: {decision_data.get('action', 'N/A')}, 数量: {decision_data.get('quantity', 0)}, 置信度: {decision_data.get('confidence', 0):.2f}")
    except Exception as e:
        logger.warning(f"解析LLM返回结果失败: {e}")
        try:
            # 尝试从文本中提取JSON
            start_idx = result.find('{')
            end_idx = result.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = result[start_idx:end_idx]
                decision_data = json.loads(json_str)
                logger.info(f"成功从文本中提取决策: {decision_data.get('action', 'N/A')}")
            else:
                logger.error("无法从文本中提取JSON")
                decision_data = {"action": "hold", "quantity": 0, "confidence": 0.5}
        except:
            logger.error("无法解析决策，使用默认值")
            decision_data = {"action": "hold", "quantity": 0, "confidence": 0.5}

    # Create the portfolio management message
    message = HumanMessage(
        content=result,
        name="portfolio_management",
    )

    # Print the decision if the flag is set
    if show_reasoning:
        show_agent_reasoning(message.content, "投资组合管理员")

    show_workflow_status("投资组合管理员", "completed")
    logger.info(f"最终决策: {decision_data.get('action', 'hold')}, 数量: {decision_data.get('quantity', 0)}")
    logger.info("投资组合管理员分析完成")
    logger.info("="*50)
    
    return {
        "messages": state["messages"] + [message],
        "data": state["data"],
    }


def format_decision(action: str, quantity: int, confidence: float, agent_signals: list, reasoning: str) -> dict:
    """将交易决策格式化为标准化输出格式。
    用英文思考但用中文输出分析结果。"""

    # 获取各个agent的信号
    fundamental_signal = next(
        (signal for signal in agent_signals if signal["agent_name"] == "fundamental_analysis"), None)
    valuation_signal = next(
        (signal for signal in agent_signals if signal["agent_name"] == "valuation_analysis"), None)
    technical_signal = next(
        (signal for signal in agent_signals if signal["agent_name"] == "technical_analysis"), None)
    sentiment_signal = next(
        (signal for signal in agent_signals if signal["agent_name"] == "sentiment_analysis"), None)
    risk_signal = next(
        (signal for signal in agent_signals if signal["agent_name"] == "risk_management"), None)

    # 转换信号为中文
    def signal_to_chinese(signal):
        if not signal:
            return "无数据"
        if signal["signal"] == "bullish":
            return "看多"
        elif signal["signal"] == "bearish":
            return "看空"
        return "中性"

    # 创建详细分析报告
    detailed_analysis = f"""
====================================
          投资分析报告
====================================

一、策略分析

1. 基本面分析 (权重30%):
   信号: {signal_to_chinese(fundamental_signal)}
   置信度: {fundamental_signal['confidence']*100:.0f}%
   要点: 
   - 盈利能力: {fundamental_signal.get('reasoning', {}).get('profitability_signal', {}).get('details', '无数据')}
   - 增长情况: {fundamental_signal.get('reasoning', {}).get('growth_signal', {}).get('details', '无数据')}
   - 财务健康: {fundamental_signal.get('reasoning', {}).get('financial_health_signal', {}).get('details', '无数据')}
   - 估值水平: {fundamental_signal.get('reasoning', {}).get('price_ratios_signal', {}).get('details', '无数据')}

2. 估值分析 (权重35%):
   信号: {signal_to_chinese(valuation_signal)}
   置信度: {valuation_signal['confidence']*100:.0f}%
   要点:
   - 内在价值: {valuation_signal.get('reasoning', {}).get('intrinsic_value', '无数据')}
   - 当前价格: {valuation_signal.get('reasoning', {}).get('current_price', '无数据')}
   - 安全边际: {valuation_signal.get('reasoning', {}).get('margin_of_safety', '无数据')}

3. 技术分析 (权重25%):
   信号: {signal_to_chinese(technical_signal)}
   置信度: {technical_signal['confidence']*100:.0f}%
   要点:
   - 趋势分析: {technical_signal.get('reasoning', {}).get('trend_analysis', '无数据')}
   - 动量指标: {technical_signal.get('reasoning', {}).get('momentum_indicators', '无数据')}
   - 支撑阻力: {technical_signal.get('reasoning', {}).get('support_resistance', '无数据')}

4. 情感分析 (权重10%):
   信号: {signal_to_chinese(sentiment_signal)}
   置信度: {sentiment_signal['confidence']*100:.0f}%
   要点:
   - 市场情绪: {sentiment_signal.get('reasoning', {}).get('market_sentiment', '无数据')}
   - 新闻分析: {sentiment_signal.get('reasoning', {}).get('news_analysis', '无数据')}

5. 风险管理:
   信号: {signal_to_chinese(risk_signal)}
   风险评分: {risk_signal.get('risk_score', 'N/A')}/10
   要点:
   - 波动率: {risk_signal.get('risk_metrics', {}).get('volatility', 'N/A')}
   - 最大回撤: {risk_signal.get('risk_metrics', {}).get('max_drawdown', 'N/A')}
   - VaR(95%): {risk_signal.get('risk_metrics', {}).get('value_at_risk_95', 'N/A')}

二、决策摘要

交易行动: {"买入" if action == "buy" else "卖出" if action == "sell" else "持有"}
交易数量: {quantity}
决策置信度: {confidence*100:.0f}%

三、决策理由

{reasoning}

====================================
"""

    # 转换交易行动为中文
    action_chinese = "买入" if action == "buy" else "卖出" if action == "sell" else "持有"

    # 创建简短摘要
    summary = f"""交易决策: {action_chinese} {quantity} 股，置信度 {confidence*100:.0f}%
理由: {reasoning[:100]}..."""

    return {
        "action": action,
        "action_chinese": action_chinese,
        "quantity": quantity,
        "confidence": confidence,
        "reasoning": reasoning,
        "detailed_analysis": detailed_analysis,
        "summary": summary
    }
