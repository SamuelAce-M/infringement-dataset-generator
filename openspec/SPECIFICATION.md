# SPECIFICATION.md — 侵权检测训练图库生成器

## 功能需求

### F1: 注册图库采集

**F1.1** 系统 SHALL 支持从中国专利公布公告系统 (http://epub.sipo.gov.cn) 搜索并下载外观设计专利图片。

**F1.2** 系统 SHALL 支持通过专利号直接获取对应专利图片。

**F1.3** 系统 SHALL 将下载的图片归一化为统一格式：PNG、512x512、RGB 色彩空间。

**F1.4** 系统 SHALL 将采集结果保存至 `datasets/registry/{侵权类型}/` 目录，文件命名规则：`patent_{专利号}.png`。

### F2: 正样本生成（程序化变换）

**F2.1** 系统 SHALL 支持以下变换操作，每种可独立配置参数：

| 变换 | 参数 |
|------|------|
| 色相偏移 | `hue_shift` (-180~180) |
| 饱和度调整 | `saturation` (0.5~2.0) |
| 明度调整 | `brightness` (0.5~2.0) |
| Logo 叠加 | `logo_path`, `position` (x,y), `scale` (0.1~0.5), `opacity` (0.3~0.9) |
| 局部变形 | `region` (x,y,w,h), `strength` (0.01~0.15) |
| 裁剪拼接 | `crop_ratio` (0.05~0.3) |
| 镜像翻转 | `direction` (horizontal/vertical) |

**F2.2** 系统 SHALL 支持随机组合 2~4 种变换生成单张样本。

**F2.3** 每张正样本 SHALL 保留原注册图的核心设计特征（轮廓、比例、结构布局不发生 >10% 的改变）。

**F2.4** 系统 SHALL 将正样本保存至 `datasets/training/{侵权类型}/positive/`，命名规则：`positive_{注册ID}_{序号}.png`。

### F3: 负样本生成

**F3.1** 系统 SHALL 从同品类（相同国际分类号）中筛选与注册图核心设计特征不同的专利图片。

**F3.2** 系统 SHALL 确认负样本与注册图的整体视觉效果存在显著差异。

**F3.3** 系统 SHALL 将负样本保存至 `datasets/training/{侵权类型}/negative/`，命名规则：`negative_{专利号}_{序号}.png`。

### F4: 元数据记录

**F4.1** 系统 SHALL 为每张训练样本记录以下元数据到 `metadata.csv`：

| 字段 | 说明 |
|------|------|
| `image_path` | 图片相对路径 |
| `label` | `positive` / `negative` |
| `infringement_type` | 侵权类型（如 `外观设计专利`） |
| `registry_id` | 对应的注册图 ID |
| `transformations` | 应用的变换操作（JSON，仅正样本） |

### F5: 流程编排

**F5.1** 系统 SHALL 提供 CLI 入口 `python main.py`，支持以下参数：

```
--type        侵权类型（必填）
--registry    注册图来源：search <关键词> 或 file <ids.txt>
--positive    正样本数量（默认 20）
--negative    负样本数量（默认 20）
--output      输出目录（默认 datasets/）
```

**F5.2** 系统 SHALL 按顺序执行：注册图采集 → 正样本生成 → 负样本生成 → 元数据写入。

## 非功能需求

**NF1** 图片处理 SHALL 在 60 秒内完成 20 张正样本的生成（不含网络下载时间）。

**NF2** 所有中间文件 SHALL 保存在 `datasets/` 下，不污染项目根目录。

**NF3** 错误处理：单张图片处理失败不影响整体流程，错误记录到日志。

## 边界情况

- 注册图下载失败 → 跳过该专利，记录日志，继续处理下一个
- 变换参数超出范围 → 裁剪到有效范围
- 同品类无其他专利可用 → 提示用户补充数据源
- 输出目录已存在 → 追加不覆盖（递增序号）

## 接口定义

### Registry Collector

```python
class RegistryCollector:
    def search(self, keyword: str, limit: int = 5) -> list[str]:
        """搜索专利号列表"""
    
    def download(self, patent_id: str) -> str:
        """下载单个专利图片，返回本地路径"""
    
    def normalize(self, image_path: str) -> str:
        """归一化为 512x512 PNG"""
```

### Positive Generator

```python
class PositiveGenerator:
    def add_transform(self, name: str, params: dict) -> None:
        """注册变换操作"""
    
    def generate(self, registry_image: str, count: int) -> list[str]:
        """生成 count 张正样本，返回路径列表"""
```

### Negative Generator

```python
class NegativeGenerator:
    def collect_same_category(self, category: str, exclude_ids: list[str], count: int) -> list[str]:
        """收集同类不同专利图片"""
    
    def verify_difference(self, registry_image: str, candidate: str) -> bool:
        """确认候选图与注册图存在显著差异"""
```
