#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path


NAMES = ("周岚", "陈屿", "顾言", "苏遥", "程野", "许川", "叶宁", "沈禾")
MODULES = ("供能", "通信", "温控", "导航", "仓储", "净水", "照明", "气象")


def build_fixture() -> str:
    lines = [
        "# 北辰基地第七码头巡检档案",
        "",
        "以下共有 110 条按时间排列的档案。巡检编号、临时读数和草案内容都是干扰信息；问题只认明确写有“正式”“最终”或“已确认”的事实。资料没有写到的内容必须回答“未提及”。",
        "",
    ]

    for index in range(1, 111):
        name = NAMES[index % len(NAMES)]
        module = MODULES[index % len(MODULES)]
        reading = 20 + (index * 7) % 61
        code = f"R-{index:03d}-{(index * 37) % 997:03d}"
        entry = (
            f"记录 {index:03d}｜{name}完成{module}模块例行巡检，临时读数为{reading}，"
            f"巡检编号{code}。设备自检通过，备用线路保持待命；本条编号不是项目代号或最终校验码。"
        )

        if index == 6:
            entry += " 项目委员会正式确认：本次行动的项目代号是“苍鹭”；此前草案中的“雨燕”已经作废。"
        elif index == 47:
            entry += " 温控复核最终确认：冷却阀批准人为林澈，温度上限为37摄氏度；周岚与41摄氏度仅属旧草案。"
        elif index == 23:
            entry += " 供能清点的正式数据：A区可用电池为17组。"
        elif index == 68:
            entry += " 供能清点的正式数据：C区可用电池为29组。"
        elif index == 92:
            entry += " 仓储主管最终确认：货舱开封口令是“松针-4821”，旧口令“海盐-2046”立即失效。"
        elif index == 101:
            entry += " 供能清点的正式数据：独立备用电池为6组；计算总数时需与A区和C区相加。"
        elif index == 110:
            entry += " 档案封存时已确认：全卷最终校验码为“K9-M2-731”，其他记录中的R编号都不是答案。"

        lines.extend((entry, ""))

    lines.extend(
        (
            "# 问题",
            "",
            "只依据以上档案回答。请严格输出一个 JSON 对象，不要添加解释或代码围栏。键名必须固定为：project_code、approver、temperature_limit_c、cargo_password、checksum、battery_total、roof_color。温度和电池总数使用整数，其他值使用字符串。",
            "",
            "1. 正式项目代号是什么？",
            "2. 冷却阀最终批准人是谁？",
            "3. 最终温度上限是多少摄氏度？",
            "4. 货舱最终开封口令是什么？",
            "5. 全卷最终校验码是什么？",
            "6. A区、C区与独立备用电池合计多少组？",
            "7. 基地屋顶是什么颜色？资料没有写明时回答“未提及”。",
            "",
        )
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_fixture(), encoding="utf-8")


if __name__ == "__main__":
    main()
