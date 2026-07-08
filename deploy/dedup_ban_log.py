#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dedup data/ban_log.jsonl.

Nguyen nhan trung: truoc khi co idempotency guard (_spam_trap_banning), gateway
Discord doi khi gui MESSAGE_CREATE 2 lan cho cung 1 tin -> bot ghi 2 dong ban
giong het nhau, chi lech truong `time` vai giay.

Cach dedup: key = toan bo record TRU truong `time`. Chi gop cac dong noi dung
giong het nhau (dung ca message_id, user, reason...), giu dong dau tien, giu
nguyen thu tu. Khong bao gio gop 2 ban khac nhau.

Dung:
    python3 deploy/dedup_ban_log.py            # dedup that, co backup
    python3 deploy/dedup_ban_log.py --dry-run  # chi bao cao, khong sua
    python3 deploy/dedup_ban_log.py <path>     # chi dinh file khac
"""
import datetime
import json
import os
import sys


def dedup(path, dry_run=False):
    if not os.path.exists(path):
        print(f"Khong tim thay file: {path}")
        return 1

    kept = []
    seen = set()
    total = 0
    removed = 0
    unparsed = 0

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            raw = line.rstrip("\n")
            if not raw.strip():
                continue
            total += 1
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                # Giu lai dong khong parse duoc, khong dedup
                unparsed += 1
                kept.append(raw)
                continue
            key = json.dumps(
                {k: v for k, v in rec.items() if k != "time"},
                sort_keys=True,
                ensure_ascii=False,
            )
            if key in seen:
                removed += 1
                continue
            seen.add(key)
            kept.append(raw)

    print(f"File:        {path}")
    print(f"Tong dong:   {total}")
    print(f"Trung (xoa): {removed}")
    print(f"Con lai:     {len(kept)}")
    if unparsed:
        print(f"Khong parse duoc (giu nguyen): {unparsed}")

    if removed == 0:
        print("Khong co dong trung, khong can sua.")
        return 0

    if dry_run:
        print("[dry-run] Khong ghi file.")
        return 0

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = f"{path}.bak-{stamp}"
    os.replace(path, backup)
    print(f"Backup ban goc -> {backup}")

    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for raw in kept:
            f.write(raw + "\n")
    os.replace(tmp, path)
    print(f"Da ghi file da dedup: {path}")
    return 0


def main(argv):
    args = [a for a in argv if a != "--dry-run"]
    dry_run = "--dry-run" in argv
    if args:
        path = args[0]
    else:
        here = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(os.path.dirname(here), "data", "ban_log.jsonl")
    return dedup(path, dry_run=dry_run)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
