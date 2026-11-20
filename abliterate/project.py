from __future__ import annotations

from typing import Any

import torch

from abliterate.config import AbliterateConfig


@torch.no_grad()
def project_out_(weight: torch.Tensor, r: torch.Tensor, strength: float) -> None:
    r = r.reshape(-1)
    if r.ndim != 1:
        raise ValueError(f"r must be a 1D vector, got shape {tuple(r.shape)}")
    if weight.ndim != 2:
        raise ValueError(f"weight must be 2D, got shape {tuple(weight.shape)}")
    out_features, in_features = weight.shape
    r_cast = r.to(device=weight.device, dtype=weight.dtype)
    if r.shape[-1] == in_features and r.shape[-1] == out_features:
        # [hidden, hidden]: both orientations equivalent
        proj = (weight @ r_cast).unsqueeze(1) * r_cast.unsqueeze(0)
    elif r.shape[-1] == out_features and r.shape[-1] != in_features:
        # output-side projection for [out, in] e.g. down_proj [hidden, intermediate]:
        # W <- W - strength * r (r^T W), removing residual-direction component from outputs
        proj = r_cast.unsqueeze(1) * (r_cast @ weight).unsqueeze(0)
    elif r.shape[-1] == in_features and r.shape[-1] != out_features:
        # input-side form for [out, in] where r matches in_features
        proj = (weight @ r_cast).unsqueeze(1) * r_cast.unsqueeze(0)
    else:
        if out_features != r.shape[0] and in_features == r.shape[0]:
            raise ValueError(
                f"Conv1D-style weight layout mismatch: weight has shape {tuple(weight.shape)} "
                f"(likely [hidden, out]) but expected [out, hidden] with hidden={r.shape[-1]}. "
                f"Refusing to apply orthogonalization to the wrong layout."
            )
        raise ValueError(
            f"Shape mismatch: r hidden {r.shape[-1]} != weight out_features {out_features} "
            f"and != in_features {in_features} (weight shape {tuple(weight.shape)})"
        )
    weight.sub_(float(strength) * proj)


def _resolve_module(layer: Any, dotted: str) -> Any:
    candidates = [dotted]
    if "." not in dotted:
        if dotted == "o_proj":
            candidates.append(f"self_attn.{dotted}")
        elif dotted == "down_proj":
            candidates.append(f"mlp.{dotted}")
        else:
            candidates.extend([f"self_attn.{dotted}", f"mlp.{dotted}"])
    last_err = None
    for cand in candidates:
        try:
            obj = layer
            for part in cand.split("."):
                if not hasattr(obj, part):
                    subs = [n for n, _ in layer.named_children()]
                    raise ValueError(
                        f"Target module '{cand}' not found: layer has no attribute '{part}'. "
                        f"Available submodules on layer: {subs}"
                    )
                obj = getattr(obj, part)
            if not hasattr(obj, "weight"):
                raise ValueError(f"Resolved module '{cand}' has no weight parameter")
            return obj
        except ValueError as exc:
            last_err = exc
    assert last_err is not None
    raise last_err


def apply_abliteration_(model: Any, directions: dict[int, torch.Tensor], cfg: AbliterateConfig) -> int:
    layers = model.model.layers
    modified = 0
    for i, layer in enumerate(layers):
        if i not in directions:
            continue
        r = directions[i]
        for target in cfg.target_modules:
            module = _resolve_module(layer, target)
            try:
                project_out_(module.weight, r, cfg.strength)
            except ValueError as exc:
                raise ValueError(
                    f"Layer {i} module '{target}' weight shape {tuple(module.weight.shape)} "
                    f"incompatible with direction shape {tuple(r.shape)}: {exc}"
                ) from exc
            modified += 1
    return modified
