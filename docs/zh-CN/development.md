# 开发

## 环境

```bash
uv sync                       # Web 与测试依赖
uv sync --extra desktop       # 可选桌面依赖
npm ci                        # CSS 构建依赖
```

运行：

```bash
uv run oma-watermark
uv run oma-watermark-desktop
```

## 测试

```bash
uv run pytest
```

覆盖 ROI 校验、mask 生成、边缘扩展、修复范围、API 成功与错误路径，以及模型缺失处理。模型存在时会运行一次 LaMa 冒烟测试，否则自动跳过。

## CSS

修改 `src/oma_watermark/static/app.css`、`index.html` 或 `style.css` 后重新构建：

```bash
npm run build:css
```

不要手改 `app.built.css`。生成文件需要提交，以保证离线和打包版本可用。

## 检查清单

提交前运行：

```bash
npm run build:css
ruff check src tests
ruff format --check src tests
uv lock --check
uv run pytest
node --check src/oma_watermark/static/app.js
```

## 贡献流程

1. 较大的行为或 API 改动请先开 Issue。
2. 算法和 API 改动先补测试。
3. ROI 坐标保持原图像素坐标，mask 必须裁剪在 ROI 内。
4. 行为、参数或打包方式变化时同步更新文档：
   - 用户可见行为：`README.md` 和 `README.zh-CN.md`
   - 详细指南：`docs/` 和 `docs/zh-CN/`
   - 架构不变量和维护规则：`AGENTS.md`
5. 提交 Pull Request，附简短说明和测试结果。

## 静态资源与打包

新增静态文件或模型文件时，必须加入 `packaging/oma-watermark.spec`。修改路径、spec 或构建脚本后，需要验证打包产物。详见 [桌面与打包](./desktop.md)。

## 手动验证

- Web：上传 → 框选 → 快速/AI → 结果/检测 → 下载。
- 桌面：`uv run oma-watermark-desktop`，确认隐藏网站导航、使用原生标题栏、下载可用。
- 主题：重新构建 CSS 后检查浅色和深色模式。
