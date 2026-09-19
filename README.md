# Cogito Resource Packs

Java 与 Bedrock/Geyser 双端资源包，为 Cogito 的「金枝」提供金色枯木模型。

## 下载

- Java：`Cogito-Resources-JE.zip`
- Bedrock/Geyser：`Cogito-Resources-BE.mcpack`

资源包 Release 可通过 GitHub 代理访问：

```text
https://v4.gh-proxy.org/https://github.com/lzqkotony/download/releases/download/v1.0.1/Cogito-Resources-JE.zip
https://v4.gh-proxy.org/https://raw.githubusercontent.com/lzqkotony/download/v1.0.1/dist/Cogito-Resources-BE.zip
```

## 构建

```bash
python3 tools/build_packs.py
```

## Geyser 配置

把 `geyser/custom_mappings/cogito_golden_bough.json` 放进 Geyser 的 `custom_mappings/`，并把 Bedrock 资源包 URL 放进 `resource-pack-urls`。
