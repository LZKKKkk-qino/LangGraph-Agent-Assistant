import sys
import os

# 获取当前文件路径，并向上回溯两级，精准定位到项目根目录 (GIT)
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# 将根目录插入到 Python 搜索路径的最前面
if root_path not in sys.path:
    sys.path.insert(0, root_path)
from src.mcp_server.mcp_server import my_mcp

if __name__ == '__main__':
    my_mcp.run(transport='stdio')