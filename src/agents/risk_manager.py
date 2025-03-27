import math

from langchain_core.messages import HumanMessage

from src.agents.state import AgentState, show_agent_reasoning, show_workflow_status
from src.tools.api import prices_to_df
from src.utils.logging_config import setup_logger

import json
import ast

##### Risk Management Agent #####

# 设置日志记录器
logger = setup_logger('risk_manager')


def risk_management_agent(state: AgentState):
    """负责风险管理和风险评估"""
    logger.info("="*50)
    logger.info("开始执行 风险管理员")
    logger.info("="*50)
    show_workflow_status("风险管理员")
    show_reasoning = state["metadata"]["show_reasoning"]
    portfolio = state["data"]["portfolio"]
    data = state["data"]
    
    symbol = state["data"]["ticker"]
    logger.info(f"开始对股票 {symbol} 进行风险评估...")
    logger.info(f"当前投资组合: 现金={portfolio['cash']:.2f}, 持股={portfolio['stock']}")

    prices_df = prices_to_df(data["prices"])
    logger.info(f"获取价格数据，共 {len(prices_df)} 条记录")

    # Fetch debate room message instead of individual analyst messages
    logger.info("获取辩论室结果...")
    debate_message = next(
        msg for msg in state["messages"] if msg.name == "debate_room_agent")

    try:
        logger.info("解析辩论室数据...")
        debate_results = json.loads(debate_message.content)
    except Exception as e:
        logger.warning(f"JSON解析失败，尝试使用ast.literal_eval: {e}")
        debate_results = ast.literal_eval(debate_message.content)

    # 1. Calculate Risk Metrics
    logger.info("开始计算风险指标...")
    returns = prices_df['close'].pct_change().dropna()
    daily_vol = returns.std()
    # Annualized volatility approximation
    volatility = daily_vol * (252 ** 0.5)
    logger.info(f"日波动率: {daily_vol:.4f}, 年化波动率: {volatility:.4f}")

    # 计算波动率的历史分布
    rolling_std = returns.rolling(window=120).std() * (252 ** 0.5)
    volatility_mean = rolling_std.mean()
    volatility_std = rolling_std.std()
    volatility_percentile = (volatility - volatility_mean) / volatility_std
    logger.info(f"波动率均值: {volatility_mean:.4f}, 标准差: {volatility_std:.4f}")
    logger.info(f"当前波动率百分位: {volatility_percentile:.2f} 标准差")

    # Simple historical VaR at 95% confidence
    var_95 = returns.quantile(0.05)
    # 使用60天窗口计算最大回撤
    max_drawdown = (
        prices_df['close'] / prices_df['close'].rolling(window=60).max() - 1).min()
    logger.info(f"95%置信度VaR: {var_95:.4f}, 最大回撤: {max_drawdown:.4f}")

    # 2. Market Risk Assessment
    logger.info("开始市场风险评估...")
    market_risk_score = 0

    # Volatility scoring based on percentile
    if volatility_percentile > 1.5:     # 高于1.5个标准差
        market_risk_score += 2
        logger.info("波动率显著高于历史水平 (+2分)")
    elif volatility_percentile > 1.0:   # 高于1个标准差
        market_risk_score += 1
        logger.info("波动率高于历史水平 (+1分)")
    else:
        logger.info("波动率处于正常水平 (0分)")

    # VaR scoring
    # Note: var_95 is typically negative. The more negative, the worse.
    if var_95 < -0.03:
        market_risk_score += 2
        logger.info("VaR风险较高 (+2分)")
    elif var_95 < -0.02:
        market_risk_score += 1
        logger.info("VaR风险中等 (+1分)")
    else:
        logger.info("VaR风险较低 (0分)")

    # Max Drawdown scoring
    if max_drawdown < -0.20:  # Severe drawdown
        market_risk_score += 2
        logger.info("最大回撤严重 (+2分)")
    elif max_drawdown < -0.10:
        market_risk_score += 1
        logger.info("最大回撤中等 (+1分)")
    else:
        logger.info("最大回撤较小 (0分)")

    # 3. Position Size Limits
    logger.info("计算仓位限制...")
    # Consider total portfolio value, not just cash
    current_stock_value = portfolio['stock'] * prices_df['close'].iloc[-1]
    total_portfolio_value = portfolio['cash'] + current_stock_value
    logger.info(f"当前股票价值: {current_stock_value:.2f}, 总投资组合价值: {total_portfolio_value:.2f}")

    # Start with 25% max position of total portfolio
    base_position_size = total_portfolio_value * 0.25
    logger.info(f"基础仓位大小(25%): {base_position_size:.2f}")

    if market_risk_score >= 4:
        # Reduce position for high risk
        max_position_size = base_position_size * 0.5
        logger.info(f"市场风险高 (得分>={market_risk_score})，仓位减半: {max_position_size:.2f}")
    elif market_risk_score >= 2:
        # Slightly reduce for moderate risk
        max_position_size = base_position_size * 0.75
        logger.info(f"市场风险中等 (得分>={market_risk_score})，仓位减少25%: {max_position_size:.2f}")
    else:
        # Keep base size for low risk
        max_position_size = base_position_size
        logger.info(f"市场风险低 (得分={market_risk_score})，维持基础仓位: {max_position_size:.2f}")

    # 4. Stress Testing
    logger.info("开始压力测试...")
    stress_test_scenarios = {
        "market_crash": -0.20,
        "moderate_decline": -0.10,
        "slight_decline": -0.05
    }

    stress_test_results = {}
    current_position_value = current_stock_value

    for scenario, decline in stress_test_scenarios.items():
        potential_loss = current_position_value * decline
        portfolio_impact = potential_loss / (portfolio['cash'] + current_position_value) if (
            portfolio['cash'] + current_position_value) != 0 else math.nan
        stress_test_results[scenario] = {
            "potential_loss": potential_loss,
            "portfolio_impact": portfolio_impact
        }
        logger.info(f"压力测试 - {scenario}: 潜在损失 {potential_loss:.2f}, 组合影响 {portfolio_impact:.2%}")

    # 5. Risk-Adjusted Signal Analysis
    logger.info("开始风险调整信号分析...")
    # Consider debate room confidence levels
    bull_confidence = debate_results["bull_confidence"]
    bear_confidence = debate_results["bear_confidence"]
    debate_confidence = debate_results["confidence"]
    logger.info(f"辩论室信号: 看多置信度={bull_confidence:.2f}, 看空置信度={bear_confidence:.2f}, 总体置信度={debate_confidence:.2f}")

    # Add to risk score if confidence is low or debate was close
    confidence_diff = abs(bull_confidence - bear_confidence)
    if confidence_diff < 0.1:  # Close debate
        market_risk_score += 1
        logger.info("辩论结果接近 (差异<0.1)，风险分数+1")
    if debate_confidence < 0.3:  # Low overall confidence
        market_risk_score += 1
        logger.info("辩论总体置信度低 (<0.3)，风险分数+1")

    # Cap risk score at 10
    risk_score = min(round(market_risk_score), 10)
    logger.info(f"最终风险分数: {risk_score}/10 (市场风险分数: {market_risk_score})")

    # 6. Generate Trading Action
    logger.info("生成交易行动建议...")
    # Consider debate room signal along with risk assessment
    debate_signal = debate_results["signal"]
    logger.info(f"辩论室信号: {debate_signal}")

    if risk_score >= 9:
        trading_action = "hold"
        logger.info(f"风险分数过高 (>= 9)，建议持有")
    elif risk_score >= 7:
        trading_action = "reduce"
        logger.info(f"风险分数较高 (>= 7)，建议减仓")
    else:
        if debate_signal == "bullish" and debate_confidence > 0.5:
            trading_action = "buy"
            logger.info(f"风险可接受，看多信号强，建议买入")
        elif debate_signal == "bearish" and debate_confidence > 0.5:
            trading_action = "sell"
            logger.info(f"风险可接受，看空信号强，建议卖出")
        else:
            trading_action = "hold"
            logger.info(f"风险可接受，但信号不明确，建议持有")

    message_content = {
        "max_position_size": float(max_position_size),
        "risk_score": risk_score,
        "trading_action": trading_action,
        "risk_metrics": {
            "volatility": float(volatility),
            "value_at_risk_95": float(var_95),
            "max_drawdown": float(max_drawdown),
            "market_risk_score": market_risk_score,
            "stress_test_results": stress_test_results
        },
        "debate_analysis": {
            "bull_confidence": bull_confidence,
            "bear_confidence": bear_confidence,
            "debate_confidence": debate_confidence,
            "debate_signal": debate_signal
        },
        "reasoning": f"Risk Score {risk_score}/10: Market Risk={market_risk_score}, "
                     f"Volatility={volatility:.2%}, VaR={var_95:.2%}, "
                     f"Max Drawdown={max_drawdown:.2%}, Debate Signal={debate_signal}"
    }

    # Create the risk management message
    message = HumanMessage(
        content=json.dumps(message_content),
        name="risk_management_agent",
    )

    if show_reasoning:
        show_agent_reasoning(message_content, "风险管理员")

    show_workflow_status("风险管理员", "completed")
    logger.info("风险管理员分析完成")
    logger.info("="*50)
    
    return {
        "messages": state["messages"] + [message],
        "data": {
            **data,
            "risk_analysis": message_content
        }
    }
