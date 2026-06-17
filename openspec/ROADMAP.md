# ROADMAP.md - 侵权检测训练图库生成器

## Phase 0.1 - 可信本地 MVP（当前）

**目标**：先交付可验证的数据生成闭环，避免把不可靠在线采集或 placeholder 混入训练集。

- [x] 修订规格和实施计划，明确相似度分层与生产/测试数据边界。
- [x] 支持本地 registry manifest 导入，生产模式禁止静默 placeholder。
- [x] 支持正样本多强度变换，覆盖 `mid` 与 `positive` 分层。
- [x] 支持负样本本地 manifest 导入；无 manifest 时只允许显式 fixture。
- [x] 实现 metadata.csv 新字段：`similarity_band`、`similarity_score`、`source`、JSON `transformations`。
- [x] 对齐 CLI：`--registry MODE VALUE`、`--negative-source`、`--allow-placeholder`。
- [x] 补充 CLI、metadata、计数、placeholder 边界测试。
- [x] 增加数据集质检脚本，检查 metadata、图片、重复内容和相似度阈值。
- [x] 增加 URL manifest 导入和在线数据源 Spike 命令。
- [x] 生成第一批可信样本：注册图 >=5，正样本 20，负样本 20。

**交付物**：可追溯、可复现、可验收的外观设计专利 MVP 数据集生成器。

## Phase 0.2 - 在线数据源 Spike

**目标**：验证真实公开专利数据源后再接入主流程。

- [ ] 验证 CNIPA 当前可用入口、图片 URL、访问限制和合规约束。
- [ ] 验证 WIPO 或其他公开设计数据库的替代可行性。
- [x] 实现 WIPO 页面结构检查 Spike，提取 qk、端点和字段信息。
- [x] 增加实验性 `wipo-export` 命令，当前失败可见并输出阻断报告。
- [x] 明确延期 WIPO 自动搜索和图片解析：当前受压缩 `qz` 状态与自动抓取限制约束。
- [x] 设计数据源适配器边界，保证在线采集失败不会污染训练数据。
- [x] 加入真实源探测和失败可见报告作为人工验收依据。

## Phase 0.3 - 在线采集接入

**目标**：在 Spike 通过后接入稳定采集能力。

- [ ] 若后续确认合规且稳定的数据源 API，再实现在线 RegistryCollector 适配器。
- [ ] 若后续确认合规且稳定的数据源 API，再支持通过关键词和专利号采集真实图片。
- [ ] 若后续接入在线采集，记录原始来源 URL、专利号、分类号和下载状态。

## Phase 1.0 - 图库交付增强

**目标**：让图库产物更容易被下游训练系统消费，但不在本项目内实现训练。

- [ ] 引入更可靠的视觉相似度估计方法。
- [ ] 支持导出批次报告和数据集摘要。
- [ ] 支持人工复核状态字段。
- [ ] 支持按 label、similarity_band、source 导出子集清单。
- [ ] 文档明确下游训练系统如何读取 metadata，但不提供训练代码。

## Phase 2.0 - 规模化

**目标**：扩展类型、规模和管理能力。

- [ ] 扩展全部 6 种侵权类型。
- [ ] 每类生成 1000 张以上正负样本。
- [ ] 接入 ComfyUI 作为可选增强器。
- [ ] Web 管理界面。
- [ ] Docker 化部署。
