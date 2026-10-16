"""Compute IP assessment scores from a JSON object on stdin; no file writes."""

import json
import sys


DIMENSIONS = {
    "定位": ["P1", "P2", "P3"],
    "人群": ["A1", "A2", "A3"],
    "产品": ["O1", "O2", "O3"],
    "内容": ["C1", "C2", "C3"],
    "信任": ["T1", "T2", "T3", "T4"],
    "咨询路径": ["J1", "J2"],
    "复盘": ["R1", "R2"],
}
CRITICAL = {"定位", "产品", "信任", "咨询路径"}
GRADES = [
    (90, "完整度高，有持续验证记录"),
    (75, "较完整，优先修补薄弱环节"),
    (60, "基本成形，仍需补证与验证"),
    (40, "已有雏形，关键缺口较多"),
    (0, "基础待建立"),
]


def score(answers):
    ids = [item for items in DIMENSIONS.values() for item in items]
    if not isinstance(answers, dict):
        raise ValueError("输入必须是检查项 ID 到分数的 JSON 对象")
    unknown = set(answers) - set(ids)
    if unknown:
        raise ValueError("未知检查项: " + ", ".join(sorted(unknown)))
    for key, value in answers.items():
        if value is not None and (type(value) is not int or not 0 <= value <= 5):
            raise ValueError(f"{key}: 分数必须是 0—5 的整数或 null")

    dimensions = []
    for name, items in DIMENSIONS.items():
        values = [answers.get(item) for item in items]
        pending = [item for item in items if answers.get(item) is None]
        low = sum(value for value in values if value is not None)
        high = low + 5 * len(pending)
        maximum = 5 * len(items)
        weak = high / maximum < 0.6
        dimensions.append({
            "name": name, "max": maximum,
            "score": low if not pending else None,
            "range": [low, high], "pending": pending,
            "weakness": "已确认" if weak else ("待确认" if pending else "未触发"),
            "critical_gap": weak and name in CRITICAL,
        })

    pending = [item for item in ids if answers.get(item) is None]
    low = sum(row["range"][0] for row in dimensions)
    high = low + 5 * len(pending)
    grade = next(label for threshold, label in GRADES if low >= threshold)
    priorities = [row for row in dimensions if row["weakness"] == "已确认"]
    priorities.sort(key=lambda row: (
        not row["critical_gap"], row["range"][1] / row["max"]
    ))
    return {
        "rubric_version": "1.0", "complete": not pending,
        "total": low if not pending else None,
        "range": [low, high], "grade": grade if not pending else None,
        "assessed_count": 20 - len(pending), "item_count": 20,
        "coverage_percent": (20 - len(pending)) * 5,
        "pending": pending, "dimensions": dimensions,
        "priority_dimensions": [row["name"] for row in priorities],
    }


if __name__ == "__main__":
    try:
        result = score(json.load(sys.stdin))
    except (ValueError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
    print(json.dumps(result, ensure_ascii=False, indent=2))
