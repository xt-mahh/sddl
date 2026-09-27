"""让 tests/ 直接 import src/ 下的 accounting_service（pytest 从项目根运行）。

SDDL example 的可运行性修复：此前无路径配置，`pytest tests/` 报
ModuleNotFoundError，导致 check_c1_c4.py 的 c3（测试执行）必然失败。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
