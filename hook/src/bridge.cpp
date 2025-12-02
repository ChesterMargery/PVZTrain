#include "bridge.h"
#include "game.h"
#include "state.h"
#include <WinSock2.h>
#include <sstream>
#include <vector>
#include <string>

#pragma comment(lib, "ws2_32.lib")

namespace Bridge {

static SOCKET g_serverSocket = INVALID_SOCKET;
static SOCKET g_clientSocket = INVALID_SOCKET;
static bool g_initialized = false;

bool Initialize(int port) {
    if (g_initialized) return true;
    
    // 初始化Winsock
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        return false;
    }
    
    // 创建服务器socket
    g_serverSocket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (g_serverSocket == INVALID_SOCKET) {
        WSACleanup();
        return false;
    }
    
    // 设置为非阻塞模式
    u_long mode = 1;
    ioctlsocket(g_serverSocket, FIONBIO, &mode);
    
    // 绑定端口
    sockaddr_in serverAddr;
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_addr.s_addr = INADDR_ANY;
    serverAddr.sin_port = htons(port);
    
    if (bind(g_serverSocket, (sockaddr*)&serverAddr, sizeof(serverAddr)) == SOCKET_ERROR) {
        closesocket(g_serverSocket);
        WSACleanup();
        return false;
    }
    
    // 监听
    if (listen(g_serverSocket, 1) == SOCKET_ERROR) {
        closesocket(g_serverSocket);
        WSACleanup();
        return false;
    }
    
    g_initialized = true;
    return true;
}

void Shutdown() {
    if (g_clientSocket != INVALID_SOCKET) {
        closesocket(g_clientSocket);
        g_clientSocket = INVALID_SOCKET;
    }
    if (g_serverSocket != INVALID_SOCKET) {
        closesocket(g_serverSocket);
        g_serverSocket = INVALID_SOCKET;
    }
    if (g_initialized) {
        WSACleanup();
        g_initialized = false;
    }
}

static std::string ProcessCommand(const std::string& cmd) {
    std::istringstream iss(cmd);
    std::string command;
    iss >> command;
    
    if (command == "PLANT") {
        int row, col, type;
        if (iss >> row >> col >> type) {
            if (PVZ::PutPlant(row, col, type)) {
                return "OK\n";
            }
        }
        return "ERR Invalid parameters\n";
    }
    else if (command == "SHOVEL") {
        int row, col;
        if (iss >> row >> col) {
            if (PVZ::Shovel(row, col)) {
                return "OK\n";
            }
        }
        return "ERR Invalid parameters\n";
    }
    else if (command == "FIRE") {
        int x, y;
        if (iss >> x >> y) {
            if (PVZ::FireCob(x, y)) {
                return "OK\n";
            }
        }
        return "ERR Invalid parameters\n";
    }
    else if (command == "RESET") {
        if (PVZ::MakeNewBoard()) {
            return "OK\n";
        }
        return "ERR Failed to reset\n";
    }
    else if (command == "ENTER") {
        int mode;
        if (iss >> mode) {
            if (PVZ::EnterGame(mode)) {
                return "OK\n";
            }
        }
        return "ERR Invalid parameters\n";
    }
    else if (command == "CHOOSE") {
        int type;
        if (iss >> type) {
            if (PVZ::ChooseCard(type)) {
                return "OK\n";
            }
        }
        return "ERR Invalid parameters\n";
    }
    else if (command == "ROCK") {
        if (PVZ::Rock()) {
            return "OK\n";
        }
        return "ERR Failed to start\n";
    }
    else if (command == "BACK") {
        if (PVZ::BackToMain()) {
            return "OK\n";
        }
        return "ERR Failed to back\n";
    }
    else if (command == "STATE") {
        std::string state = State::GetGameState();
        return state + "\n";
    }
    
    return "ERR Unknown command\n";
}

void ProcessCommands() {
    if (!g_initialized) return;
    
    // 接受新连接
    if (g_clientSocket == INVALID_SOCKET) {
        g_clientSocket = accept(g_serverSocket, nullptr, nullptr);
        if (g_clientSocket != INVALID_SOCKET) {
            // 设置为非阻塞模式
            u_long mode = 1;
            ioctlsocket(g_clientSocket, FIONBIO, &mode);
        }
    }
    
    // 处理客户端命令
    if (g_clientSocket != INVALID_SOCKET) {
        char buffer[1024];
        int bytesRead = recv(g_clientSocket, buffer, sizeof(buffer) - 1, 0);
        
        if (bytesRead > 0) {
            buffer[bytesRead] = '\0';
            
            // 处理命令（可能包含多个命令，用换行分隔）
            std::string data(buffer);
            size_t pos = 0;
            while ((pos = data.find('\n')) != std::string::npos) {
                std::string cmd = data.substr(0, pos);
                data.erase(0, pos + 1);
                
                if (!cmd.empty() && cmd[cmd.length()-1] == '\r') {
                    cmd.erase(cmd.length()-1);
                }
                
                if (!cmd.empty()) {
                    std::string response = ProcessCommand(cmd);
                    send(g_clientSocket, response.c_str(), response.length(), 0);
                }
            }
        }
        else if (bytesRead == 0 || WSAGetLastError() != WSAEWOULDBLOCK) {
            // 客户端断开连接
            closesocket(g_clientSocket);
            g_clientSocket = INVALID_SOCKET;
        }
    }
}

}  // namespace Bridge
