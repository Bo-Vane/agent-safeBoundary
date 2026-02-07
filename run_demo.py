#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目入口（根目录代码带中文注释）：

这个脚本把“用户指令 -> 需求图 -> 安全边界 -> 授权/拒绝 -> 证据更新 -> 再授权”
串成一个可运行闭环。

运行：
  python run_demo.py
"""
from src.demo_agent.scenario import run_fix_failing_test_scenario

def main():
    run_fix_failing_test_scenario()

if __name__ == "__main__":
    main()
