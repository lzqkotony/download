#!/usr/bin/env python3
"""构建 EZ-MS 官方客户端整合包（在 GitHub Actions runner 或服务器上运行）。

用法:
  python3 ezms/build_client_pack.py <tag> [--old-pack PATH] [--mods-dir PATH] [--out DIR]

默认行为（CI）:
  - 从 GitHub Release 下载上一版客户端包（含 PCL 启动器 + servers.dat + 旧 mods + 配置）
  - 按 ezms/mods_manifest.json 下载新增 mod（sha256 校验）
  - 重新打包为 build/EZ-MS-client-<date>.zip

本地模式（服务器上验证）:
  --old-pack /path/EZ-MS-client-20261028.zip --mods-dir /path/new_mods --out /path/pack_out
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile

UA = {"User-Agent": "EZ-MS-pack-builder/1.0 (lzqkotony ezms server admin tool)"}
OLD_TAG = "ezms-client-20261028"
OLD_ASSET_URL = "https://github.com/lzqkotony/download/releases/download/%s/EZ-MS-client-20261028.zip" % OLD_TAG
HERE = os.path.dirname(os.path.abspath(__file__))


def log(msg):
    print("[build] " + msg, flush=True)


def fetch(url, dest):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=600) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f, 1024 * 1024)
    return os.path.getsize(dest)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    tag = args[0]
    old_pack = mods_dir = out_dir = None
    i = 1
    while i < len(args):
        if args[i] == "--old-pack":
            old_pack = args[i + 1]; i += 2
        elif args[i] == "--mods-dir":
            mods_dir = args[i + 1]; i += 2
        elif args[i] == "--out":
            out_dir = args[i + 1]; i += 2
        else:
            raise SystemExit("unknown arg " + args[i])
    date = tag.replace("ezms-client-", "")
    out_dir = out_dir or os.path.join("build")
    os.makedirs(out_dir, exist_ok=True)

    work = tempfile.mkdtemp(prefix="ezms-pack-")
    log("workdir " + work)

    # 1) 上一版客户端包
    if not old_pack:
        old_pack = os.path.join(work, "old.zip")
        log("download old pack ...")
        size = fetch(OLD_ASSET_URL, old_pack)
        log("old pack %d bytes" % size)
    if not os.path.exists(old_pack):
        raise SystemExit("old pack not found: " + old_pack)

    # 2) 解包
    old_dir = os.path.join(work, "oldpack")
    os.makedirs(old_dir)
    with zipfile.ZipFile(old_pack) as z:
        z.extractall(old_dir)
    pcl = [f for f in os.listdir(old_dir) if f.lower().endswith(".exe")]
    if len(pcl) != 1:
        raise SystemExit("expected exactly one .exe in old pack, got %r" % pcl)
    pcl = pcl[0]
    mrpack_path = os.path.join(old_dir, "modpack.mrpack")
    mr_dir = os.path.join(work, "mrpack")
    os.makedirs(mr_dir)
    with zipfile.ZipFile(mrpack_path) as z:
        z.extractall(mr_dir)
    with open(os.path.join(mr_dir, "modrinth.index.json"), encoding="utf-8") as f:
        index = json.load(f)
    mods_out = os.path.join(mr_dir, "overrides", "mods")
    os.makedirs(mods_out, exist_ok=True)
    old_mods = sorted(f for f in os.listdir(mods_out) if f.endswith(".jar"))
    log("old mod count: %d" % len(old_mods))

    # 3) 新增 mod
    with open(os.path.join(HERE, "mods_manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    for item in manifest["items"]:
        fname = item["filename"]
        dest = os.path.join(mods_out, fname)
        if mods_dir:
            src = os.path.join(mods_dir, fname)
            if not os.path.exists(src):
                raise SystemExit("missing mod in mods-dir: " + src)
            if os.path.abspath(src) != os.path.abspath(dest):
                shutil.copyfile(src, dest)
        else:
            log("download %s ..." % fname)
            fetch(item["url"], dest)
        got = sha256(dest)
        if got != item["sha256"]:
            raise SystemExit("sha256 mismatch %s: %s != %s" % (fname, got, item["sha256"]))
        log("added %s (%d bytes, sha256 ok)" % (fname, os.path.getsize(dest)))
    new_mods = sorted(f for f in os.listdir(mods_out) if f.endswith(".jar"))
    log("new mod count: %d" % len(new_mods))
    if len(new_mods) != len(old_mods) + len(manifest["items"]):
        raise SystemExit("unexpected mod count: %d" % len(new_mods))

    # 4) 更新 index 元信息
    index["versionId"] = date
    index["name"] = "EZ-MS 官方整合包 " + date
    index["summary"] = "EZ-MS Minecraft 1.21.11 + NeoForge 21.11.48 客户端整合包（%s）" % date
    index["dependencies"] = {"minecraft": "1.21.11", "neoforge": "21.11.48"}
    with open(os.path.join(mr_dir, "modrinth.index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    # 5) 重新打 mrpack
    new_mrpack = os.path.join(work, "modpack.mrpack")
    with zipfile.ZipFile(new_mrpack, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(mr_dir):
            for name in files:
                full = os.path.join(root, name)
                z.write(full, os.path.relpath(full, mr_dir))

    # 6) 外层 zip: modpack.mrpack + PCL
    outer_dir = os.path.join(work, "outer")
    os.makedirs(outer_dir)
    shutil.copy(new_mrpack, os.path.join(outer_dir, "modpack.mrpack"))
    shutil.copy(os.path.join(old_dir, pcl), os.path.join(outer_dir, pcl))
    final_zip = os.path.join(out_dir, "EZ-MS-client-%s.zip" % date)
    with zipfile.ZipFile(final_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(os.listdir(outer_dir)):
            z.write(os.path.join(outer_dir, name), name)

    size = os.path.getsize(final_zip)
    digest = sha256(final_zip)
    log("FINAL %s size=%d (%.1f MB) sha256=%s" % (final_zip, size, size / 1048576.0, digest))
    with open(final_zip + ".sha256", "w") as f:
        f.write(digest + "  " + os.path.basename(final_zip) + "\n")
    shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
