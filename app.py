# app.py
import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import json
import os
import sys
import glob

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

# 定义函数用于读取日志文件
def read_agent_logs():
    """读取所有代理的日志文件并返回一个字典"""
    logs_dir = os.path.join(current_dir, 'logs')
    log_files = glob.glob(os.path.join(logs_dir, '*.log'))
    
    # 定义代理的显示顺序
    agent_order = [
        'market_data_agent',
        'technical_analyst',  
        'fundamentals_analyst',  
        'sentiment_agent',  
        'valuation_agent',  
        'researcher_bull_agent',
        'researcher_bear_agent',
        'debate_room',
        'risk_manager',
        'portfolio_manager'
    ]
    
    # 代理名称的中文映射
    agent_names = {
        'market_data_agent': '市场数据分析师',
        'technical_analyst': '技术面分析师',  
        'fundamentals_analyst': '基本面分析师',  
        'sentiment_agent': '舆情分析师',  
        'valuation_agent': '估值分析师',  
        'researcher_bull_agent': '看涨研究员',
        'researcher_bear_agent': '看跌研究员',
        'debate_room': '辩论室',
        'risk_manager': '风险管理员',
        'portfolio_manager': '投资组合管理员'
    }
    
    # 需要排除的日志文件
    exclude_logs = ['agent_state', 'api', 'api_calls']
    
    agent_logs = {}
    
    # 先按照预定义顺序处理日志文件
    for agent in agent_order:
        log_file = os.path.join(logs_dir, f"{agent}.log")
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content.strip():  
                        agent_logs[agent] = {
                            'name': agent_names.get(agent, agent),
                            'content': content
                        }
                        print(f"成功读取日志: {agent}")
            except Exception as e:
                print(f"读取日志文件 {log_file} 时出错: {str(e)}")
    
    # 处理其他可能的日志文件
    for log_file in log_files:
        agent = os.path.basename(log_file).replace('.log', '')
        if agent not in agent_logs and agent not in exclude_logs:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content.strip():  
                        agent_logs[agent] = {
                            'name': agent_names.get(agent, agent),
                            'content': content
                        }
                        print(f"成功读取额外日志: {agent}")
            except Exception as e:
                print(f"读取日志文件 {log_file} 时出错: {str(e)}")
    
    # 按照预定义顺序排序
    ordered_logs = {}
    for agent in agent_order:
        if agent in agent_logs:
            ordered_logs[agent] = agent_logs[agent]
    
    # 添加其他未在预定义顺序中的日志
    for agent, log_data in agent_logs.items():
        if agent not in ordered_logs and agent not in exclude_logs:
            ordered_logs[agent] = log_data
    
    return ordered_logs

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
initial_capital = st.sidebar.number_input("初始资金（元）", min_value=1000.0, value=100000.0, step=10000.0)
initial_position = st.sidebar.number_input("初始持仓数量（股）", min_value=0, value=0, step=100)

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
                
                # 将英文操作转换为中文
                action_map = {
                    "buy": "买入",
                    "sell": "卖出",
                    "hold": "持有",
                    "": "未知"
                }
                
                with col1:
                    st.metric("建议操作", action_map.get(action.lower(), action.upper()))
                with col2:
                    st.metric("交易数量（股）", quantity)
                with col3:
                    st.metric("置信度", f"{confidence*100:.1f}%")
                
                # 显示各个分析师的信号
                st.subheader("分析师信号")
                agent_signals = result_json.get("agent_signals", [])
                
                if agent_signals:
                    # 将信号和代理名称翻译为中文
                    signal_map = {
                        "bullish": "看涨",
                        "bearish": "看跌",
                        "neutral": "中性",
                        "buy": "买入",
                        "sell": "卖出",
                        "hold": "持有"
                    }
                    
                    agent_map = {
                        "Valuation Analysis": "估值分析",
                        "Fundamental Analysis": "基本面分析",
                        "Technical Analysis": "技术面分析",
                        "Technical Analyst": "技术分析",
                        "Sentiment Analysis": "舆情分析",
                        "Risk Management": "风险管理",
                        "Market Data Analysis": "市场数据分析",
                        "Debate Room": "辩论室",
                        "Bull Researcher": "多头研究员",
                        "Bear Researcher": "空头研究员",
                        "Portfolio Manager": "投资组合管理",
                        "Risk Manager": "风险管理员"
                    }
                    
                    # 转换DataFrame中的英文为中文
                    signal_df = pd.DataFrame(agent_signals)
                    
                    # 重命名列
                    if 'agent' in signal_df.columns:
                        signal_df = signal_df.rename(columns={
                            'agent': '分析师',
                            'signal': '信号',
                            'confidence': '置信度'
                        })
                    
                    # 转换分析师名称和信号为中文
                    if '分析师' in signal_df.columns:
                        signal_df['分析师'] = signal_df['分析师'].apply(lambda x: agent_map.get(x, x) if isinstance(x, str) else x)
                    
                    if '信号' in signal_df.columns:
                        signal_df['信号'] = signal_df['信号'].apply(lambda x: signal_map.get(x.lower(), x) if isinstance(x, str) else x)
                    
                    # 如果置信度是小数，转换为百分比格式
                    if '置信度' in signal_df.columns:
                        signal_df['置信度'] = signal_df['置信度'].apply(lambda x: f"{x*100:.1f}%" if isinstance(x, (int, float)) and x <= 1 else x)
                    
                    # 打印调试信息，查看转换后的数据
                    print("转换后的分析师信号表格:")
                    print(signal_df)
                    
                    st.dataframe(signal_df, use_container_width=True)
                
                # 显示分析推理
                if "reasoning" in result_json:
                    st.subheader("分析推理")
                    
                    # 获取英文原文
                    english_reasoning = result_json["reasoning"]
                    
                    # 使用LLM API进行翻译
                    try:
                        # 构建翻译提示
                        translation_prompt = [
                            {"role": "system", "content": "你是一个专业的金融翻译专家。请将以下英文金融分析内容翻译成流畅的中文。保持专业术语的准确性，同时确保翻译后的内容通俗易懂。只返回翻译结果，不要添加任何解释或额外内容。"},
                            {"role": "user", "content": f"请将以下金融分析内容从英文翻译成中文：\n\n{english_reasoning}"}
                        ]
                        
                        # 调用LLM API进行翻译
                        from src.tools.openrouter_config import get_chat_completion
                        chinese_reasoning = get_chat_completion(translation_prompt)
                        
                        if not chinese_reasoning:
                            # 如果翻译失败，使用原文
                            chinese_reasoning = "翻译失败，请查看英文原文。"
                            st.warning("无法获取中文翻译，请查看英文原文。")
                    except Exception as e:
                        chinese_reasoning = "翻译过程中出现错误，请查看英文原文。"
                        st.error(f"翻译错误: {str(e)}")
                    
                    # 创建双语显示
                    st.markdown(f"```\n{chinese_reasoning}\n```")
                    st.markdown(f"```\n{english_reasoning}\n```")
                
                # 显示完整 JSON
                with st.expander("查看完整分析结果"):
                    st.json(result_json)
                
                # 添加分析师分析过程展示区域
                st.subheader("所有分析师分析过程")
                agent_logs = read_agent_logs()
                
                if agent_logs:
                    # 使用tabs代替嵌套expander
                    agent_names = [log_data['name'] for agent, log_data in agent_logs.items()]
                    tabs = st.tabs(agent_names)
                    
                    for i, (agent, log_data) in enumerate(agent_logs.items()):
                        with tabs[i]:
                            st.code(log_data['content'], language="text")
                else:
                    st.info("未找到分析师日志记录")
                    
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
                
                # 添加分析师分析过程展示区域
                st.subheader("展现所有分析师分析过程")
                agent_logs = read_agent_logs()
                
                if agent_logs:
                    # 使用tabs代替嵌套expander
                    agent_names = [log_data['name'] for agent, log_data in agent_logs.items()]
                    tabs = st.tabs(agent_names)
                    
                    for i, (agent, log_data) in enumerate(agent_logs.items()):
                        with tabs[i]:
                            st.code(log_data['content'], language="text")
                else:
                    st.info("未找到分析师日志记录")
                
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