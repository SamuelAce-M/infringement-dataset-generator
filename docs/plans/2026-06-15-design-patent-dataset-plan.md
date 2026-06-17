# 外观设计专利训练图库生成器 - Phase 0.1 修订实施计划

## 目标

先交付一个可信本地 MVP：从本地 manifest 导入注册图和负样本，生成多相似度分层的正样本，输出可追溯 metadata。在线 CNIPA/WIPO 采集先作为独立 Spike，不再作为 Phase 0.1 的前置假设。

本项目只做训练图库，不做训练。当前范围包括图片导入、样本生成、标签与相似度 metadata、质检和 manifest 导出；不包括模型训练、训练框架封装、训练/验证/测试切分或训练调度。

## 关键判断

当前样本集中应该覆盖各种程度的相似度。只给模型极高相似正例和极低相似负例，会让模型边界很脆。当前暂定阈值如下：

| 分层 | 相似度范围 | 默认 label | 用途 |
|------|------------|------------|------|
| `positive` | `>=55%` | `positive` | 明确侵权或高度近似样本 |
| `mid` | `>=40%` 且 `<55%` | `positive` | 边界样本，当前归正样本，后续可调 |
| `negative` | `<40%` | `negative` | 明显不同样本 |

## 当前实现问题

- `RegistryCollector` 在真实下载失败时静默生成 placeholder，容易把假数据当训练集。
- CLI 和规格不一致，当前 `--registry` 是数量，不是来源。
- metadata 没有记录真实变换参数、相似度分层和数据来源。
- 负样本没有可靠来源和分类依据，只是复用关键词搜索或 fixture。
- 测试只验证文件生成，不验证数据契约。

## Phase 0.1 实施顺序

### Task 1: 修订规格和计划

**目标**：让产品文档、规格、路线图和实施计划保持一致。

**交付**：
- 更新 `openspec/PRODUCT.md`
- 更新 `openspec/SPECIFICATION.md`
- 更新 `openspec/ROADMAP.md`
- 更新本计划文档

### Task 2: 数据源边界改造

**目标**：生产模式不允许静默 placeholder，测试 fixture 必须显式开启。

**实现点**：
- `RegistryCollector(allow_placeholder=False)` 默认不生成 fixture。
- 支持 `collect_from_file(path)`，每行格式为 `registry_id,image_path` 或 `registry_id`。
- 本地图片存在时归一化复制到 registry 目录。
- 图片缺失或下载失败时记录并跳过。
- 只有 `allow_placeholder=True` 时才生成 fixture。

### Task 3: CLI 对齐

**目标**：让入口契约符合规格。

**CLI**：

```bash
python main.py generate \
  --type 外观设计专利 \
  --registry file datasets/registry_manifest.csv \
  --negative-source datasets/negative_manifest.csv \
  --registry-count 5 \
  --positive 20 \
  --negative 20 \
  --output datasets
```

测试或演示可使用：

```bash
python main.py \
  --type 外观设计专利 \
  --registry search 保温杯 \
  --allow-placeholder
```

### Task 4: 正样本相似度分层

**目标**：生成覆盖不同相似度强度的正样本。

**实现点**：
- 每张正样本返回 `path`、`transformations`、`similarity_score`、`similarity_band`。
- `mid` 样本当前仍写入 positive 目录，label 为 `positive`。
- 变换参数写入 JSON，而不是 `"composite"`。

### Task 5: 负样本导入

**目标**：先支持可信本地负样本，不把在线采集作为默认依赖。

**实现点**：
- `NegativeGenerator.collect_from_file(path, count)` 导入负样本 manifest。
- manifest 每行格式为 `sample_id,image_path[,registry_id][,similarity_score]`。
- 未提供相似度时使用当前轻量估计，低于 0.40 才进入 negative。
- 无负样本 manifest 且未开启 placeholder 时，报告缺口。

### Task 6: metadata 和测试

**目标**：让输出可验收。

**metadata 字段**：
- `image_path`
- `label`
- `similarity_band`
- `similarity_score`
- `infringement_type`
- `registry_id`
- `source`
- `transformations`

**测试覆盖**：
- 生产模式不生成 placeholder。
- 显式 fixture 模式可以生成 placeholder。
- CLI 参数契约。
- metadata 字段完整且 transformations 是 JSON。
- 正样本精确数量。
- 非整除分配不会少生成。

### Task 7: 数据集质检脚本

**目标**：每次生成数据集后都有统一验收入口。

**实现点**：
- 提供 `validate_dataset.py --root datasets`。
- 检查 metadata 必填字段。
- 检查图片存在、可打开、512x512、RGB。
- 检查 `similarity_band` 与 `similarity_score` 阈值一致。
- 检查 negative 样本必须 `<0.40`。
- 检查 transformations 是 JSON list。
- 对重复图片、缺少某个分层给出 warning。

## Phase 0.2: 在线数据源 Spike

在线数据源接入前必须先回答：

- CNIPA 当前入口是否可稳定搜索和下载图片？
- 是否需要验证码、动态 token 或浏览器渲染？
- 是否能拿到专利号、分类号、标题、图片 URL？
- 访问频率和使用条款是否允许批量采集？
- WIPO 或其他公开数据源是否更稳定？

只有 Spike 通过后，才进入在线采集接入。
