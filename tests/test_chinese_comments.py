"""确保项目 Python 源码使用 UTF-8 并保留可读的中文模块说明。"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ChineseCommentTest(unittest.TestCase):
    """中文说明是可维护性约束；复杂逻辑另由具体模块中的局部注释解释。"""

    def test_every_python_module_has_utf8_chinese_docstring(self) -> None:
        paths = sorted(
            path
            for folder in ("safemem", "scripts", "experiments", "tests")
            for path in (ROOT / folder).rglob("*.py")
        )
        self.assertTrue(paths)
        for path in paths:
            text = path.read_text(encoding="utf-8")
            module = ast.parse(text, filename=str(path))
            docstring = ast.get_docstring(module) or ""
            self.assertTrue(any("\u4e00" <= char <= "\u9fff" for char in docstring), path)


if __name__ == "__main__":
    unittest.main()
