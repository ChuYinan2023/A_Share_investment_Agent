from langchain_core.messages import HumanMessage
from src.tools.openrouter_config import get_chat_completion
from src.agents.state import AgentState, show_agent_reasoning, show_workflow_status
from src.tools.api import get_financial_metrics, get_financial_statements, get_market_data, get_price_history
from src.utils.logging_config import setup_logger

from datetime import datetime, timedelta
import pandas as pd
import json

# 设置日志记录
logger = setup_logger('market_data_agent')


def market_data_agent(state: AgentState):
    """Responsible for gathering and preprocessing market data"""
    logger.info("="*50)
    logger.info("开始执行 Market Data Agent")
    logger.info("="*50)
    show_workflow_status("Market Data Agent")
    show_reasoning = state["metadata"]["show_reasoning"]

    messages = state["messages"]
    data = state["data"]

    # 记录输入数据
    logger.info(f"输入数据概览:")
    logger.info(f"- 股票代码: {data.get('ticker', 'N/A')}")
    logger.info(f"- 初始资金: {data.get('portfolio', {}).get('cash', 0)}")
    logger.info(f"- 初始持仓: {data.get('portfolio', {}).get('stock', 0)}")
    logger.info(f"- 开始日期: {data.get('start_date', 'N/A')}")
    logger.info(f"- 结束日期: {data.get('end_date', 'N/A')}")
    logger.info(f"- 新闻数量: {data.get('num_of_news', 5)}")
    logger.info(f"- 显示推理过程: {show_reasoning}")

    # Set default dates
    current_date = datetime.now()
    yesterday = current_date - timedelta(days=1)
    end_date = data["end_date"] or yesterday.strftime('%Y-%m-%d')

    # Ensure end_date is not in the future
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
    if end_date_obj > yesterday:
        logger.info(f"结束日期 {end_date} 超过当前日期，已调整为昨天: {yesterday.strftime('%Y-%m-%d')}")
        end_date = yesterday.strftime('%Y-%m-%d')
        end_date_obj = yesterday

    if not data["start_date"]:
        # Calculate 1 year before end_date
        start_date = end_date_obj - timedelta(days=365)  # 默认获取一年的数据
        start_date = start_date.strftime('%Y-%m-%d')
        logger.info(f"未指定开始日期，已设置为结束日期前一年: {start_date}")
    else:
        start_date = data["start_date"]
        logger.info(f"使用指定的开始日期: {start_date}")

    # Get all required data
    ticker = data["ticker"]
    logger.info(f"开始获取 {ticker} 的市场数据...")

    # 获取价格数据并验证
    logger.info(f"正在获取价格历史数据 ({start_date} 至 {end_date})...")
    prices_df = get_price_history(ticker, start_date, end_date)
    if prices_df is None or prices_df.empty:
        logger.warning(f"警告：无法获取{ticker}的价格数据，将使用空数据继续")
        prices_df = pd.DataFrame(
            columns=['close', 'open', 'high', 'low', 'volume'])
    else:
        logger.info(f"成功获取价格数据，共 {len(prices_df)} 条记录")
        logger.info(f"价格范围: {prices_df['close'].min():.2f} - {prices_df['close'].max():.2f}")
        logger.info(f"最新收盘价: {prices_df['close'].iloc[-1]:.2f}")
        logger.info(f"交易量范围: {prices_df['volume'].min()} - {prices_df['volume'].max()}")
        
        # 计算并记录价格变动百分比
        if len(prices_df) > 1:
            first_price = prices_df['close'].iloc[0]
            last_price = prices_df['close'].iloc[-1]
            price_change_pct = (last_price - first_price) / first_price * 100
            logger.info(f"期间价格变动: {price_change_pct:.2f}%")

    # 获取财务指标
    logger.info("正在获取财务指标...")
    try:
        financial_metrics = get_financial_metrics(ticker)
        if isinstance(financial_metrics, dict):
            logger.info(f"成功获取财务指标，包含 {len(financial_metrics)} 个指标")
            # 记录关键财务指标
            key_metrics = ['pe_ratio', 'pb_ratio', 'dividend_yield', 'roe', 'roa']
            for metric in key_metrics:
                if metric in financial_metrics:
                    logger.info(f"- {metric}: {financial_metrics[metric]}")
        elif isinstance(financial_metrics, list) and financial_metrics:
            logger.info(f"成功获取财务指标，包含 {len(financial_metrics)} 条记录")
            if financial_metrics and isinstance(financial_metrics[0], dict):
                # 记录第一条记录的关键指标
                first_metric = financial_metrics[0]
                logger.info(f"最新财务指标:")
                for key, value in first_metric.items():
                    logger.info(f"- {key}: {value}")
        else:
            logger.info(f"财务指标数据结构: {type(financial_metrics)}")
    except Exception as e:
        logger.error(f"获取财务指标失败: {str(e)}")
        financial_metrics = {}

    # 获取财务报表
    logger.info("正在获取财务报表...")
    try:
        financial_line_items = get_financial_statements(ticker)
        if financial_line_items:
            if isinstance(financial_line_items, dict):
                logger.info(f"成功获取财务报表，包含 {len(financial_line_items)} 个项目")
                # 记录资产负债表和利润表的关键项目
                for category, items in financial_line_items.items():
                    logger.info(f"- {category}: {len(items) if isinstance(items, (list, dict)) else '数据可用'}")
            elif isinstance(financial_line_items, list):
                logger.info(f"成功获取财务报表，包含 {len(financial_line_items)} 条记录")
        else:
            logger.info("财务报表数据为空")
    except Exception as e:
        logger.error(f"获取财务报表失败: {str(e)}")
        financial_line_items = {}

    # 获取市场数据
    logger.info("正在获取市场数据...")
    try:
        market_data = get_market_data(ticker)
        logger.info(f"成功获取市场数据")
        # 记录关键市场数据
        logger.info(f"- 市值: {market_data.get('market_cap', 'N/A')}")
        logger.info(f"- 行业: {market_data.get('industry', 'N/A')}")
        logger.info(f"- 板块: {market_data.get('sector', 'N/A')}")
        
        # 记录其他可能有用的市场数据
        for key, value in market_data.items():
            if key not in ['market_cap', 'industry', 'sector']:
                logger.info(f"- {key}: {value}")
    except Exception as e:
        logger.error(f"获取市场数据失败: {str(e)}")
        market_data = {"market_cap": 0}

    # 确保数据格式正确
    if not isinstance(prices_df, pd.DataFrame):
        logger.warning("价格数据不是DataFrame格式，已创建空DataFrame")
        prices_df = pd.DataFrame(
            columns=['close', 'open', 'high', 'low', 'volume'])

    # 转换价格数据为字典格式
    prices_dict = prices_df.to_dict('records')
    logger.info(f"价格数据已转换为字典格式，共 {len(prices_dict)} 条记录")

    # 构建返回数据
    return_data = {
        **data,
        "prices": prices_dict,
        "start_date": start_date,
        "end_date": end_date,
        "financial_metrics": financial_metrics,
        "financial_line_items": financial_line_items,
        "market_cap": market_data.get("market_cap", 0),
        "market_data": market_data,
    }
    
    logger.info("Market Data Agent 数据处理完成")
    logger.info(f"数据概览:")
    logger.info(f"- 价格数据: {len(prices_dict)} 条记录")
    logger.info(f"- 财务指标: {'可用' if financial_metrics else '不可用'}")
    logger.info(f"- 财务报表: {'可用' if financial_line_items else '不可用'}")
    logger.info(f"- 市场数据: {'可用' if market_data else '不可用'}")
    logger.info("="*50)
    
    return {
        "messages": messages,
        "data": return_data
    }
