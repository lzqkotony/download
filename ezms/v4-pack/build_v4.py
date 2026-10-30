#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建 EZ-MS 1.21.1 客户端 v4（优化版）整合包。

输入：
  build/r2.zip                     —— 由 workflow 从 GitHub Release 下载的 r2 客户端包
  ezms/v4-pack/mods/*.jar          —— 25 个客户端优化 mod + codxlib/economycraft 补依赖
  ezms/v4-pack/pcl/                —— 旧版客户端 PCL2
  ezms/v4-pack/servers.dat         —— 旧版客户端服务器列表

输出：
  dist/EZ-MS-1.21.1-client-<ver>.mrpack        标准 Modrinth 整合包
  dist/EZ-MS-client-<ver>.zip                  分发包（mrpack + PCL2 + 说明）
  dist/*.sha256
"""
from __future__ import annotations

import hashlib
import json
import os
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
R2_ZIP = os.path.join(REPO, "build", "r2.zip")
OUT_DIR = os.path.join(REPO, "dist")
VERSION = os.environ.get("PACK_VERSION", "20261030-v4")

README = """EZ-MS 1.21.1 客户端整合包（优化版 v4）

环境：Minecraft 1.21.1 + NeoForge 21.1.265 + Java 21
内容：服务端配套客户端 mod + 25 个客户端优化 mod（Sodium/Lithium/Iris/JEI/Jade/Xaero 地图等）+
      codxlib、economycraft 补依赖 + 旧版官方客户端服务器列表。

安装（PCL2 / Modrinth App / Prism / HMCL 均可）：
1. 把 EZ-MS-1.21.1-client-%s.mrpack 拖入启动器，自动安装 NeoForge 与全部 mod；
2. 启动游戏，多人列表已带服务器条目；
3. 进服先 /register <密码> <密码>，之后 /login <密码>。

说明：本版暂不含“匠魂移植”（其 1.5.0 与 NeoForge 21.1.265 存在进服 payload 兼容问题，恢复后另行更新）。
""" % VERSION


def read_file(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)

    # 1) 读取 r2 基础包里的客户端 mods
    mods: dict[str, bytes] = {}
    with zipfile.ZipFile(R2_ZIP) as z:
        for name in z.namelist():
            if name.startswith("mods/") and name.endswith(".jar"):
                mods[os.path.basename(name)] = z.read(name)
    before = len(mods)
    mods = {n: d for n, d in mods.items() if "Tinkers" not in n}

    # 2) 追加优化 mod / 补依赖
    extra_dir = os.path.join(HERE, "mods")
    for name in sorted(os.listdir(extra_dir)):
        if name.endswith(".jar"):
            mods[name] = read_file(os.path.join(extra_dir, name))

    servers_dat = read_file(os.path.join(HERE, "servers.dat"))
    pcl_path = os.path.join(HERE, "pcl", "Plain Craft Launcher.exe")

    # 3) 构建 .mrpack
    index = {
        "game": "minecraft",
        "formatVersion": 1,
        "versionId": "ezms-1.21.1-" + VERSION,
        "name": "EZ-MS 1.21.1 客户端整合包（优化版）",
        "summary": "EZ-MS 官方服务器客户端：服务端配套 mod + 客户端优化 mod + 服务器列表，自包含安装",
        "files": [],
        "dependencies": {"minecraft": "1.21.1", "neoforge": "21.1.265"},
    }
    mrpack = os.path.join(OUT_DIR, "EZ-MS-1.21.1-client-%s.mrpack" % VERSION)
    with zipfile.ZipFile(mrpack, "w", zipfile.ZIP_STORED) as z:
        z.writestr("modrinth.index.json", json.dumps(index, ensure_ascii=False, indent=2))
        for name, data in sorted(mods.items()):
            z.writestr("overrides/mods/" + name, data)
        z.writestr("overrides/servers.dat", servers_dat)
        z.writestr("overrides/EZ-MS-README.txt", README)

    # 4) 构建分发包（mrpack + PCL2 + 说明）
    dist = os.path.join(OUT_DIR, "EZ-MS-client-%s.zip" % VERSION)
    with zipfile.ZipFile(dist, "w", zipfile.ZIP_STORED) as z:
        z.write(mrpack, os.path.basename(mrpack))
        if os.path.exists(pcl_path):
            z.write(pcl_path, "Plain Craft Launcher.exe")
        z.writestr("EZ-MS-README.txt", README)

    # 5) 校验和
    for path in (mrpack, dist):
        h = hashlib.sha256(read_file(path)).hexdigest()
        with open(path + ".sha256", "w", encoding="utf-8") as f:
            f.write("%s  %s\n" % (h, os.path.basename(path)))

    print("r2 mods=%d, after removing Tinkers=%d, final mods=%d" % (before, len(mods) - 27 + 27, len(mods)))
    for path in (mrpack, dist):
        print("%s  %d bytes" % (os.path.basename(path), os.path.getsize(path)))


if __name__ == "__main__":
    main()
