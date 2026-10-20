#!/usr/bin/env python3
"""Проверка документации репозитория: относительные ссылки, HTML, заготовки.

Профиль — это витрина, и витрина разъезжается тихо: ссылка ведёт в пустоту,
тег не закрыт, и на странице это видно только в рендере. Проверка ловит это
до публикации.

Что проверяется в каждом markdown-файле:

  1. Каждая относительная ссылка ведёт в существующий файл репозитория.
     Абсолютные ссылки (http, mailto, якоря) не проверяются: они либо
     внешние, либо работают внутри страницы.

  2. HTML-теги вложены правильно. README рендерится GitHub'ом, и незакрытый
     <div> тянет за собой полстраницы.

  3. В тексте не осталось заготовок: TODO, FIXME, «скоро», «в разработке».
     Для опубликованного документа это недопустимо.

Запуск:  python scripts/check_docs.py [файл ...]
         без аргументов проверяются все *.md в корне репозитория.
Выход:  0 — всё в порядке, 1 — есть замечания (они печатаются в stderr).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Теги без закрывающей пары.
VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
    # SVG, которые GitHub рендерит в бейджах и картинках.
    "path", "circle", "rect", "line", "polyline", "polygon", "ellipse", "use", "stop",
}

# Заготовки, которые не должны оставаться в опубликованном документе.
PLACEHOLDERS = (
    re.compile(r"\bTODO\b", re.IGNORECASE),
    re.compile(r"\bFIXME\b", re.IGNORECASE),
    re.compile(r"\bWIP\b"),
    re.compile(r"coming soon", re.IGNORECASE),
    re.compile(r"в разработке", re.IGNORECASE),
    re.compile(r"скоро", re.IGNORECASE),
)

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
TAG_RE = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)([^>]*?)(/?)>")


def check_links(text: str) -> list[str]:
    problems = []
    for match in LINK_RE.finditer(text):
        target = match.group(1).strip()
        if target.startswith(("http://", "https://", "mailto:", "#", "tel:")):
            continue
        path_part = target.split("#", 1)[0].split("?", 1)[0]
        if not path_part:
            continue
        if not (ROOT / path_part).exists():
            problems.append(f"относительная ссылка ведёт в никуда: {target}")
    return problems


def check_html(text: str) -> list[str]:
    problems = []
    stack: list[str] = []
    for match in TAG_RE.finditer(text):
        closing = match.group(1)
        tag = match.group(2).lower()
        self_closing = match.group(4)
        if tag in VOID_TAGS or self_closing:
            continue
        if closing:
            if not stack:
                problems.append(f"тег </{tag}> закрывает то, что не открыто")
            elif stack[-1] != tag:
                problems.append(f"тег </{tag}> закрывает <{stack[-1]}> — вложенность нарушена")
                stack.pop()
            else:
                stack.pop()
        else:
            stack.append(tag)
    for tag in reversed(stack):
        problems.append(f"тег <{tag}> не закрыт")
    return problems


def check_placeholders(text: str) -> list[str]:
    problems = []
    for pattern in PLACEHOLDERS:
        for match in pattern.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            problems.append(f"заготовка на строке {line}: {match.group(0)!r}")
    return problems


def check_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    problems = []
    for problem in check_links(text):
        problems.append(f"{path.name}: {problem}")
    for problem in check_html(text):
        problems.append(f"{path.name}: {problem}")
    for problem in check_placeholders(text):
        problems.append(f"{path.name}: {problem}")
    return problems


def main(argv: list[str]) -> int:
    if argv:
        targets = [Path(a) for a in argv]
        missing = [t for t in targets if not t.exists()]
        if missing:
            print(f"нет таких файлов: {', '.join(str(m) for m in missing)}", file=sys.stderr)
            return 1
    else:
        targets = sorted(ROOT.glob("*.md"))
        if not targets:
            print("в корне репозитория нет markdown-файлов", file=sys.stderr)
            return 1

    problems: list[str] = []
    for path in targets:
        problems.extend(check_file(path))

    if problems:
        print("документация не прошла проверку:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    print(
        f"документация в порядке: {len(targets)} файл(ов), "
        "ссылок и тегов без замечаний"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
