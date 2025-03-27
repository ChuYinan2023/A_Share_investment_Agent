from langchain_core.messages import HumanMessage
from src.agents.state import AgentState, show_agent_reasoning, show_workflow_status
import json
from src.utils.logging_config import setup_logger

# 设置日志记录
logger = setup_logger('valuation_agent')


def valuation_agent(state: AgentState):
    """负责进行估值分析"""
    logger.info("="*50)
    logger.info("开始执行 估值分析师")
    logger.info("="*50)
    show_workflow_status("估值分析师")
    show_reasoning = state["metadata"]["show_reasoning"]
    data = state["data"]
    metrics = data["financial_metrics"][0]
    current_financial_line_item = data["financial_line_items"][0]
    previous_financial_line_item = data["financial_line_items"][1]
    market_cap = data["market_cap"]
    symbol = data["ticker"]
    
    logger.info(f"正在分析股票: {symbol}")
    logger.info(f"当前市值: {market_cap:,.2f}元")
    logger.info(f"盈利增长率: {metrics['earnings_growth']:.2%}")

    reasoning = {}

    # Calculate working capital change
    logger.info("计算营运资金变化...")
    current_wc = current_financial_line_item.get('working_capital') or 0
    previous_wc = previous_financial_line_item.get('working_capital') or 0
    working_capital_change = current_wc - previous_wc
    logger.info(f"当前营运资金: {current_wc:,.2f}元, 前期营运资金: {previous_wc:,.2f}元")
    logger.info(f"营运资金变化: {working_capital_change:,.2f}元")

    # Owner Earnings Valuation (Buffett Method)
    logger.info("开始进行所有者收益估值(巴菲特方法)...")
    net_income = current_financial_line_item.get('net_income')
    depreciation = current_financial_line_item.get('depreciation_and_amortization')
    capex = current_financial_line_item.get('capital_expenditure')
    
    logger.info(f"净利润: {net_income:,.2f}元")
    logger.info(f"折旧与摊销: {depreciation:,.2f}元")
    logger.info(f"资本支出: {capex:,.2f}元")
    
    owner_earnings_value = calculate_owner_earnings_value(
        net_income=net_income,
        depreciation=depreciation,
        capex=capex,
        working_capital_change=working_capital_change,
        growth_rate=metrics["earnings_growth"],
        required_return=0.15,
        margin_of_safety=0.25
    )
    logger.info(f"所有者收益估值结果: {owner_earnings_value:,.2f}元")

    # DCF Valuation
    logger.info("开始进行现金流折现(DCF)估值...")
    free_cash_flow = current_financial_line_item.get('free_cash_flow')
    logger.info(f"自由现金流: {free_cash_flow:,.2f}元")
    
    dcf_value = calculate_intrinsic_value(
        free_cash_flow=free_cash_flow,
        growth_rate=metrics["earnings_growth"],
        discount_rate=0.10,
        terminal_growth_rate=0.03,
        num_years=5,
    )
    logger.info(f"DCF估值结果: {dcf_value:,.2f}元")

    # Calculate combined valuation gap (average of both methods)
    logger.info("计算估值差距...")
    dcf_gap = (dcf_value - market_cap) / market_cap
    owner_earnings_gap = (owner_earnings_value - market_cap) / market_cap
    valuation_gap = (dcf_gap + owner_earnings_gap) / 2
    
    logger.info(f"DCF估值差距: {dcf_gap:.2%}")
    logger.info(f"所有者收益估值差距: {owner_earnings_gap:.2%}")
    logger.info(f"综合估值差距: {valuation_gap:.2%}")

    logger.info("根据估值差距生成交易信号...")
    if valuation_gap > 0.10:  # Changed from 0.15 to 0.10 (10% undervalued)
        signal = 'bullish'
        logger.info(f"估值信号: 看涨 (低估 {valuation_gap:.2%} > 10%)")
    elif valuation_gap < -0.20:  # Changed from -0.15 to -0.20 (20% overvalued)
        signal = 'bearish'
        logger.info(f"估值信号: 看跌 (高估 {valuation_gap:.2%} < -20%)")
    else:
        signal = 'neutral'
        logger.info(f"估值信号: 中性 (-20% < {valuation_gap:.2%} < 10%)")

    reasoning["dcf_analysis"] = {
        "signal": "bullish" if dcf_gap > 0.10 else "bearish" if dcf_gap < -0.20 else "neutral",
        "details": f"Intrinsic Value: ${dcf_value:,.2f}, Market Cap: ${market_cap:,.2f}, Gap: {dcf_gap:.1%}"
    }

    reasoning["owner_earnings_analysis"] = {
        "signal": "bullish" if owner_earnings_gap > 0.10 else "bearish" if owner_earnings_gap < -0.20 else "neutral",
        "details": f"Owner Earnings Value: ${owner_earnings_value:,.2f}, Market Cap: ${market_cap:,.2f}, Gap: {owner_earnings_gap:.1%}"
    }

    message_content = {
        "signal": signal,
        "confidence": f"{abs(valuation_gap):.0%}",
        "reasoning": reasoning
    }
    
    logger.info(f"估值分析置信度: {abs(valuation_gap):.0%}")

    message = HumanMessage(
        content=json.dumps(message_content),
        name="valuation_agent",
    )

    if show_reasoning:
        show_agent_reasoning(message_content, "估值分析师")

    show_workflow_status("估值分析师", "completed")
    logger.info("估值分析完成")
    logger.info("="*50)
    
    return {
        "messages": [message],
        "data": {
            **data,
            "valuation_analysis": message_content
        }
    }


def calculate_owner_earnings_value(
    net_income: float,
    depreciation: float,
    capex: float,
    working_capital_change: float,
    growth_rate: float = 0.05,
    required_return: float = 0.15,
    margin_of_safety: float = 0.25,
    num_years: int = 5
) -> float:
    """
    使用改进的所有者收益法计算公司价值。

    Args:
        net_income: 净利润
        depreciation: 折旧和摊销
        capex: 资本支出
        working_capital_change: 营运资金变化
        growth_rate: 预期增长率
        required_return: 要求回报率
        margin_of_safety: 安全边际
        num_years: 预测年数

    Returns:
        float: 计算得到的公司价值
    """
    try:
        # 数据有效性检查
        if not all(isinstance(x, (int, float)) for x in [net_income, depreciation, capex, working_capital_change]):
            return 0

        # 计算初始所有者收益
        owner_earnings = (
            net_income +
            depreciation -
            capex -
            working_capital_change
        )

        if owner_earnings <= 0:
            return 0

        # 调整增长率，确保合理性
        growth_rate = min(max(growth_rate, 0), 0.25)  # 限制在0-25%之间

        # 计算预测期收益现值
        future_values = []
        for year in range(1, num_years + 1):
            # 使用递减增长率模型
            year_growth = growth_rate * (1 - year / (2 * num_years))  # 增长率逐年递减
            future_value = owner_earnings * (1 + year_growth) ** year
            discounted_value = future_value / (1 + required_return) ** year
            future_values.append(discounted_value)

        # 计算永续价值
        terminal_growth = min(growth_rate * 0.4, 0.03)  # 永续增长率取增长率的40%或3%的较小值
        terminal_value = (
            future_values[-1] * (1 + terminal_growth)) / (required_return - terminal_growth)
        terminal_value_discounted = terminal_value / \
            (1 + required_return) ** num_years

        # 计算总价值并应用安全边际
        intrinsic_value = sum(future_values) + terminal_value_discounted
        value_with_safety_margin = intrinsic_value * (1 - margin_of_safety)

        return max(value_with_safety_margin, 0)  # 确保不返回负值

    except Exception as e:
        logger.error(f"所有者收益计算错误: {e}")
        return 0


def calculate_intrinsic_value(
    free_cash_flow: float,
    growth_rate: float = 0.05,
    discount_rate: float = 0.10,
    terminal_growth_rate: float = 0.02,
    num_years: int = 5,
) -> float:
    """
    使用改进的DCF方法计算内在价值，考虑增长率和风险因素。

    Args:
        free_cash_flow: 自由现金流
        growth_rate: 预期增长率
        discount_rate: 基础折现率
        terminal_growth_rate: 永续增长率
        num_years: 预测年数

    Returns:
        float: 计算得到的内在价值
    """
    try:
        if not isinstance(free_cash_flow, (int, float)) or free_cash_flow <= 0:
            return 0

        # 调整增长率，确保合理性
        growth_rate = min(max(growth_rate, 0), 0.25)  # 限制在0-25%之间

        # 调整永续增长率，不能超过经济平均增长
        terminal_growth_rate = min(growth_rate * 0.4, 0.03)  # 取增长率的40%或3%的较小值

        # 计算预测期现金流现值
        present_values = []
        for year in range(1, num_years + 1):
            future_cf = free_cash_flow * (1 + growth_rate) ** year
            present_value = future_cf / (1 + discount_rate) ** year
            present_values.append(present_value)

        # 计算永续价值
        terminal_year_cf = free_cash_flow * (1 + growth_rate) ** num_years
        terminal_value = terminal_year_cf * \
            (1 + terminal_growth_rate) / (discount_rate - terminal_growth_rate)
        terminal_present_value = terminal_value / \
            (1 + discount_rate) ** num_years

        # 总价值
        total_value = sum(present_values) + terminal_present_value

        return max(total_value, 0)  # 确保不返回负值

    except Exception as e:
        logger.error(f"DCF计算错误: {e}")
        return 0


def calculate_working_capital_change(
    current_working_capital: float,
    previous_working_capital: float,
) -> float:
    """
    计算两个时期之间的营运资金变化。
    正值表示更多资金被占用在营运资金中（现金流出）。
    负值表示较少资金被占用（现金流入）。

    Args:
        current_working_capital: 当前期间的营运资金
        previous_working_capital: 前一期间的营运资金

    Returns:
        float: 营运资金变化（当前 - 前期）
    """
    return current_working_capital - previous_working_capital
