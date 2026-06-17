# SPECIFICATION.md - 侵权检测训练图库生成器

## 功能需求

### F0: 项目范围

**F0.1** 系统 SHALL 只负责训练图库的导入、生成、标注、质检和导出。

**F0.2** 系统 SHALL NOT 实现模型训练、训练调度、训练框架封装或训练/验证/测试切分。

**F0.3** 系统 MAY 输出供下游训练系统读取的 metadata 和目录结构说明。

### F1: 注册图库导入与采集

**F1.1** 系统 SHALL 支持从本地 manifest 文件导入注册图。manifest 每行 SHALL 至少包含 `registry_id,image_path`。

**F1.2** 系统 SHOULD 支持从专利号文件导入注册图 ID。若无本地图片路径，系统 MAY 尝试在线下载，但生产模式 SHALL 在失败时跳过并记录日志。

**F1.3** 系统 MAY 支持从公开专利数据库搜索并下载外观设计专利图片，但该能力 SHALL 作为独立数据源适配器验证后接入。

**F1.4** 系统 SHALL 支持 URL manifest。manifest 的图片字段 MAY 为 `http://` 或 `https://` 图片 URL。

**F1.5** 系统 SHALL 将导入或下载的图片归一化为 PNG、512x512、RGB。

**F1.6** 系统 SHALL 将采集结果保存至 `datasets/registry/{侵权类型}/`，文件命名规则为 `patent_{注册ID}.png`。

**F1.7** 系统 SHALL 区分生产模式与测试模式。生产模式 SHALL NOT 在下载失败或来源缺失时静默生成 placeholder；测试模式 MAY 显式启用 placeholder fixture。

### F2: 正样本生成

**F2.1** 系统 SHALL 支持以下变换操作，每种变换 SHALL 记录参数：

| 变换 | 参数 |
|------|------|
| 色相偏移 | `hue_shift` (-180~180) |
| 饱和度调整 | `saturation` (0.5~2.0) |
| 明度调整 | `brightness` (0.5~2.0) |
| Logo 叠加 | `position` (x,y), `scale` (0.1~0.5), `opacity` (0.3~0.9) |
| 局部变形 | `strength` (0.01~0.15) |
| 裁剪拼接 | `crop_ratio` (0.05~0.3) |
| 镜像翻转 | `direction` (horizontal/vertical) |

**F2.2** 系统 SHALL 支持随机组合 2-4 种变换生成单张样本。

**F2.3** 系统 SHALL 为正样本生成不同相似度强度，至少覆盖 `mid` 与 `positive` 两个分层。

**F2.4** 系统 SHALL 将正样本保存至 `datasets/training/{侵权类型}/positive/`，命名规则为 `positive_{注册ID}_{序号}.png`。

### F3: 负样本生成

**F3.1** 系统 SHALL 支持从本地负样本 manifest 导入同品类但核心设计不同的图片。

**F3.2** 系统 SHOULD 支持从同品类（相同国际分类号或人工确认分类）中筛选候选负样本。

**F3.3** 系统 SHALL 对候选负样本计算或记录相似度，只有 `<40%` 的样本进入 `negative` 分层。

**F3.4** 系统 SHALL 将负样本保存至 `datasets/training/{侵权类型}/negative/`，命名规则为 `negative_{样本ID}_{序号}.png`。

### F4: 相似度与标签分层

**F4.1** 系统 SHALL 使用以下暂定阈值：

| 分层 | 相似度范围 | 默认 label |
|------|------------|------------|
| `positive` | `>=55%` | `positive` |
| `mid` | `>=40%` 且 `<55%` | `positive` |
| `negative` | `<40%` | `negative` |

**F4.2** `mid` 样本当前 SHALL 归类为正样本，但 metadata SHALL 保留 `similarity_band=mid`，便于后续重标或调参。

**F4.3** 系统 SHOULD 让训练集覆盖不同相似度程度，而不是只生成极高相似或极低相似样本。

### F5: 元数据记录

**F5.1** 系统 SHALL 为每张训练样本记录以下字段到 `metadata.csv`：

| 字段 | 说明 |
|------|------|
| `image_path` | 图片相对路径 |
| `label` | `positive` / `negative` |
| `similarity_band` | `positive` / `mid` / `negative` |
| `similarity_score` | 0.0-1.0 的相似度估计值 |
| `infringement_type` | 侵权类型 |
| `registry_id` | 对应的注册图 ID |
| `source` | `local_manifest` / `online` / `fixture` |
| `transformations` | 应用的变换操作 JSON |

### F6: 流程编排

**F6.1** 系统 SHALL 提供 CLI 入口 `python main.py generate`，支持以下参数：

```
--type                 侵权类型，必填
--registry MODE VALUE  注册图来源：file <manifest.csv> 或 search <关键词>
--negative-source PATH 负样本 manifest，可选
--positive             正样本数量，默认 20
--negative             负样本数量，默认 20
--registry-count       注册图数量，默认 5
--output               输出目录，默认 datasets/
--allow-placeholder    显式启用测试 fixture
```

**F6.2** 系统 SHALL 提供 `python main.py prepare-manifests`，支持从本地图片目录生成 registry 与 negative manifest。

**F6.3** 系统 SHALL 提供 `python main.py validate`，支持对输出数据集执行 metadata、图片、相似度分层和重复内容质检。

**F6.4** 系统 SHALL 提供 `python main.py source-spike`，支持探测候选在线专利或设计数据库并输出 JSON 报告。

**F6.5** 系统 SHALL 提供 `python main.py wipo-inspect`，支持检查 WIPO 页面结构、候选端点和搜索字段。

**F6.6** 系统 SHALL 提供实验性 `python main.py wipo-export`。当 WIPO 查询状态或使用限制阻止安全导出时，系统 SHALL 生成 header-only manifest 与 blocker report，并以非零退出码失败。

**F6.7** 系统 SHALL 按顺序执行：注册图导入或采集 -> 正样本生成 -> 负样本生成 -> metadata 写入。

## 非功能需求

**NF1** 图片处理 SHALL 在 60 秒内完成 20 张正样本生成，不含网络下载时间。

**NF2** 所有中间文件 SHALL 保存在输出目录下，不污染项目根目录。

**NF3** 单张图片处理失败 SHALL 不影响整体流程，错误 SHALL 记录到日志。

**NF4** 生产模式 SHALL fail visible：关键数据源不可用时返回失败状态或明确日志，不得静默产出假训练集。

## 边界情况

- 注册图下载失败：生产模式跳过并记录；测试模式可生成 fixture。
- manifest 图片不存在：跳过该行并记录。
- 变换参数超出范围：裁剪到有效范围并记录实际值。
- 无足够负样本：生成可用部分并报告缺口。
- 输出目录已存在：追加不覆盖，序号递增。
