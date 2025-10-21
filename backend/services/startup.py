"""应用启动初始化服务"""

import logging

from services.auto_trader import schedule_auto_trading
from services.scheduler import start_scheduler, setup_market_tasks

logger = logging.getLogger(__name__)


def initialize_services():
    """初始化所有服务"""
    try:
        # 启动调度器
        start_scheduler()
        logger.info("调度器服务已启动")
        
        # 设置市场相关定时任务
        setup_market_tasks()
        logger.info("市场定时任务已设置")

        # 启动自动加密货币模拟交易任务
        schedule_auto_trading(interval_seconds=5)
        logger.info("自动加密货币交易任务已开启")
        
        logger.info("所有服务初始化完成")
        
    except Exception as e:
        logger.error(f"服务初始化失败: {e}")
        raise


def shutdown_services():
    """关闭所有服务"""
    try:
        from services.scheduler import stop_scheduler
        stop_scheduler()
        logger.info("所有服务已关闭")
        
    except Exception as e:
        logger.error(f"服务关闭失败: {e}")


# 可以在 FastAPI 应用的生命周期事件中调用
async def startup_event():
    """FastAPI 应用启动事件"""
    initialize_services()


async def shutdown_event():
    """FastAPI 应用关闭事件"""
    shutdown_services()