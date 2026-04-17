#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import fitz

if hasattr(fitz, "TOOLS") and hasattr(fitz.TOOLS, "mupdf_display_warnings"):
    fitz.TOOLS.mupdf_display_warnings(False)


FIGURE_KEYWORDS = ("framework", "overview", "architecture", "pipeline", "approach", "overall")
FIGURE_NEGATIVE = ("comparison", "ablation", "results", "ece", "calibration", "accuracy")
TABLE_POSITIVE = (
    "comparison",
    "results",
    "benchmark",
    "accuracy",
    "top-1",
    "top1",
    "mAP",
    "mean",
    "few",
    "many",
    "medium",
    "imagenet",
    "cifar",
    "inat",
    "places",
    "lvis",
    "coco",
)
TABLE_NEGATIVE = ("ablation", "runtime", "latency", "efficiency", "cost", "seed")
MAX_AREA_RATIO = 0.70
MIN_TABLE_AREA_RATIO = 0.025


@dataclass
class Region:
    kind: str
    page: int
    bbox: list[float]
    caption: str
    confidence: str
    source: str
    area_ratio: float
    output_name: str | None = None


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract tight method figures and main results tables from a paper PDF.")
    parser.add_argument("--pdf", required=True, help="Input PDF path.")
    parser.add_argument("--out-dir", required=True, help="Directory for PNGs and JSON sidecar.")
    parser.add_argument("--stem", help="Optional output stem. Defaults to the PDF stem.")
    parser.add_argument("--max-tables", type=int, default=2, help="Maximum number of main result tables to export.")
    parser.add_argument("--manual-method", action="append", default=[], help="Manual method region in page,x0,y0,x1,y1 format.")
    parser.add_argument("--manual-table", action="append", default=[], help="Manual table region in page,x0,y0,x1,y1 format. Repeatable.")
    parser.add_argument("--allow-large-crop", action="store_true", help="Allow crops above the normal area guard.")
    return parser.parse_args(argv)


def parse_manual_region(raw: str) -> tuple[int, fitz.Rect]:
    parts = [x.strip() for x in raw.split(",")]
    if len(parts) != 5:
        raise ValueError(f"Invalid manual region: {raw}")
    page = int(parts[0])
    x0, y0, x1, y1 = (float(x) for x in parts[1:])
    return page, fitz.Rect(x0, y0, x1, y1)


def get_text_blocks(page: fitz.Page) -> list[dict]:
    blocks: list[dict] = []
    raw = page.get_text("dict")
    for block in raw.get("blocks", []):
        if block.get("type") != 0:
            continue
        text_parts: list[str] = []
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text_parts.append(span.get("text", ""))
        text = " ".join("".join(text_parts).split()).strip()
        if text:
            blocks.append({"rect": fitz.Rect(block["bbox"]), "text": text})
    return blocks


def get_visual_rects(page: fitz.Page) -> list[fitz.Rect]:
    rects: list[fitz.Rect] = []
    raw = page.get_text("dict")
    for block in raw.get("blocks", []):
        if block.get("type") == 1:
            rect = fitz.Rect(block["bbox"])
            if rect.width > 8 and rect.height > 8:
                rects.append(rect)
    for drawing in page.get_drawings():
        rect = drawing.get("rect")
        if not rect:
            continue
        rect = fitz.Rect(rect)
        if rect.width < 8 or rect.height < 8:
            continue
        if rect.width * rect.height < 120:
            continue
        rects.append(rect)
    return rects


def merge_rects(rects: list[fitz.Rect], gap_x: float = 12, gap_y: float = 12) -> list[fitz.Rect]:
    merged: list[fitz.Rect] = []
    for rect in sorted(rects, key=lambda r: (r.y0, r.x0)):
        current = fitz.Rect(rect)
        changed = True
        while changed:
            changed = False
            next_merged: list[fitz.Rect] = []
            for item in merged:
                expanded = fitz.Rect(item.x0 - gap_x, item.y0 - gap_y, item.x1 + gap_x, item.y1 + gap_y)
                if expanded.intersects(current):
                    current |= item
                    changed = True
                else:
                    next_merged.append(item)
            merged = next_merged
        merged.append(current)
    return merged


def find_experiment_start(doc: fitz.Document) -> int:
    for idx in range(doc.page_count):
        text = doc[idx].get_text("text").lower()
        if (
            re.search(r"(^|\n)\s*\d+\.\s*experiments\b", text)
            or re.search(r"(^|\n)\s*[ivx]+\.\s*experiments\b", text)
            or "performance comparison" in text
            or "experimental results" in text
        ):
            return idx + 1
    return max(1, doc.page_count // 2)


def detect_figure_captions(doc: fitz.Document, max_pages: int = 12) -> list[tuple[int, fitz.Rect, str, int]]:
    items: list[tuple[int, fitz.Rect, str, int]] = []
    for page_num in range(1, min(doc.page_count, max_pages) + 1):
        page = doc[page_num - 1]
        page_text = page.get_text("text").lower()
        for block in get_text_blocks(page):
            text = block["text"]
            if not re.match(r"(?:Figure|Fig\.)\s+\d+\.?", text, re.I):
                continue
            score = 10
            lower = text.lower()
            if any(keyword in lower for keyword in FIGURE_KEYWORDS):
                score += 30
            if any(keyword in lower for keyword in FIGURE_NEGATIVE):
                score -= 28
            if page_num <= 8:
                score += 10
            if "method" in page_text or "framework" in page_text or "approach" in page_text:
                score += 10
            if re.match(r"(?:figure|fig\.)\s+2\.?", lower):
                score += 6
            items.append((page_num, block["rect"], text, score))
    return sorted(items, key=lambda item: (-item[3], item[0], item[1].y0))


def detect_table_captions(page: fitz.Page) -> list[tuple[fitz.Rect, str]]:
    items: list[tuple[fitz.Rect, str]] = []
    for block in get_text_blocks(page):
        text = block["text"]
        if re.match(r"Table\s+\d+\.?", text, re.I):
            items.append((block["rect"], text))
    return items


def expand_rect_with_labels(rect: fitz.Rect, blocks: list[dict], margin: float = 14) -> fitz.Rect:
    expanded = fitz.Rect(rect)
    zone = fitz.Rect(rect.x0 - margin, rect.y0 - margin, rect.x1 + margin, rect.y1 + margin)
    for block in blocks:
        block_rect = block["rect"]
        if block_rect.height > 90:
            continue
        if zone.intersects(block_rect):
            expanded |= block_rect
    return expanded


def clamp_rect(rect: fitz.Rect, page_rect: fitz.Rect, margin: float = 18) -> fitz.Rect:
    return fitz.Rect(
        max(margin, rect.x0),
        max(margin, rect.y0),
        min(page_rect.width - margin, rect.x1),
        min(page_rect.height - margin, rect.y1),
    )


def area_ratio(rect: fitz.Rect, page_rect: fitz.Rect) -> float:
    return (rect.width * rect.height) / max(1.0, page_rect.width * page_rect.height)


def build_region(kind: str, page_num: int, rect: fitz.Rect, caption: str, source: str, page_rect: fitz.Rect, allow_large_crop: bool) -> Region | None:
    ratio = area_ratio(rect, page_rect)
    if ratio > MAX_AREA_RATIO and not allow_large_crop:
        return None
    if source == "manual":
        confidence = "manual"
    elif ratio <= 0.45 and source.endswith("cluster"):
        confidence = "high"
    elif ratio <= MAX_AREA_RATIO:
        confidence = "medium"
    else:
        confidence = "low"
    return Region(
        kind=kind,
        page=page_num,
        bbox=[round(rect.x0, 1), round(rect.y0, 1), round(rect.x1, 1), round(rect.y1, 1)],
        caption=caption,
        confidence=confidence,
        source=source,
        area_ratio=round(ratio, 4),
    )


def choose_method_region(doc: fitz.Document, allow_large_crop: bool) -> Region | None:
    for page_num, caption_rect, caption_text, _score in detect_figure_captions(doc):
        page = doc[page_num - 1]
        page_rect = page.rect
        blocks = get_text_blocks(page)
        visual_rects = []
        upper_limit = max(18.0, caption_rect.y0 - page_rect.height * 0.72)
        for rect in get_visual_rects(page):
            if rect.y1 >= caption_rect.y0 - 4:
                continue
            if rect.y0 < upper_limit:
                continue
            visual_rects.append(rect)
        clusters = merge_rects(visual_rects, gap_x=18, gap_y=16)
        ranked: list[tuple[float, fitz.Rect]] = []
        for cluster in clusters:
            gap = max(0.0, caption_rect.y0 - cluster.y1)
            ratio = area_ratio(cluster, page_rect)
            if ratio < 0.03:
                continue
            if ratio > 0.68 and not allow_large_crop:
                continue
            score = (cluster.width * cluster.height) - gap * 120
            ranked.append((score, cluster))
        if ranked:
            cluster = sorted(ranked, key=lambda item: item[0], reverse=True)[0][1]
            cluster = expand_rect_with_labels(cluster, blocks)
            cluster = clamp_rect(cluster, page_rect)
            region = build_region("method_figure", page_num, cluster, caption_text, "figure-cluster", page_rect, allow_large_crop)
            if region:
                return region

        fallback = fitz.Rect(24, max(24, caption_rect.y0 - page_rect.height * 0.42), page_rect.width - 24, caption_rect.y0 - 8)
        fallback = clamp_rect(fallback, page_rect)
        region = build_region("method_figure", page_num, fallback, caption_text, "figure-caption-fallback", page_rect, allow_large_crop)
        if region:
            return region
    return None


def table_candidates_from_detector(page: fitz.Page, start_page: int) -> list[tuple[fitz.Rect, str, int, str]]:
    page_text = page.get_text("text").lower()
    captions = detect_table_captions(page)
    items: list[tuple[fitz.Rect, str, int, str]] = []
    try:
        tables = page.find_tables().tables
    except Exception:
        tables = []
    for table in tables:
        bbox = fitz.Rect(table.bbox)
        bbox_ratio = area_ratio(bbox, page.rect)
        if bbox_ratio < 0.018:
            continue
        caption_text = f"PDF page {page.number + 1} main table"
        score = 15
        source = "table-detector"
        above = [(rect, text) for rect, text in captions if rect.y1 <= bbox.y0 + 36]
        if above:
            rect, text = sorted(above, key=lambda item: abs(bbox.y0 - item[0].y1))[0]
            caption_text = text
            score += 18
            lower = text.lower()
            if any(token.lower() in lower for token in TABLE_POSITIVE):
                score += 18
            if any(token in lower for token in TABLE_NEGATIVE):
                score -= 16
        elif bbox_ratio < 0.05:
            continue
        if any(token.lower() in page_text for token in TABLE_POSITIVE):
            score += 10
        if any(token in page_text for token in TABLE_NEGATIVE):
            score -= 12
        if page.number + 1 <= start_page + 6:
            score += 6
        items.append((bbox, caption_text, score, source))
    return items


def fallback_table_from_caption(page: fitz.Page) -> list[tuple[fitz.Rect, str, int, str]]:
    blocks = get_text_blocks(page)
    items: list[tuple[fitz.Rect, str, int, str]] = []
    for caption_rect, caption_text in detect_table_captions(page):
        bottom = page.rect.height - 24
        for block in blocks:
            block_rect = block["rect"]
            text = block["text"]
            if block_rect.y0 <= caption_rect.y1 + 20:
                continue
            if re.match(r"(Figure|Table)\s+\d+\.?", text, re.I):
                bottom = max(caption_rect.y1 + 120, block_rect.y0 - 12)
                break
            if re.match(r"\d+\.\d+(\.\d+)?\s+", text):
                bottom = max(caption_rect.y1 + 120, block_rect.y0 - 12)
                break
        rect = fitz.Rect(24, caption_rect.y1 + 4, page.rect.width - 24, bottom)
        score = 12
        lower = caption_text.lower()
        if any(token.lower() in lower for token in TABLE_POSITIVE):
            score += 15
        if any(token in lower for token in TABLE_NEGATIVE):
            score -= 16
        items.append((rect, caption_text, score, "table-caption-fallback"))
    return items


def choose_table_regions(doc: fitz.Document, max_tables: int, allow_large_crop: bool) -> list[Region]:
    start_page = find_experiment_start(doc)
    raw_candidates: list[tuple[int, fitz.Rect, str, int, str]] = []
    for page_num in range(start_page, doc.page_count + 1):
        page = doc[page_num - 1]
        raw = table_candidates_from_detector(page, start_page)
        if not raw:
            raw = fallback_table_from_caption(page)
        for rect, caption, score, source in raw:
            raw_candidates.append((page_num, rect, caption, score, source))
    regions: list[Region] = []
    seen_pages: set[tuple[int, int, int]] = set()
    for page_num, rect, caption, _score, source in sorted(raw_candidates, key=lambda item: (-item[3], item[0], item[1].y0)):
        page = doc[page_num - 1]
        rect = clamp_rect(rect, page.rect)
        region = build_region("results_table", page_num, rect, caption, source, page.rect, allow_large_crop)
        if not region:
            continue
        if region.area_ratio < MIN_TABLE_AREA_RATIO and source != "manual":
            continue
        shape = (page_num, round(rect.y0), round(rect.y1))
        if shape in seen_pages:
            continue
        seen_pages.add(shape)
        regions.append(region)
        if len(regions) >= max_tables:
            break
    return regions


def render_region(doc: fitz.Document, region: Region, out_path: Path) -> None:
    page = doc[region.page - 1]
    rect = fitz.Rect(*region.bbox)
    pix = page.get_pixmap(matrix=fitz.Matrix(2.4, 2.4), clip=rect, alpha=False)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pix.save(out_path)


def safe_name(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_") or "paper"


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    pdf_path = Path(args.pdf).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    if not pdf_path.exists():
        raise SystemExit(f"Missing PDF: {pdf_path}")

    stem = safe_name(args.stem or pdf_path.stem)
    doc = fitz.open(str(pdf_path))

    manual_method = [parse_manual_region(raw) for raw in args.manual_method]
    manual_tables = [parse_manual_region(raw) for raw in args.manual_table]

    method_region: Region | None = None
    if manual_method:
        page_num, rect = manual_method[0]
        page = doc[page_num - 1]
        rect = clamp_rect(rect, page.rect)
        method_region = build_region("method_figure", page_num, rect, "manual method region", "manual", page.rect, True)
    else:
        method_region = choose_method_region(doc, args.allow_large_crop)

    table_regions: list[Region]
    if manual_tables:
        table_regions = []
        for page_num, rect in manual_tables[: args.max_tables]:
            page = doc[page_num - 1]
            rect = clamp_rect(rect, page.rect)
            region = build_region("results_table", page_num, rect, "manual table region", "manual", page.rect, True)
            if region:
                table_regions.append(region)
    else:
        table_regions = choose_table_regions(doc, args.max_tables, args.allow_large_crop)

    warnings: list[str] = []
    if method_region is None:
        warnings.append("No acceptable method figure region was found.")
    if not table_regions:
        warnings.append("No acceptable results table region was found.")

    if method_region:
        method_region.output_name = f"{stem}_figure_main.png"
        render_region(doc, method_region, out_dir / method_region.output_name)
        if method_region.confidence == "medium" and method_region.area_ratio > 0.55:
            warnings.append("Method figure crop is medium confidence and visually large; consider a manual bbox.")

    for index, region in enumerate(table_regions, start=1):
        region.output_name = f"{stem}_table_main_{index}.png"
        render_region(doc, region, out_dir / region.output_name)
        if region.confidence == "medium" and region.area_ratio > 0.55:
            warnings.append(f"Results table {index} is medium confidence and visually large; consider a manual bbox.")

    payload = {
        "pdf": str(pdf_path),
        "method_figure": asdict(method_region) if method_region else None,
        "results_tables": [asdict(region) for region in table_regions],
        "warnings": warnings,
    }
    json_path = out_dir / f"{stem}_regions.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
