"""
启动TUI界面

启动MathModelAgent终端界面
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))


def main():
    """启动TUI界面"""
    try:
        from tui.app import MathModelAgentTUI
        
        print("启动 MathModelAgent TUI...")
        print("按 Ctrl+C 退出")
        print()
        
        app = MathModelAgentTUI()
        app.run()
        
    except ImportError as e:
        print(f"导入错误: {e}")
        print("请安装依赖: pip install textual rich")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n已退出")
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
