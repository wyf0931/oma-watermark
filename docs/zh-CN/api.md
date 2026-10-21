# API

服务在 `127.0.0.1` 上提供两个 JSON 接口。

## `POST /api/remove`

`multipart/form-data` 请求。

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `file` | file | 是 | PNG、JPEG、WebP 或 BMP，最大 25 MB |
| `x`, `y` | int | 是 | ROI 左上角，原图像素坐标 |
| `width`, `height` | int | 是 | ROI 尺寸，原图像素坐标 |
| `threshold` | int | 否 | 浅色阈值，默认 `200` |
| `expand` | int | 否 | mask 扩展像素，0–12，默认 `6` |
| `mode` | string | 否 | `ai`（默认）或 `fast` |

成功响应：

```json
{
  "result": "data:image/png;base64,...",
  "mask_overlay": "data:image/png;base64,...",
  "filename": "photo.png",
  "width": 1600,
  "height": 1200,
  "detected_pixels": 4821,
  "mode": "ai",
  "expand": 6,
  "roi": {"x": 100, "y": 200, "width": 300, "height": 120}
}
```

`result` 和 `mask_overlay` 是 PNG data URL。`detected_pixels` 是扩展前 ROI 内选中的像素数。

错误：

| 状态码 | 原因 |
| --- | --- |
| `422` | ROI 非法、缺少字段、expand/mode 非法、上传非图片，或未检测到浅色像素 |
| `503` | 请求 AI 模式但模型不可用 |
| `500` | AI 推理失败 |
| `413` | 上传超过 25 MB |

## `GET /api/health`

```json
{
  "status": "ok",
  "ai_available": true,
  "ai_engine": "lama"
}
```

前端用 `ai_available` 在启动后选择模式；模型缺失时保持快速模式。只有快速模式可用时该值可能为 `false`。

## 说明

- ROI 坐标是原图像素坐标，不是 CSS 像素。
- mask 始终裁剪在 ROI 内。
- 图片只在内存中解码，不落盘。
- 没有认证机制，服务面向本机使用。
