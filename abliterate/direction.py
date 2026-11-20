from __future__ import annotations

import numpy as np
import torch


def compute_refusal_directions(
    harmful: dict[int, torch.Tensor], harmless: dict[int, torch.Tensor]
) -> dict[int, torch.Tensor]:
    directions: dict[int, torch.Tensor] = {}
    for i in sorted(set(harmful) & set(harmless)):
        h = harmful[i].float()
        b = harmless[i].float()
        if h.shape[1:] != b.shape[1:]:
            raise ValueError(
                f"Shape mismatch at layer {i}: harmful {tuple(h.shape)} vs harmless {tuple(b.shape)}"
            )
        diff = h.mean(0) - b.mean(0)
        norm = diff.norm()
        if float(norm) == 0.0:
            continue
        directions[i] = (diff / norm).float()
    return directions


def cosine_matrix(dirs: dict[int, torch.Tensor]) -> np.ndarray:
    keys = sorted(dirs)
    if not keys:
        return np.zeros((0, 0), dtype=np.float32)
    mat = torch.stack([dirs[k].float() for k in keys], dim=0)
    mat = mat / mat.norm(dim=1, keepdim=True).clamp(min=1e-12)
    return (mat @ mat.T).cpu().numpy()
