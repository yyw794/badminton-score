#!/usr/bin/env python3
"""
快速测试脚本 - 验证优先排阵功能
"""

from test_priority_comprehensive import run_all_tests

if __name__ == "__main__":
    exit_code = run_all_tests()
    
    if exit_code == 0:
        print("\n✅ 测试完成，可以正常使用")
    else:
        print("\n❌ 测试失败，请检查代码")
    
    exit(exit_code)
