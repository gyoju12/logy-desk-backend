import logging
import sys
from typing import Dict, Any

def setup_logging(level: str = "INFO") -> None:
    """
    로깅 설정을 초기화합니다.
    
    Args:
        level: 로깅 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # 로깅 레벨 설정
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # 로깅 포맷 설정
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # 기본 로깅 설정
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
    
    # 특정 로거들의 레벨 조정
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    # 애플리케이션 로거 설정
    app_logger = logging.getLogger("app")
    app_logger.setLevel(log_level)
    
    logging.info(f"Logging initialized with level: {level}")


def get_logger(name: str) -> logging.Logger:
    """
    로거 인스턴스를 반환합니다.
    
    Args:
        name: 로거 이름
        
    Returns:
        logging.Logger: 로거 인스턴스
    """
    return logging.getLogger(name)
