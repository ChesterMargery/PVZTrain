"""
Logger Module
Provides logging utilities for the PVZ bot
"""

import sys
import time
from typing import Optional, Tuple
from enum import IntEnum


class LogLevel(IntEnum):
    """Log levels"""
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4


class Logger:
    """
    Simple logger for the PVZ bot
    
    Supports different log levels and optional file output.
    """
    
    LEVEL_NAMES = {
        LogLevel.DEBUG: "DEBUG",
        LogLevel.INFO: "INFO",
        LogLevel.WARNING: "WARN",
        LogLevel.ERROR: "ERROR",
        LogLevel.CRITICAL: "CRIT",
    }
    
    LEVEL_COLORS = {
        LogLevel.DEBUG: "\033[36m",  # Cyan
        LogLevel.INFO: "\033[32m",   # Green
        LogLevel.WARNING: "\033[33m", # Yellow
        LogLevel.ERROR: "\033[31m",   # Red
        LogLevel.CRITICAL: "\033[35m", # Magenta
    }
    
    RESET_COLOR = "\033[0m"
    
    def __init__(self, name: str = "PVZ", level: LogLevel = LogLevel.INFO,
                 use_colors: bool = True, file_path: Optional[str] = None):
        self.name = name
        self.level = level
        self.use_colors = use_colors
        self.file_path = file_path
        self._file = None
        
        if file_path:
            self._file = open(file_path, 'a', encoding='utf-8')
    
    def _format_message(self, level: LogLevel, message: str, 
                       include_colors: bool = True) -> str:
        """Format a log message"""
        timestamp = time.strftime("%H:%M:%S")
        level_name = self.LEVEL_NAMES.get(level, "???")
        
        if include_colors and self.use_colors:
            color = self.LEVEL_COLORS.get(level, "")
            return f"{color}[{timestamp}] [{level_name}] [{self.name}] {message}{self.RESET_COLOR}"
        else:
            return f"[{timestamp}] [{level_name}] [{self.name}] {message}"
    
    def _log(self, level: LogLevel, message: str):
        """Internal log method"""
        if level < self.level:
            return
        
        # Console output with colors
        formatted = self._format_message(level, message, include_colors=True)
        print(formatted)
        
        # File output without colors
        if self._file:
            formatted_plain = self._format_message(level, message, include_colors=False)
            self._file.write(formatted_plain + "\n")
            self._file.flush()
    
    def debug(self, message: str):
        """Log debug message"""
        self._log(LogLevel.DEBUG, message)
    
    def info(self, message: str):
        """Log info message"""
        self._log(LogLevel.INFO, message)
    
    def warning(self, message: str):
        """Log warning message"""
        self._log(LogLevel.WARNING, message)
    
    def error(self, message: str):
        """Log error message"""
        self._log(LogLevel.ERROR, message)
    
    def critical(self, message: str):
        """Log critical message"""
        self._log(LogLevel.CRITICAL, message)
    
    def set_level(self, level: LogLevel):
        """Set logging level"""
        self.level = level
    
    def close(self):
        """Close file handle if open"""
        if self._file:
            self._file.close()
            self._file = None
    
    def __del__(self):
        """Clean up on destruction"""
        self.close()


# Global logger instance
_global_logger: Optional[Logger] = None

# Last status snapshot (for deduplication)
_last_status_snapshot: Optional[Tuple[int, int, int, int, int, bool, int, int]] = None
_last_status_time: float = 0.0
_status_interval: float = 3.0  # seconds - force refresh if exceeded


def get_logger(name: str = "PVZ", level: LogLevel = LogLevel.INFO) -> Logger:
    """Get or create a logger instance"""
    global _global_logger
    if _global_logger is None:
        _global_logger = Logger(name, level)
    return _global_logger


def status_line(message: str, end: str = ""):
    """Print a status line (overwrites current line)"""
    sys.stdout.write(f"\r{message}" + " " * 20 + end)
    sys.stdout.flush()


def log_status(wave: int, total_waves: int, sun: int, plants: int,
               zombies: int, llm_calls: int, actions: int,
               llm_busy: bool = False, pending: int = 0) -> None:
    """Log a concise status line only when data changes"""
    global _last_status_snapshot, _last_status_time
    snapshot = (wave, total_waves, sun, plants, zombies, llm_busy, pending, actions)
    now = time.time()
    if (_last_status_snapshot == snapshot and
            (now - _last_status_time) < _status_interval):
        return
    _last_status_snapshot = snapshot
    _last_status_time = now
    llm_state = "busy" if llm_busy else "idle"
    status = ("[STATUS] wave {}/{} | sun {:>4} | plants {:>2} | "
              "zombies {:>2} | llm {} | pending {:>2} | actions {:>3}").format(
                  wave, total_waves, sun, plants, zombies, llm_state, pending, actions)
    print(status)
    # Also write to log file
    if _global_logger and _global_logger._file:
        timestamp = time.strftime("%H:%M:%S")
        _global_logger._file.write(f"[{timestamp}] {status}\n")
        _global_logger._file.flush()


def print_action(action_type: str, plant_name: str, row: int, col: int, 
                 reason: str, success: bool = True):
    """Print action information in plain text"""
    status = "OK" if success else "FAIL"
    msg1 = f"\n[ACTION] {status} {action_type} {plant_name} -> ({row}, {col})"
    msg2 = f"          reason: {reason}" if reason else ""
    print(msg1)
    if msg2:
        print(msg2)
    # Also write to log file
    if _global_logger and _global_logger._file:
        _global_logger._file.write(msg1 + "\n")
        if msg2:
            _global_logger._file.write(msg2 + "\n")
        _global_logger._file.flush()


def print_llm_response(plan: str, action_count: int):
    """Print LLM response summary without emojis"""
    msg1 = f"\n[LLM] {plan}"
    msg2 = f"       queued actions: {action_count}" if action_count > 0 else ""
    print(msg1)
    if msg2:
        print(msg2)
    # Also write to log file
    if _global_logger and _global_logger._file:
        _global_logger._file.write(msg1 + "\n")
        if msg2:
            _global_logger._file.write(msg2 + "\n")
        _global_logger._file.flush()
