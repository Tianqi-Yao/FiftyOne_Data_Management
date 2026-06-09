#!/usr/bin/env python
"""用训练好的 YOLO .pt 在一个 dataset/view 上跑推理，把预测写进 FiftyOne。

用法:
    python scripts/predict.py <weights.pt> <dataset> [过滤token...] \
        [conf=0.25] [iou=0.5] [label_field=predictions] [device=cuda:0|cpu] \
        [slice=640] [overlap=0.2] [batch=16]
例:
    # 整图推理（小图/检测够用）
    python scripts/predict.py best.pt swd_2024_eachfarm_16mp site=air1 limit=50
    # 切片推理（高分辨率必备：切小片→批量推理→合并回原图坐标，不爆显存、找小目标更准）
    python scripts/predict.py best.pt swd_2024_eachfarm_16mp site=air1 limit=50 slice=640 overlap=0.2
    # 从 App 里存好的 saved view 出发（在 App 里筛/选好图 → Save view → 这里 view=名）
    python scripts/predict.py best.pt swd_2024_eachfarm_16mp view=good slice=640

- .pt 直接加载，**不用转 ONNX**。检测/分割自动判别。结果存成 FiftyOne label 字段
  （默认 predictions），App 里叠加在图上、可筛可改。要导出给别的软件用 export_labelme.py。
- **slice=<边长>** 开启切片：cv2 切成 slice×slice（overlap 重叠）小片，ultralytics 批量推理，
  加 origin 偏移回全局坐标，再按类做 box-IoU 贪心 NMS 去重。**自写、不依赖 SAHI**
  （原生支持 YOLO 能加载的任何格式 .pt/.onnx/.engine，cv2 读图+批量+全程内存，更快可控）。
- 不给 slice = 整图 apply_model（分割大图可能 OOM，可 device=cpu）。
- 过滤 token 见 viewspec.py。
"""
import os
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fiftyone as fo
from ultralytics import YOLO
from viewspec import build_view


def run_whole(view, weights, label_field, conf, device):
    model = YOLO(weights)
    if device:
        model.to(device)
    print(f"整图推理 task={model.task} device={device or 'auto'} 类别={list(model.names.values())}")
    view.apply_model(model, label_field=label_field, confidence_thresh=conf)


def tile_positions(size, tile, stride):
    """瓦片起点；snap-back 让最后一片正好贴边。"""
    if size <= tile:
        return [0]
    pos = list(range(0, size - tile + 1, stride))
    if pos[-1] != size - tile:
        pos.append(size - tile)
    return pos


def _greedy_nms(boxes, scores, iou_thr):
    """单类贪心 NMS（box-IoU），返回保留的局部索引。boxes: Nx4 xyxy。"""
    import numpy as np
    order = scores.argsort()[::-1]
    x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
    areas = (x2 - x1).clip(min=0) * (y2 - y1).clip(min=0)
    keep = []
    while order.size:
        i = order[0]
        keep.append(i)
        if order.size == 1:
            break
        rest = order[1:]
        xx1 = np.maximum(x1[i], x1[rest]); yy1 = np.maximum(y1[i], y1[rest])
        xx2 = np.minimum(x2[i], x2[rest]); yy2 = np.minimum(y2[i], y2[rest])
        inter = (xx2 - xx1).clip(min=0) * (yy2 - yy1).clip(min=0)
        iou = inter / (areas[i] + areas[rest] - inter + 1e-9)
        order = rest[iou <= iou_thr]
    return keep


def _build_dets(boxes, scores, labels, polys, W, H, iou):
    """全局候选 → 按类 NMS → fo.Detections（有多边形则栅格化成 bbox 内小 mask）。"""
    import numpy as np
    import cv2
    if not boxes:
        return fo.Detections(detections=[])
    boxes = np.array(boxes, dtype=float)
    scores = np.array(scores, dtype=float)
    labels = np.array(labels, dtype=object)

    keep = []
    for lab in set(labels.tolist()):
        idx = np.where(labels == lab)[0]
        for k in _greedy_nms(boxes[idx], scores[idx], iou):
            keep.append(idx[k])

    dets = []
    for i in keep:
        x1, y1, x2, y2 = boxes[i]
        bw, bh = x2 - x1, y2 - y1
        if bw <= 0 or bh <= 0:
            continue
        kw = dict(label=str(labels[i]), confidence=float(scores[i]),
                  bounding_box=[x1 / W, y1 / H, bw / W, bh / H])
        if polys[i] is not None:
            iw, ih = max(1, int(round(bw))), max(1, int(round(bh)))
            m = np.zeros((ih, iw), dtype=np.uint8)
            pl = (polys[i] - [x1, y1]).astype(np.int32)
            np.clip(pl[:, 0], 0, iw - 1, out=pl[:, 0])
            np.clip(pl[:, 1], 0, ih - 1, out=pl[:, 1])
            cv2.fillPoly(m, [pl], 1)
            kw["mask"] = m.astype(bool)
        dets.append(fo.Detection(**kw))
    return fo.Detections(detections=dets)


def run_sliced(view, weights, label_field, conf, device, slice_sz, overlap, iou, batch):
    import cv2
    import torch
    if device is None:
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
    model = YOLO(weights)
    model.to(device)
    stride = max(1, int(slice_sz * (1 - overlap)))
    print(f"切片推理 slice={slice_sz} overlap={overlap} iou={iou} batch={batch} "
          f"device={device} task={model.task} 类别={list(model.names.values())}")

    for sample in view.iter_samples(progress=True, autosave=True):
        img = cv2.imread(sample.filepath)
        if img is None:
            print(f"  ! 读图失败，跳过 {sample.filepath}")
            continue
        H, W = img.shape[:2]
        tiles, origins = [], []
        for y0 in tile_positions(H, slice_sz, stride):
            for x0 in tile_positions(W, slice_sz, stride):
                tiles.append(img[y0:y0 + slice_sz, x0:x0 + slice_sz])
                origins.append((x0, y0))

        boxes, scores, labels, polys = [], [], [], []
        for s in range(0, len(tiles), batch):
            chunk, chunk_org = tiles[s:s + batch], origins[s:s + batch]
            results = model.predict(chunk, conf=conf, imgsz=slice_sz,
                                    verbose=False, device=device)
            for (x0, y0), r in zip(chunk_org, results):
                if r.boxes is None or len(r.boxes) == 0:
                    continue
                xyxy = r.boxes.xyxy.cpu().numpy()
                cls = r.boxes.cls.cpu().numpy().astype(int)
                cfd = r.boxes.conf.cpu().numpy()
                xy = r.masks.xy if r.masks is not None else [None] * len(xyxy)
                for j in range(len(xyxy)):
                    boxes.append(xyxy[j] + [x0, y0, x0, y0])
                    scores.append(float(cfd[j]))
                    labels.append(model.names[int(cls[j])])
                    p = xy[j] if j < len(xy) else None
                    polys.append((p + [x0, y0]) if (p is not None and len(p) >= 3) else None)

        sample[label_field] = _build_dets(boxes, scores, labels, polys, W, H, iou)


def main(args):
    weights, name = args[0], args[1]
    if not os.path.exists(weights):
        sys.exit(f"[err] 权重不存在：{weights}")
    if name not in fo.list_datasets():
        sys.exit(f"[err] 数据集不存在：{name}")

    conf, iou, label_field, device = 0.25, 0.5, "predictions", None
    slice_sz, overlap, batch = None, 0.2, 16
    view_tokens = []
    for tok in args[2:]:
        if tok.startswith("conf="):
            conf = float(tok[5:])
        elif tok.startswith("iou="):
            iou = float(tok[4:])
        elif tok.startswith("label_field="):
            label_field = tok[len("label_field="):]
        elif tok.startswith("device="):
            device = tok[len("device="):]
        elif tok.startswith("slice="):
            slice_sz = int(tok[6:])
        elif tok.startswith("overlap="):
            overlap = float(tok[8:])
        elif tok.startswith("batch="):
            batch = int(tok[6:])
        else:
            view_tokens.append(tok)

    dataset = fo.load_dataset(name)
    view, _ = build_view(dataset, view_tokens)
    print(f"对 {len(view)} 张图 → 字段 {label_field}（conf≥{conf}）…")

    if slice_sz:
        run_sliced(view, weights, label_field, conf, device, slice_sz, overlap, iou, batch)
    else:
        run_whole(view, weights, label_field, conf, device)

    counts = view.count_values(f"{label_field}.detections.label")
    print(f"[ok] 完成：{sum(counts.values())} 个目标，分布 {counts}")
    print(f"     复核：conda run -n fif fiftyone app launch")
    print(f"     导出：python scripts/export_labelme.py {name} <同样过滤> label_field={label_field}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1:])
