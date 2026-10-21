# API

The server exposes two JSON endpoints on `127.0.0.1`.

## `POST /api/remove`

`multipart/form-data` request.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `file` | file | yes | PNG, JPEG, WebP, or BMP; max 25 MB |
| `x`, `y` | int | yes | ROI top-left corner in original-image pixels |
| `width`, `height` | int | yes | ROI size in original-image pixels |
| `threshold` | int | no | Light-pixel threshold, default `200` |
| `expand` | int | no | Mask expansion in pixels, 0–12, default `6` |
| `mode` | string | no | `ai` (default) or `fast` |

Success response:

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

`result` and `mask_overlay` are PNG data URLs. `detected_pixels` counts pixels selected inside the ROI before expansion.

Errors:

| Status | Cause |
| --- | --- |
| `422` | Invalid ROI, missing fields, unsupported expand/mode, non-image upload, or no light pixels detected |
| `503` | AI mode requested but the model is unavailable |
| `500` | AI inference failed |
| `413` | Upload exceeds 25 MB |

## `GET /api/health`

```json
{
  "status": "ok",
  "ai_available": true,
  "ai_engine": "lama"
}
```

The UI uses `ai_available` to select AI mode after startup. If the model is missing, it keeps Fast mode. `ai_available` may be `false` when only Fast mode is usable.

## Notes

- ROI coordinates are original-image pixels, not CSS pixels.
- The mask is always clipped to the ROI.
- Images are decoded in memory and never persisted.
- No authentication is implemented; the server is intended for localhost use.
