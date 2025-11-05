import logging

from src.config import Config, get_config


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def setup_logging(config: Config) -> None:
    """
    Setup the logging.
    """
    logging.basicConfig(
        level=config.app.log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    # 关闭APScheduler详细日志
    logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)
    logging.getLogger("apscheduler.executors.threadpool").setLevel(logging.WARNING)
    logging.getLogger("apscheduler.scheduler").setLevel(logging.WARNING)
    
    # 关闭SQLAlchemy Engine详细SQL查询日志
    logging.getLogger("sqlalchemy.engine.Engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    
    # 关闭端点调度器详细日志（减少"Scheduling single test"日志噪音）
    logging.getLogger("src.endpoint.scheduler").setLevel(logging.WARNING)
    
    # 关闭性能测试详细日志（减少多轮测试的DEBUG/WARNING日志噪音）
    logging.getLogger("src.ollama.performance_test").setLevel(logging.WARNING)


setup_logging(get_config())
