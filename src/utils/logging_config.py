import os
import time
import logging
from typing import Optional


def clean_all_log_files(log_dir: Optional[str] = None) -> None:
    """清空所有代理的日志文件

    Args:
        log_dir: 日志文件目录，如果为None则使用默认的logs目录
    """
    if log_dir is None:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))), 'logs')
    
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
        return
    
    # 定义需要清理的代理日志文件列表
    agent_logs = [
        'market_data_agent.log',
        'technical_analyst.log',  # 修正为实际的日志记录器名称
        'fundamentals_agent.log',  # 修正为实际的日志记录器名称
        'sentiment_agent.log',  # 修正为实际的日志记录器名称
        'valuation_agent.log',  # 修正为实际的日志记录器名称
        'researcher_bull_agent.log',
        'researcher_bear_agent.log',
        'debate_room.log',
        'risk_manager.log',
        'portfolio_manager.log'
    ]
    
    # 清空每个日志文件
    for log_file in agent_logs:
        file_path = os.path.join(log_dir, log_file)
        if os.path.exists(file_path):
            # 以写入模式打开文件，这会清空文件内容
            with open(file_path, 'w', encoding='utf-8') as f:
                pass  # 不需要写入任何内容，仅清空


def setup_logger(name: str, log_dir: Optional[str] = None, mode: str = 'w') -> logging.Logger:
    """设置统一的日志配置

    Args:
        name: logger的名称
        log_dir: 日志文件目录，如果为None则使用默认的logs目录
        mode: 文件打开模式，'a'为追加，'w'为覆盖

    Returns:
        配置好的logger实例
    """
    # 设置 root logger 的级别为 DEBUG
    logging.getLogger().setLevel(logging.DEBUG)

    # 获取或创建 logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # logger本身记录DEBUG级别及以上
    logger.propagate = False  # 防止日志消息传播到父级logger

    # 如果已经有处理器，先移除它们
    if logger.handlers:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)  # 控制台只显示INFO及以上级别

    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)

    # 创建文件处理器
    if log_dir is None:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{name}.log")
    file_handler = logging.FileHandler(log_file, mode=mode, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)  # 文件记录DEBUG级别及以上的日志
    file_handler.setFormatter(formatter)

    # 添加处理器到日志记录器
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


# 预定义的图标
SUCCESS_ICON = "✓"
ERROR_ICON = "✗"
WAIT_ICON = "🔄"
