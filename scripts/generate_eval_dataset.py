#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List


SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def first_sentence(text: str) -> str:
    parts = [p.strip() for p in SENTENCE_SPLIT_RE.split(text.strip()) if p.strip()]
    if not parts:
        return text.strip()
    sentence = parts[0]
    if not sentence.endswith((".", "!", "?")):
        sentence += "."
    return sentence


def load_chunks(path: Path) -> List[Dict]:
    rows: List[Dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return sorted(rows, key=lambda r: r["chunk_id"])


def domain_from_department(dept: str) -> str:
    d = (dept or "General").strip()
    return d if d else "General"


def easy_question(chunk: Dict) -> str:
    section = chunk["section_path"].split(" > ")[-1]
    return f"Theo tài liệu '{chunk['title']}', mục '{section}' quy định gì?"


def hard_question(chunk: Dict, idx: int) -> str:
    section = chunk["section_path"].split(" > ")[-1]
    title = chunk["title"]
    dept = (chunk.get("department") or "General").lower()

    templates = {
        "hr": [
            "Trong bối cảnh nhân sự, mục '{section}' trong tài liệu '{title}' áp dụng như thế nào?",
            "Nếu nhân viên cần tra cứu '{section}', nội dung cốt lõi cần tuân thủ là gì theo '{title}'?",
        ],
        "engineering": [
            "Trong vận hành kỹ thuật, tài liệu '{title}' yêu cầu gì ở mục '{section}'?",
            "Theo chuẩn làm việc của đội kỹ thuật, mục '{section}' trong '{title}' được thực hiện ra sao?",
        ],
        "security": [
            "Theo kiểm soát bảo mật nội bộ, mục '{section}' trong '{title}' quy định điều gì quan trọng nhất?",
            "Khi đánh giá tuân thủ an ninh, cần bám theo nội dung nào ở mục '{section}' của '{title}'?",
        ],
        "operations": [
            "Trong quy trình vận hành, mục '{section}' của '{title}' hướng dẫn như thế nào?",
            "Để xử lý đúng nghiệp vụ vận hành, cần làm gì theo mục '{section}' trong '{title}'?",
        ],
        "finance": [
            "Từ góc nhìn tài chính, mục '{section}' trong '{title}' đặt ra yêu cầu gì?",
            "Theo quy trình tài chính nội bộ, nội dung chính của mục '{section}' trong '{title}' là gì?",
        ],
        "legal": [
            "Theo yêu cầu pháp lý nội bộ, mục '{section}' trong '{title}' cần tuân thủ điều gì?",
            "Khi rà soát hồ sơ pháp lý, mục '{section}' của '{title}' quy định ra sao?",
        ],
        "general": [
            "Nội dung trọng tâm ở mục '{section}' trong tài liệu '{title}' là gì?",
            "Theo tài liệu '{title}', mục '{section}' hướng dẫn điều gì?",
        ],
    }

    key = "general"
    if "hr" in dept:
        key = "hr"
    elif "engineering" in dept:
        key = "engineering"
    elif "security" in dept:
        key = "security"
    elif "operations" in dept:
        key = "operations"
    elif "finance" in dept:
        key = "finance"
    elif "legal" in dept:
        key = "legal"

    options = templates[key]
    template = options[idx % len(options)]
    return template.format(section=section, title=title)


def build_multi_hop_items(chunks: List[Dict], limit: int) -> List[Dict]:
    by_doc: Dict[str, List[Dict]] = {}
    for chunk in chunks:
        by_doc.setdefault(chunk["doc_id"], []).append(chunk)

    items: List[Dict] = []
    for doc_id in sorted(by_doc.keys()):
        group = sorted(by_doc[doc_id], key=lambda r: r["chunk_id"])
        if len(group) < 2:
            continue
        first = group[0]
        second = group[1]
        sec1 = first["section_path"].split(" > ")[-1]
        sec2 = second["section_path"].split(" > ")[-1]
        question = (
            f"Hãy tổng hợp yêu cầu chính ở mục '{sec1}' và '{sec2}' trong tài liệu '{first['title']}'."
        )
        reference = f"{first_sentence(first['text'])} {first_sentence(second['text'])}".strip()
        items.append(
            {
                "question": question,
                "gold_chunk_ids": [first["chunk_id"], second["chunk_id"]],
                "reference_answer": reference,
                "difficulty": "hard",
                "query_type": "positive_multi",
                "domain": domain_from_department(first.get("department", "General")),
            }
        )
        if len(items) >= limit:
            break
    return items


def negative_questions() -> List[str]:
    return [
        "Công ty có chính sách cấp cổ phiếu ESOP vesting theo tháng không?",
        "Mức phụ cấp gửi xe máy tại văn phòng chính là bao nhiêu?",
        "Quy định sử dụng phòng gym nội bộ sau 22:00 như thế nào?",
        "Nhân viên có được hỗ trợ học phí thạc sĩ toàn phần không?",
        "Quy trình đổi chỗ đậu xe ô tô theo quý được thực hiện ra sao?",
        "Có chính sách hoàn tiền mua ghế công thái học tại nhà không?",
        "Công ty quy định đồng phục bắt buộc vào thứ Hai như thế nào?",
        "Chính sách thưởng Tết theo hệ số thâm niên chi tiết ra sao?",
        "Nhân viên có thể đăng ký làm thêm ngày Chủ nhật với phụ cấp cố định không?",
        "Quy trình mượn studio quay video marketing nội bộ là gì?",
        "Công ty có chính sách nuôi thú cưng tại văn phòng không?",
        "Mức ngân sách team building quốc tế tối đa mỗi người là bao nhiêu USD?",
        "Quy định thưởng nóng cho sáng kiến AI cấp công ty là gì?",
        "Cách đăng ký phòng ngủ trưa cá nhân tại văn phòng như thế nào?",
        "Chính sách cấp xe công cho nhân viên cấp chuyên viên có không?",
        "Quy định đặt suất ăn đêm miễn phí sau 23:00 là gì?",
        "Công ty có chương trình cho vay mua nhà lãi suất ưu đãi không?",
        "Mức hỗ trợ học tiếng Nhật cho toàn bộ nhân viên là bao nhiêu?",
        "Quy trình xin phép livestream tại khu pantry được quy định thế nào?",
        "Có chính sách làm việc 4 ngày mỗi tuần trong mùa thấp điểm không?",
        "Nhân viên có thể đổi ngày nghỉ phép thành tiền mặt theo tháng không?",
        "Quy định sử dụng drone trong khuôn viên công ty là gì?",
        "Công ty có chính sách tài trợ thi marathon quốc tế cho nhân viên không?",
        "Mức thưởng giới thiệu khách hàng doanh nghiệp mới là bao nhiêu phần trăm?",
        "Quy định mở nhạc tại khu làm việc sau 18:00 như thế nào?",
        "Có chính sách miễn phí gửi con tại nhà trẻ liên kết không?",
        "Thời gian mở cửa thư viện nội bộ vào cuối tuần là mấy giờ?",
        "Quy trình xin chữ ký số cá nhân để ký hợp đồng cá nhân là gì?",
        "Công ty có quy định trang phục lễ hội bắt buộc theo tháng không?",
        "Có chính sách đổi laptop cá nhân sang máy công ty theo nhu cầu không?",
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate curated evaluation dataset")
    parser.add_argument("--chunks", default="data/processed/chunks.jsonl")
    parser.add_argument("--output", default="data/eval/qa_eval.jsonl")
    parser.add_argument("--target", type=int, default=120)
    args = parser.parse_args()

    chunks = load_chunks(Path(args.chunks))
    if not chunks:
        raise SystemExit("No chunks found. Run ingest/index first.")

    items: List[Dict] = []

    # Easy positives: one question per chunk.
    for chunk in chunks:
        items.append(
            {
                "question": easy_question(chunk),
                "gold_chunk_ids": [chunk["chunk_id"]],
                "reference_answer": first_sentence(chunk["text"]),
                "difficulty": "easy",
                "query_type": "positive_single",
                "domain": domain_from_department(chunk.get("department", "General")),
            }
        )

    # Hard single-hop paraphrases.
    hard_single_limit = 24
    for idx, chunk in enumerate(chunks[:hard_single_limit]):
        items.append(
            {
                "question": hard_question(chunk, idx),
                "gold_chunk_ids": [chunk["chunk_id"]],
                "reference_answer": first_sentence(chunk["text"]),
                "difficulty": "hard",
                "query_type": "positive_single",
                "domain": domain_from_department(chunk.get("department", "General")),
            }
        )

    # Hard multi-hop positives.
    items.extend(build_multi_hop_items(chunks, limit=12))

    # Negatives.
    for question in negative_questions():
        items.append(
            {
                "question": question,
                "gold_chunk_ids": [],
                "reference_answer": "NOT_FOUND",
                "difficulty": "hard",
                "query_type": "negative",
                "domain": "General",
            }
        )

    if len(items) != args.target:
        raise SystemExit(f"Generated {len(items)} items, expected {args.target}. Adjust generator constants.")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        for i, item in enumerate(items, start=1):
            payload = {
                "id": f"q{i:03d}",
                **item,
            }
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    pos_single = sum(1 for item in items if item["query_type"] == "positive_single")
    pos_multi = sum(1 for item in items if item["query_type"] == "positive_multi")
    neg = sum(1 for item in items if item["query_type"] == "negative")
    print(f"Wrote {len(items)} items -> {output}")
    print(f"Distribution: positive_single={pos_single}, positive_multi={pos_multi}, negative={neg}")


if __name__ == "__main__":
    main()
