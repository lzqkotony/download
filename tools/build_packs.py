#!/usr/bin/env python3
import os, shutil, zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
dist=root/'dist'; dist.mkdir(exist_ok=True)
for name,src in [('Cogito-Resources-JE.zip',root/'java'),('Cogito-Resources-BE.mcpack',root/'bedrock')]:
    out=dist/name
    if out.exists(): out.unlink()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(src.rglob('*')):
            if p.is_file(): z.write(p,p.relative_to(src))
    print(out)
# Geyser requires application/zip; release asset aliases are still octet-stream, so
# keep a raw-repository .zip copy as well.
shutil.copyfile(dist/'Cogito-Resources-BE.mcpack', dist/'Cogito-Resources-BE.zip')
print(dist/'Cogito-Resources-BE.zip')
