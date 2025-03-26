# app.py
import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import json
import os
import sys

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 导入您的现有功能
from src.main import run_hedge_fund

st.set_page_config(
    page_title="A股投资分析代理",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("A股投资分析代理")
st.sidebar.image("https://img.alicdn.com/imgextra/i4/O1CN01cVW8Ju1nQ9Q1HQxzQ_!!6000000005079-2-tps-512-512.png", width=100)
st.sidebar.title("配置参数")

# 用户输入
ticker = st.sidebar.text_input("股票代码", "601318")

# 日期选择
today = datetime.now()
yesterday = today - timedelta(days=1)
default_end_date = yesterday
default_start_date = yesterday - timedelta(days=365)

start_date = st.sidebar.date_input("开始日期", default_start_date, max_value=yesterday)
end_date = st.sidebar.date_input("结束日期", default_end_date, max_value=yesterday)

# 其他参数
initial_capital = st.sidebar.number_input("初始资金", min_value=1000.0, value=100000.0, step=10000.0)
initial_position = st.sidebar.number_input("初始持仓数量", min_value=0, value=0, step=100)

num_of_news = st.sidebar.slider("分析的新闻数量", min_value=1, max_value=20, value=5)
show_reasoning = st.sidebar.checkbox("显示分析推理过程")

# 执行分析
if st.sidebar.button("开始分析", type="primary"):
    with st.spinner("正在分析中，这可能需要几分钟时间..."):
        portfolio = {
            "cash": initial_capital,
            "stock": initial_position
        }
        
        try:
            result = run_hedge_fund(
                ticker=ticker,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                portfolio=portfolio,
                show_reasoning=show_reasoning,
                num_of_news=num_of_news
            )
            
            # 显示结果
            st.success("分析完成！")
            
            # 预处理结果，移除可能的markdown代码块标记
            if result.startswith("```json"):
                result = result.replace("```json", "", 1)
            if result.endswith("```"):
                result = result[:-3]
            result = result.strip()
            
            try:
                # 尝试解析为JSON
                result_json = json.loads(result)
                
                # 创建结果展示区
                col1, col2, col3 = st.columns(3)
                
                # 显示建议操作
                action = result_json.get("action", "")
                quantity = result_json.get("quantity", 0)
                confidence = result_json.get("confidence", 0)
                
                with col1:
                    st.metric("建议操作", action.upper())
                with col2:
                    st.metric("交易数量", quantity)
                with col3:
                    st.metric("置信度", f"{confidence*100:.1f}%")
                
                # 显示各个分析师的信号
                st.subheader("分析师信号")
                agent_signals = result_json.get("agent_signals", [])
                
                if agent_signals:
                    signal_df = pd.DataFrame(agent_signals)
                    st.dataframe(signal_df, use_container_width=True)
                
                # 显示分析推理
                if "reasoning" in result_json:
                    st.subheader("分析推理")
                    st.write(result_json["reasoning"])
                
                # 显示完整 JSON
                with st.expander("查看完整分析结果"):
                    st.json(result_json)
                    
            except json.JSONDecodeError:
                # 如果不是JSON格式，直接显示文本结果
                st.subheader("分析结果")
                st.markdown(result)
                
                # 添加结果解释区域
                st.subheader("如何使用本工具")
                st.markdown("""
                1. 在侧边栏输入股票代码（如：601318 为中国平安）
                2. 选择分析的时间范围
                3. 设置初始资金和持仓
                4. 点击"开始分析"按钮
                5. 查看系统生成的投资建议
                """)
                
                # 添加分析结果说明
                st.subheader("分析结果说明")
                st.markdown("""
                - 投资建议：买入（Buy）、卖出（Sell）、持有（Hold）
                - 交易量：建议交易的股票数量
                - 置信度：分析师对此建议的置信程度
                """)
                
                # 添加分析师信号说明
                st.subheader("分析师信号说明")
                st.markdown("""
                - Market Data Analysis：提供市场数据和技术指标
                - Fundamental Analysis：基于财务指标，提供基本面分析
                - Sentiment Analysis：基于市场情绪，提供情绪分析
                - Valuation Analysis：估值分析，提供价值投资视角
                - Risk Management：风险管理，评估投资风险
                """)
                
        except Exception as e:
            st.error(f"分析过程中出现错误: {str(e)}")

# 添加使用说明
with st.expander("使用说明"):
    st.markdown("""
    ### 如何使用本工具
    
    1. 在侧边栏输入股票代码（例如：601318 为中国平安）
    2. 选择分析的时间范围
    3. 设置初始资金和持仓
    4. 点击"开始分析"按钮
    5. 等待分析完成后查看结果
    
    ### 分析结果说明
    
    - **建议操作**：buy（买入）、sell（卖出）或 hold（持有）
    - **交易数量**：建议交易的股票数量
    - **置信度**：分析结果的可信度，越高越可信
    
    ### 分析师信号说明
    
    - **Technical Analysis**：技术分析，基于价格走势和技术指标
    - **Fundamental Analysis**：基本面分析，基于财务数据
    - **Sentiment Analysis**：情感分析，基于新闻和市场情绪
    - **Valuation Analysis**：估值分析，基于内在价值计算
    - **Risk Management**：风险管理，评估投资风险
    """)

# 添加页脚
st.sidebar.markdown("---")
st.sidebar.caption(" 2025 A股投资分析代理")