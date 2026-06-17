# ARCHITECTURE.md - 侵权检测训练图库生成器

## 系统架构

```
CLI main.py
  |
  v
Pipeline Runner
  |
  +-- RegistryCollector
  |     +-- file manifest import
  |     +-- optional online search adapter
  |     +-- explicit fixture placeholder mode
  |
  +-- PositiveGenerator
  |     +-- programmatic transforms
  |     +-- similarity score estimate
  |     +-- positive / mid band assignment
  |
  +-- NegativeGenerator
  |     +-- local negative manifest import
  |     +-- optional same-category online adapter
  |     +-- negative threshold enforcement
  |
  +-- Metadata Writer
  |
  v
datasets/
  |
  +-- registry/{type}/
  +-- training/{type}/positive/
  +-- training/{type}/negative/
  +-- metadata.csv

validate_dataset.py
  |
  v
Dataset validation report
```

## 当前边界

Phase 0.1 以本地可信数据导入为主。在线 CNIPA/WIPO 采集仍是 Phase 0.2 Spike，不作为当前主流程的可靠前提。

placeholder 只能通过 `--allow-placeholder` 显式启用，用于测试或演示；生产模式下载失败或来源缺失时应跳过并记录。

## 组件说明

### 1. RegistryCollector

**职责**：导入或采集注册图库。

**输入**：
- `file <manifest.csv>`：本地注册图 manifest。
- URL manifest：manifest 图片字段可为 `http://` 或 `https://` 图片 URL。
- `search <keyword>`：在线搜索适配器入口；当前必须显式允许 placeholder 才能在无网络或无结果时生成 fixture。

**输出**：
- `datasets/registry/{type}/patent_{registry_id}.png`
- 统一 PNG、512x512、RGB。

### 2. PositiveGenerator

**职责**：基于注册图生成侵权或边界正样本。

**输出记录**：
- 图片路径。
- JSON 变换参数。
- `similarity_score`。
- `similarity_band`：`positive` 或 `mid`。

当前 `mid` 样本仍写入 positive 目录，`label=positive`，但 metadata 保留分层，便于后期调整阈值。

### 3. NegativeGenerator

**职责**：导入或筛选不侵权负样本。

**输入**：
- 本地负样本 manifest：`sample_id,image_path[,registry_id][,similarity_score]`。
- 可选同品类在线采集适配器。

**规则**：
- 负样本必须满足 `similarity_score < 0.40`。
- 不满足阈值的候选跳过并记录日志。

### 4. Pipeline Runner

**职责**：串联注册图导入、正样本生成、负样本生成、metadata 写入。

**CLI 示例**：

```bash
python main.py \
  --type 外观设计专利 \
  --registry file datasets/registry_manifest.csv \
  --negative-source datasets/negative_manifest.csv \
  --registry-count 5 \
  --positive 20 \
  --negative 20 \
  --output datasets
```

### 5. Dataset Validator

**职责**：对生成后的数据集做批量验收。

**检查项**：
- `metadata.csv` 必填字段完整。
- 图片文件存在、可打开、尺寸为 512x512、RGB。
- `transformations` 是 JSON list。
- `similarity_score` 在 0.0-1.0。
- `similarity_band` 与阈值一致。
- negative 样本低于 0.40。
- 重复图片给出 warning。
- 缺少 `mid`、`positive` 或 `negative` 分层给出 warning。

**命令**：

```bash
python validate_dataset.py --root datasets
```

### 6. Source Spike

**职责**：探测候选在线专利或设计数据库是否可访问，并输出 JSON 报告。

**命令**：

```bash
python main.py source-spike --output reports/source_spike.json --timeout 10
```

当前候选：
- WIPO Global Design Database。
- CNIPA legacy publication endpoint。

Spike 只负责验证可访问性和记录状态；稳定搜索、记录解析和图片下载需要单独数据源适配器实现。

## metadata 字段

| 字段 | 说明 |
|------|------|
| `image_path` | 相对数据集根目录的图片路径 |
| `label` | `positive` / `negative` |
| `similarity_band` | `positive` / `mid` / `negative` |
| `similarity_score` | 0.0-1.0 |
| `infringement_type` | 侵权类型 |
| `registry_id` | 对应注册图 ID |
| `source` | `generated` / `local_manifest` / `online` / `fixture` |
| `transformations` | JSON list |

## 扩展点

- 在线数据源适配器：CNIPA、WIPO 或其他公开设计数据库。
- 更可靠的相似度估计：pHash、SSIM、CLIP embedding。
- ComfyUI：作为 Phase 2 可选增强器。
- 下游训练系统接口说明：只描述 metadata 和目录结构，不提供训练代码。
