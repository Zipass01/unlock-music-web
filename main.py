#!/usr/bin/env python3
"""不忙脚本盒子入口：本地解密网易云 / QQ 音乐 / 酷狗 / 酷我加密音乐。

盒子把参数 JSON 文件路径作为第一个命令行参数传入。
用法: python main.py "C:/Users/xxx/AppData/Local/Temp/xxxx.json"

输出目录留空时，解密结果输出到原文件所在目录；否则输出到指定目录
（相对路径以脚本目录为基准）。
"""
from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

from music_unlock.batch import BatchOptions, collect_inputs, process_one, summarize
from music_unlock.formats.base import DecodeOptions


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python main.py <参数JSON路径>")
        return 1

    with open(sys.argv[1], encoding="utf-8") as fp:
        payload = json.load(fp)
    env = payload["environment"]
    data = payload.get("data", {})
    params = payload.get("params", {})

    inputs = [Path(p) for p in (data.get("target_paths") or [])]
    if not inputs:
        print("没有收到要解锁的文件。请选择加密音乐文件或目录后重试。")
        return 1

    common = BatchOptions(
        output_dir=Path("."),
        embed_cover=bool(params.get("embed_cover", True)),
        recursive=bool(params.get("recursive", True)),
        force=bool(params.get("force", False)),
        decode=DecodeOptions(
            ekey=params.get("ekey") or None,
            ekey_db=Path(params["ekey_db"]) if params.get("ekey_db") else None,
            kgm_key=Path(params["kgm_key"]) if params.get("kgm_key") else None,
        ),
    )

    files = collect_inputs(inputs, common.recursive)
    total = len(files)
    if total == 0:
        print("没有可处理的加密文件。请选择扩展名为 ncm/mflac/mgg/kgm/kwm 等的文件或目录。")
        return 1

    raw_output = (params.get("output_dir") or "").strip()
    if raw_output:
        out_dir = Path(raw_output)
        if not out_dir.is_absolute():
            out_dir = Path(env["script_dir"]) / out_dir
        groups = [(out_dir, files)]
    else:
        by_dir: dict[Path, list[Path]] = {}
        for f in files:
            by_dir.setdefault(f.parent, []).append(f)
        groups = list(by_dir.items())

    print(f"开始解锁，共 {total} 个文件。", flush=True)
    results = []
    done = 0
    for out_dir, group in groups:
        opts = replace(common, output_dir=out_dir)
        for f in group:
            done += 1
            print(f"[{done}/{total}] 正在解锁 {f.name} ...", flush=True)
            outcome = process_one(f, opts)
            results.append(outcome)
            if outcome.status == "ok":
                print(f"    -> {outcome.output}  ({outcome.note})", flush=True)
            elif outcome.status == "skipped":
                print(f"    跳过: {outcome.note}", flush=True)
            else:
                print(f"    失败: {outcome.note}", flush=True)

    ok, skipped, failed = summarize(results)
    print(f"完成：成功 {ok}，跳过 {skipped}，失败 {failed}", flush=True)

    if env.get("output_json"):
        out_files = [str(r.output) for r in results if r.output]
        with open(env["output_json"], "w", encoding="utf-8") as fp:
            json.dump(
                {
                    "code": 0 if failed == 0 else 1,
                    "msg": f"成功 {ok}，跳过 {skipped}，失败 {failed}",
                    "output_files": out_files,
                    "ok_count": str(ok),
                },
                fp,
                ensure_ascii=False,
            )

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())