#!/usr/bin/env python3
"""
环境自动配置工具

功能:
1. 自动切换 pip 到国内镜像源
2. 自动安装所有依赖包
3. 检查 CUDA/PyTorch 配置

使用方法:
    python setup_env.py           # 自动配置环境
    python setup_env.py --check   # 只检查环境，不安装
    python setup_env.py --mirror  # 只切换镜像源
"""

import subprocess
import sys
import os
import platform

# 国内 pip 镜像源
MIRRORS = {
    "aliyun": "https://mirrors.aliyun.com/pypi/simple/",
    "tsinghua": "https://pypi.tuna.tsinghua.edu.cn/simple/",
    "ustc": "https://pypi.mirrors.ustc.edu.cn/simple/",
    "douban": "https://pypi.doubanio.com/simple/",
    "huawei": "https://repo.huaweicloud.com/repository/pypi/simple/",
}

# 默认使用阿里云 (速度快且稳定)
DEFAULT_MIRROR = "aliyun"

# 必需的依赖包
REQUIRED_PACKAGES = [
    "numpy",
    "gymnasium",
    "stable-baselines3",
    "torch",
    "pymem",
]


def run_cmd(cmd: list, capture=False) -> tuple:
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            check=False,
        )
        return result.returncode == 0, result.stdout if capture else ""
    except Exception as e:
        return False, str(e)


def get_pip_cmd():
    """获取 pip 命令"""
    return [sys.executable, "-m", "pip"]


def set_pip_mirror(mirror_name: str = DEFAULT_MIRROR) -> bool:
    """
    设置 pip 国内镜像源
    
    Args:
        mirror_name: 镜像名称 (aliyun, tsinghua, ustc, douban, huawei)
    
    Returns:
        是否成功
    """
    if mirror_name not in MIRRORS:
        print(f"❌ 未知镜像: {mirror_name}")
        print(f"   可用镜像: {', '.join(MIRRORS.keys())}")
        return False
    
    mirror_url = MIRRORS[mirror_name]
    trusted_host = mirror_url.split("//")[1].split("/")[0]
    
    print(f"🔄 正在切换 pip 镜像源到 {mirror_name}...")
    print(f"   URL: {mirror_url}")
    
    # 设置全局镜像
    cmd = get_pip_cmd() + [
        "config", "set", "global.index-url", mirror_url
    ]
    success, _ = run_cmd(cmd)
    
    if success:
        # 设置信任主机
        cmd = get_pip_cmd() + [
            "config", "set", "global.trusted-host", trusted_host
        ]
        run_cmd(cmd)
        print(f"✅ pip 镜像源已切换到 {mirror_name}")
        return True
    else:
        print(f"❌ 切换失败，尝试手动设置...")
        # 备选方案：创建 pip.ini
        return set_pip_mirror_manual(mirror_url, trusted_host)


def set_pip_mirror_manual(mirror_url: str, trusted_host: str) -> bool:
    """手动创建 pip 配置文件"""
    if platform.system() == "Windows":
        pip_dir = os.path.join(os.environ.get("APPDATA", ""), "pip")
        pip_file = os.path.join(pip_dir, "pip.ini")
    else:
        pip_dir = os.path.expanduser("~/.pip")
        pip_file = os.path.join(pip_dir, "pip.conf")
    
    try:
        os.makedirs(pip_dir, exist_ok=True)
        
        config_content = f"""[global]
index-url = {mirror_url}
trusted-host = {trusted_host}
timeout = 120
"""
        with open(pip_file, "w", encoding="utf-8") as f:
            f.write(config_content)
        
        print(f"✅ 已创建配置文件: {pip_file}")
        return True
    except Exception as e:
        print(f"❌ 创建配置文件失败: {e}")
        return False


def check_package(package_name: str) -> tuple:
    """
    检查包是否已安装
    
    Returns:
        (已安装, 版本号)
    """
    cmd = get_pip_cmd() + ["show", package_name]
    success, output = run_cmd(cmd, capture=True)
    
    if success and output:
        for line in output.split("\n"):
            if line.startswith("Version:"):
                version = line.split(":")[1].strip()
                return True, version
    return False, ""


def install_package(package_name: str, upgrade: bool = False) -> bool:
    """安装单个包"""
    cmd = get_pip_cmd() + ["install"]
    if upgrade:
        cmd.append("--upgrade")
    cmd.append(package_name)
    
    print(f"   📦 安装 {package_name}...")
    success, _ = run_cmd(cmd)
    return success


def install_requirements(requirements_file: str = "requirements.txt") -> bool:
    """从 requirements.txt 安装依赖"""
    if not os.path.exists(requirements_file):
        print(f"⚠️ 未找到 {requirements_file}")
        return False
    
    cmd = get_pip_cmd() + ["install", "-r", requirements_file]
    print(f"📦 正在安装依赖 ({requirements_file})...")
    success, _ = run_cmd(cmd)
    return success


def check_cuda() -> tuple:
    """检查 CUDA 和 PyTorch GPU 支持"""
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            cuda_version = torch.version.cuda
            device_name = torch.cuda.get_device_name(0)
            return True, f"CUDA {cuda_version} - {device_name}"
        else:
            return False, "CUDA 不可用 (将使用 CPU 训练)"
    except ImportError:
        return False, "PyTorch 未安装"


def check_environment() -> dict:
    """
    检查完整环境状态
    
    Returns:
        环境状态字典
    """
    print("\n" + "=" * 50)
    print("🔍 环境检查")
    print("=" * 50)
    
    status = {
        "python": sys.version.split()[0],
        "platform": platform.system(),
        "packages": {},
        "cuda": None,
    }
    
    print(f"\n📌 Python 版本: {status['python']}")
    print(f"📌 操作系统: {status['platform']}")
    
    # 检查包
    print(f"\n📦 依赖包状态:")
    all_installed = True
    for pkg in REQUIRED_PACKAGES:
        installed, version = check_package(pkg)
        status["packages"][pkg] = {"installed": installed, "version": version}
        
        if installed:
            print(f"   ✅ {pkg}: {version}")
        else:
            print(f"   ❌ {pkg}: 未安装")
            all_installed = False
    
    # 检查 CUDA
    if status["packages"].get("torch", {}).get("installed"):
        cuda_ok, cuda_info = check_cuda()
        status["cuda"] = cuda_info
        if cuda_ok:
            print(f"\n🎮 GPU: {cuda_info}")
        else:
            print(f"\n⚠️ GPU: {cuda_info}")
    
    print("\n" + "=" * 50)
    
    if all_installed:
        print("✅ 所有依赖已安装!")
    else:
        print("⚠️ 部分依赖缺失，请运行: python setup_env.py")
    
    print("=" * 50 + "\n")
    
    return status


def auto_setup(mirror: str = DEFAULT_MIRROR) -> bool:
    """
    自动配置完整环境
    
    1. 切换国内镜像
    2. 升级 pip
    3. 安装依赖
    4. 检查 CUDA
    """
    print("\n" + "=" * 50)
    print("🚀 PVZ RL 训练环境自动配置")
    print("=" * 50)
    
    # Step 1: 切换镜像
    print("\n[1/4] 配置 pip 镜像源...")
    set_pip_mirror(mirror)
    
    # Step 2: 升级 pip
    print("\n[2/4] 升级 pip...")
    run_cmd(get_pip_cmd() + ["install", "--upgrade", "pip"])
    
    # Step 3: 安装依赖
    print("\n[3/4] 安装依赖包...")
    
    # 先尝试 requirements.txt
    script_dir = os.path.dirname(os.path.abspath(__file__))
    req_file = os.path.join(script_dir, "requirements.txt")
    
    if os.path.exists(req_file):
        install_requirements(req_file)
    else:
        # 逐个安装必需包
        for pkg in REQUIRED_PACKAGES:
            installed, _ = check_package(pkg)
            if not installed:
                install_package(pkg)
    
    # Step 4: 验证环境
    print("\n[4/4] 验证环境...")
    status = check_environment()
    
    # 检查关键依赖
    all_ok = all(
        status["packages"].get(pkg, {}).get("installed", False)
        for pkg in REQUIRED_PACKAGES
    )
    
    if all_ok:
        print("🎉 环境配置完成!")
        print("\n📝 下一步:")
        print("   1. 启动 Plants vs Zombies 游戏")
        print("   2. 运行训练: python env/pvz_env.py")
        return True
    else:
        print("⚠️ 部分依赖安装失败，请手动检查")
        return False


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="PVZ RL 环境自动配置")
    parser.add_argument("--check", action="store_true", help="只检查环境，不安装")
    parser.add_argument("--mirror", type=str, default=DEFAULT_MIRROR,
                        choices=list(MIRRORS.keys()),
                        help=f"pip 镜像源 (默认: {DEFAULT_MIRROR})")
    parser.add_argument("--mirror-only", action="store_true", help="只切换镜像源")
    args = parser.parse_args()
    
    if args.check:
        check_environment()
    elif args.mirror_only:
        set_pip_mirror(args.mirror)
    else:
        auto_setup(args.mirror)


if __name__ == "__main__":
    main()
