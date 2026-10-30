#!/usr/bin/env python3
"""构建 EZ-MS 1.21.1 客户端必备 mod 包（GitHub Actions / 本地均可运行）。

读取 ezms/client_mods_1.21.1.json，下载所有 client_required mod，
校验 sha1/size，打成 EZ-MS-client-mods-1.21.1-<tag>.zip（含 mods/、README.txt、modlist.json）。
"""
import hashlib
import json
import os
import shutil
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, "client_mods_1.21.1.json")
OUT = os.path.join("build")
UA = {"User-Agent": "EZ-MS-client-pack/1.0 (lzqkotony)"}


def log(msg):
    print("[build] " + msg, flush=True)


def fetch(url, dest):
    import urllib.request
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=600) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f, 1024 * 1024)


def sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GITHUB_REF_NAME", "dev")
    date = tag.replace("ezms-client-1.21.1-", "").replace("ezms-client-", "")
    os.makedirs(OUT, exist_ok=True)
    with open(MANIFEST, encoding="utf-8") as f:
        manifest = json.load(f)
    root = os.path.join(OUT, "EZ-MS-client-mods-1.21.1-" + date)
    mods_dir = os.path.join(root, "mods")
    os.makedirs(mods_dir, exist_ok=True)

    for item in manifest["items"]:
        fn = item["filename"]
        dest = os.path.join(mods_dir, fn)
        log("download " + fn)
        ok = False
        last = None
        for attempt in range(1, 4):
            try:
                fetch(item["url"], dest)
                if item.get("size") and os.path.getsize(dest) != item["size"]:
                    raise RuntimeError("size mismatch %d != %d" % (os.path.getsize(dest), item["size"]))
                if item.get("sha1"):
                    got = sha1(dest)
                    if got != item["sha1"].lower():
                        raise RuntimeError("sha1 mismatch " + got)
                ok = True
                break
            except Exception as e:  # noqa: BLE001
                last = e
                log("retry %d %s: %s" % (attempt, fn, e))
        if not ok:
            raise SystemExit("failed to download %s: %s" % (fn, last))
        log("ok %s (%d bytes)" % (fn, os.path.getsize(dest)))

    readme = """EZ-MS 1.21.1 客户端必备 Mod 包（{date}）

环境要求：
  - Minecraft 1.21.1
  - NeoForge 21.1.265（客户端安装器：https://neoforged.net/ ）
  - 64 位 Java 21

安装：
  1. 用 NeoForge 安装器给 1.21.1 客户端装好 NeoForge 21.1.265；
  2. 打开 .minecraft 目录（或对应版本隔离目录），把本包 mods 文件夹里的
     所有 .jar 复制到客户端 mods 目录；
  3. 启动游戏 → 多人游戏 → 添加服务器地址。

服务器：EZ-MS 1.21.1 NeoForge 单服（端口 25565，具体地址问服主）。
注意：本包只含客户端“必需”mod（client_side=required），
      服务端专用 mod（EasyLogin / EasyBot / ezmsproxy / spark 等）不需要装。
管理类可选 mod（OPAC、小地图、语音等）请自行另装。
""".format(date=date)
    with open(os.path.join(root, "README.txt"), "w", encoding="utf-8") as f:
        f.write(readme)
    with open(os.path.join(root, "modlist.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    zip_path = os.path.join(OUT, "EZ-MS-client-mods-1.21.1-%s.zip" % date)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for base, _dirs, files in os.walk(root):
            for name in files:
                full = os.path.join(base, name)
                z.write(full, os.path.relpath(full, root))
    size = os.path.getsize(zip_path)
    digest = hashlib.sha256(open(zip_path, "rb").read()).hexdigest()
    log("FINAL %s size=%.1fMB sha256=%s" % (zip_path, size / 1048576.0, digest))
    with open(zip_path + ".sha256", "w") as f:
        f.write(digest + "  " + os.path.basename(zip_path) + "\n")


if __name__ == "__main__":
    main()
