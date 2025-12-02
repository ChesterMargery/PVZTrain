"""
Hook Client
TCP客户端，连接到Hook DLL
"""

import socket
import json
from typing import Optional, Dict
from .protocol import Command, Response


class HookClient:
    """Hook DLL客户端"""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 12345, timeout: float = 5.0):
        """
        初始化客户端
        
        Args:
            host: 服务器地址
            port: 服务器端口
            timeout: 连接超时时间（秒）
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.socket: Optional[socket.socket] = None
        self.connected = False
    
    def connect(self) -> bool:
        """
        连接到Hook DLL
        
        Returns:
            True if successful
        """
        if self.connected:
            return True
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            self.connected = True
            return True
        except Exception as e:
            print(f"Failed to connect to Hook DLL: {e}")
            self.socket = None
            self.connected = False
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        self.connected = False
    
    def _send_command(self, command: str) -> Optional[str]:
        """
        发送命令并接收响应
        
        Args:
            command: 命令字符串
            
        Returns:
            响应字符串，失败返回None
        """
        if not self.connected:
            if not self.connect():
                return None
        
        try:
            # 发送命令
            self.socket.sendall((command + '\n').encode('utf-8'))
            
            # 接收响应
            response = b''
            while True:
                chunk = self.socket.recv(4096)
                if not chunk:
                    break
                response += chunk
                if b'\n' in response:
                    break
            
            return response.decode('utf-8').strip()
        except Exception as e:
            print(f"Command failed: {e}")
            self.disconnect()
            return None
    
    def plant(self, row: int, col: int, plant_type: int) -> bool:
        """
        种植物
        
        Args:
            row: 行（0-5）
            col: 列（0-8）
            plant_type: 植物类型
            
        Returns:
            True if successful
        """
        cmd = f"{Command.PLANT} {row} {col} {plant_type}"
        response = self._send_command(cmd)
        return response and Response.is_success(response)
    
    def shovel(self, row: int, col: int) -> bool:
        """
        铲植物
        
        Args:
            row: 行（0-5）
            col: 列（0-8）
            
        Returns:
            True if successful
        """
        cmd = f"{Command.SHOVEL} {row} {col}"
        response = self._send_command(cmd)
        return response and Response.is_success(response)
    
    def fire_cob(self, x: int, y: int) -> bool:
        """
        发射玉米炮
        
        Args:
            x: 目标X坐标（像素）
            y: 目标Y坐标（像素）
            
        Returns:
            True if successful
        """
        cmd = f"{Command.FIRE} {x} {y}"
        response = self._send_command(cmd)
        return response and Response.is_success(response)
    
    def reset(self) -> bool:
        """
        重置关卡
        
        Returns:
            True if successful
        """
        response = self._send_command(Command.RESET)
        return response and Response.is_success(response)
    
    def enter_game(self, mode: int) -> bool:
        """
        进入游戏模式
        
        Args:
            mode: 游戏模式（13=泳池无尽）
            
        Returns:
            True if successful
        """
        cmd = f"{Command.ENTER} {mode}"
        response = self._send_command(cmd)
        return response and Response.is_success(response)
    
    def choose_card(self, plant_type: int) -> bool:
        """
        选卡
        
        Args:
            plant_type: 植物类型
            
        Returns:
            True if successful
        """
        cmd = f"{Command.CHOOSE} {plant_type}"
        response = self._send_command(cmd)
        return response and Response.is_success(response)
    
    def rock(self) -> bool:
        """
        点击开始游戏按钮
        
        Returns:
            True if successful
        """
        response = self._send_command(Command.ROCK)
        return response and Response.is_success(response)
    
    def back_to_main(self) -> bool:
        """
        返回主菜单
        
        Returns:
            True if successful
        """
        response = self._send_command(Command.BACK)
        return response and Response.is_success(response)
    
    def get_state(self) -> Optional[Dict]:
        """
        获取游戏状态
        
        Returns:
            游戏状态字典，失败返回None
        """
        response = self._send_command(Command.STATE)
        if not response:
            return None
        
        try:
            # 解析JSON响应
            return json.loads(response)
        except json.JSONDecodeError:
            print(f"Failed to parse state: {response}")
            return None
    
    def __enter__(self):
        """Context manager support"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support"""
        self.disconnect()
