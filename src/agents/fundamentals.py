from langchain_core.messages import HumanMessage

from src.agents.state import AgentState, show_agent_reasoning, show_workflow_status
from src.utils.logging_config import setup_logger

import json

# 设置日志记录
logger = setup_logger('fundamentals_analyst')

##### Fundamental Agent #####


def fundamentals_agent(state: AgentState):
    """负责进行基本面分析"""
    logger.info("="*50)
    logger.info("开始执行 基本面分析师")
    logger.info("="*50)
    show_workflow_status("基本面分析师")
    show_reasoning = state["metadata"]["show_reasoning"]
    data = state["data"]
    metrics = data["financial_metrics"][0]
    
    # 记录输入数据
    ticker = data.get("ticker", "未知")
    logger.info(f"开始对 {ticker} 进行基本面分析...")
    
    # 记录可用的财务指标
    available_metrics = [key for key in metrics.keys() if metrics.get(key) is not None]
    logger.info(f"可用财务指标数量: {len(available_metrics)}")
    logger.info(f"主要财务指标概览:")
    
    # 显示一些关键指标
    key_metrics = ["pe_ratio", "price_to_book", "return_on_equity", "debt_to_equity", 
                  "current_ratio", "revenue_growth", "earnings_growth"]
    for metric in key_metrics:
        value = metrics.get(metric)
        if value is not None:
            if "ratio" in metric or "to_" in metric or "debt_to_equity" == metric:
                logger.info(f"- {metric}: {value:.2f}")
            elif "growth" in metric or "return" in metric or "margin" in metric:
                logger.info(f"- {metric}: {value:.2%}")
            else:
                logger.info(f"- {metric}: {value}")
        else:
            logger.info(f"- {metric}: 数据不可用")

    # Initialize signals list for different fundamental aspects
    signals = []
    reasoning = {}
    
    logger.info("开始分析各项基本面指标...")

    # 1. Profitability Analysis
    logger.info("1. 分析盈利能力...")
    return_on_equity = metrics.get("return_on_equity", 0)
    net_margin = metrics.get("net_margin", 0)
    operating_margin = metrics.get("operating_margin", 0)

    thresholds = [
        (return_on_equity, 0.15),  # Strong ROE above 15%
        (net_margin, 0.20),  # Healthy profit margins
        (operating_margin, 0.15)  # Strong operating efficiency
    ]
    profitability_score = sum(
        metric is not None and metric > threshold
        for metric, threshold in thresholds
    )
    
    logger.info(f"盈利能力指标:")
    logger.info(f"- 股本回报率(ROE): {return_on_equity:.2%}" if return_on_equity is not None else "- 股本回报率(ROE): 数据不可用")
    logger.info(f"- 净利润率: {net_margin:.2%}" if net_margin is not None else "- 净利润率: 数据不可用")
    logger.info(f"- 营业利润率: {operating_margin:.2%}" if operating_margin is not None else "- 营业利润率: 数据不可用")
    logger.info(f"- 盈利能力得分: {profitability_score}/3")

    signals.append('bullish' if profitability_score >=
                   2 else 'bearish' if profitability_score == 0 else 'neutral')
    profitability_signal = signals[0]
    logger.info(f"- 盈利能力信号: {'看涨' if profitability_signal == 'bullish' else '看跌' if profitability_signal == 'bearish' else '中性'}")
    
    reasoning["profitability_signal"] = {
        "signal": signals[0],
        "details": (
            f"ROE: {metrics.get('return_on_equity', 0):.2%}" if metrics.get(
                "return_on_equity") is not None else "ROE: N/A"
        ) + ", " + (
            f"Net Margin: {metrics.get('net_margin', 0):.2%}" if metrics.get(
                "net_margin") is not None else "Net Margin: N/A"
        ) + ", " + (
            f"Op Margin: {metrics.get('operating_margin', 0):.2%}" if metrics.get(
                "operating_margin") is not None else "Op Margin: N/A"
        )
    }

    # 2. Growth Analysis
    logger.info("2. 分析增长能力...")
    revenue_growth = metrics.get("revenue_growth", 0)
    earnings_growth = metrics.get("earnings_growth", 0)
    book_value_growth = metrics.get("book_value_growth", 0)

    thresholds = [
        (revenue_growth, 0.10),  # 10% revenue growth
        (earnings_growth, 0.10),  # 10% earnings growth
        (book_value_growth, 0.10)  # 10% book value growth
    ]
    growth_score = sum(
        metric is not None and metric > threshold
        for metric, threshold in thresholds
    )
    
    logger.info(f"增长能力指标:")
    logger.info(f"- 营收增长率: {revenue_growth:.2%}" if revenue_growth is not None else "- 营收增长率: 数据不可用")
    logger.info(f"- 盈利增长率: {earnings_growth:.2%}" if earnings_growth is not None else "- 盈利增长率: 数据不可用")
    logger.info(f"- 账面价值增长率: {book_value_growth:.2%}" if book_value_growth is not None else "- 账面价值增长率: 数据不可用")
    logger.info(f"- 增长能力得分: {growth_score}/3")

    signals.append('bullish' if growth_score >=
                   2 else 'bearish' if growth_score == 0 else 'neutral')
    growth_signal = signals[1]
    logger.info(f"- 增长能力信号: {'看涨' if growth_signal == 'bullish' else '看跌' if growth_signal == 'bearish' else '中性'}")
    
    reasoning["growth_signal"] = {
        "signal": signals[1],
        "details": (
            f"Revenue Growth: {metrics.get('revenue_growth', 0):.2%}" if metrics.get(
                "revenue_growth") is not None else "Revenue Growth: N/A"
        ) + ", " + (
            f"Earnings Growth: {metrics.get('earnings_growth', 0):.2%}" if metrics.get(
                "earnings_growth") is not None else "Earnings Growth: N/A"
        )
    }

    # 3. Financial Health
    logger.info("3. 分析财务健康度...")
    current_ratio = metrics.get("current_ratio", 0)
    debt_to_equity = metrics.get("debt_to_equity", 0)
    free_cash_flow_per_share = metrics.get("free_cash_flow_per_share", 0)
    earnings_per_share = metrics.get("earnings_per_share", 0)

    health_score = 0
    if current_ratio and current_ratio > 1.5:  # Strong liquidity
        health_score += 1
        logger.info(f"- 流动比率 {current_ratio:.2f} > 1.5 (良好)")
    elif current_ratio:
        logger.info(f"- 流动比率 {current_ratio:.2f} <= 1.5 (不足)")
    else:
        logger.info("- 流动比率: 数据不可用")
        
    if debt_to_equity and debt_to_equity < 0.5:  # Conservative debt levels
        health_score += 1
        logger.info(f"- 负债/权益比 {debt_to_equity:.2f} < 0.5 (良好)")
    elif debt_to_equity:
        logger.info(f"- 负债/权益比 {debt_to_equity:.2f} >= 0.5 (较高)")
    else:
        logger.info("- 负债/权益比: 数据不可用")
        
    if (free_cash_flow_per_share and earnings_per_share and
            free_cash_flow_per_share > earnings_per_share * 0.8):  # Strong FCF conversion
        health_score += 1
        logger.info(f"- 每股自由现金流 {free_cash_flow_per_share:.2f} > 每股收益的80% {earnings_per_share * 0.8:.2f} (良好)")
    elif free_cash_flow_per_share and earnings_per_share:
        logger.info(f"- 每股自由现金流 {free_cash_flow_per_share:.2f} <= 每股收益的80% {earnings_per_share * 0.8:.2f} (不足)")
    else:
        logger.info("- 现金流转换率: 数据不可用")
    
    logger.info(f"- 财务健康度得分: {health_score}/3")

    signals.append('bullish' if health_score >=
                   2 else 'bearish' if health_score == 0 else 'neutral')
    health_signal = signals[2]
    logger.info(f"- 财务健康度信号: {'看涨' if health_signal == 'bullish' else '看跌' if health_signal == 'bearish' else '中性'}")
    
    reasoning["financial_health_signal"] = {
        "signal": signals[2],
        "details": (
            f"Current Ratio: {metrics.get('current_ratio', 0):.2f}" if metrics.get(
                "current_ratio") is not None else "Current Ratio: N/A"
        ) + ", " + (
            f"D/E: {metrics.get('debt_to_equity', 0):.2f}" if metrics.get(
                "debt_to_equity") is not None else "D/E: N/A"
        )
    }

    # 4. Price to X ratios
    logger.info("4. 分析估值比率...")
    pe_ratio = metrics.get("pe_ratio", 0)
    price_to_book = metrics.get("price_to_book", 0)
    price_to_sales = metrics.get("price_to_sales", 0)

    thresholds = [
        (pe_ratio, 25),  # Reasonable P/E ratio
        (price_to_book, 3),  # Reasonable P/B ratio
        (price_to_sales, 5)  # Reasonable P/S ratio
    ]
    price_ratio_score = sum(
        metric is not None and metric < threshold
        for metric, threshold in thresholds
    )
    
    logger.info(f"估值比率指标:")
    logger.info(f"- 市盈率(P/E): {pe_ratio:.2f}" if pe_ratio else "- 市盈率(P/E): 数据不可用")
    logger.info(f"- 市净率(P/B): {price_to_book:.2f}" if price_to_book else "- 市净率(P/B): 数据不可用")
    logger.info(f"- 市销率(P/S): {price_to_sales:.2f}" if price_to_sales else "- 市销率(P/S): 数据不可用")
    logger.info(f"- 估值比率得分: {price_ratio_score}/3")

    signals.append('bullish' if price_ratio_score >=
                   2 else 'bearish' if price_ratio_score == 0 else 'neutral')
    price_ratio_signal = signals[3]
    logger.info(f"- 估值比率信号: {'看涨' if price_ratio_signal == 'bullish' else '看跌' if price_ratio_signal == 'bearish' else '中性'}")
    
    reasoning["price_ratios_signal"] = {
        "signal": signals[3],
        "details": (
            f"P/E: {pe_ratio:.2f}" if pe_ratio else "P/E: N/A"
        ) + ", " + (
            f"P/B: {price_to_book:.2f}" if price_to_book else "P/B: N/A"
        ) + ", " + (
            f"P/S: {price_to_sales:.2f}" if price_to_sales else "P/S: N/A"
        )
    }

    # Determine overall signal
    bullish_signals = signals.count('bullish')
    bearish_signals = signals.count('bearish')
    neutral_signals = signals.count('neutral')
    
    logger.info("综合所有基本面信号...")
    logger.info(f"信号统计: 看涨={bullish_signals}, 看跌={bearish_signals}, 中性={neutral_signals}")

    if bullish_signals > bearish_signals:
        overall_signal = 'bullish'
        logger.info("最终基本面信号: 看涨")
    elif bearish_signals > bullish_signals:
        overall_signal = 'bearish'
        logger.info("最终基本面信号: 看跌")
    else:
        overall_signal = 'neutral'
        logger.info("最终基本面信号: 中性")

    # Calculate confidence level
    total_signals = len(signals)
    confidence = max(bullish_signals, bearish_signals) / total_signals
    logger.info(f"基本面分析置信度: {confidence*100:.2f}%")

    message_content = {
        "signal": overall_signal,
        "confidence": f"{round(confidence * 100)}%",
        "reasoning": reasoning
    }

    # Create the fundamental analysis message
    message = HumanMessage(
        content=json.dumps(message_content),
        name="fundamentals_agent",
    )

    # Print the reasoning if the flag is set
    if show_reasoning:
        show_agent_reasoning(message_content, "基本面分析师")

    show_workflow_status("基本面分析师", "completed")
    logger.info("基本面分析完成")
    logger.info("="*50)
    
    return {
        "messages": [message],
        "data": {
            **data,
            "fundamental_analysis": message_content
        }
    }
