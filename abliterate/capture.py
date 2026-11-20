from __future__ import annotations

from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from abliterate.config import AbliterateConfig


def dtype_from_str(s: str) -> torch.dtype:
    mapping = {
        "float16": torch.float16,
        "fp16": torch.float16,
        "bfloat16": torch.bfloat16,
        "bf16": torch.bfloat16,
        "float32": torch.float32,
        "fp32": torch.float32,
    }
    key = str(s).lower()
    if key not in mapping:
        raise ValueError(f"Unsupported dtype '{s}'. Expected one of: {sorted(mapping)}")
    return mapping[key]


def load_model(cfg: AbliterateConfig):
    dtype = dtype_from_str(cfg.dtype)
    if str(cfg.device).lower().startswith("cpu") and dtype in (torch.float16, torch.bfloat16):
        print(f"[capture] dtype {dtype} not ideal on CPU; using float32")
        dtype = torch.float32
    tokenizer = AutoTokenizer.from_pretrained(cfg.model_id, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"
    model = AutoModelForCausalLM.from_pretrained(
        cfg.model_id,
        dtype=dtype,
        device_map=cfg.device,
        low_cpu_mem_usage=True,
    )
    model.eval()
    return model, tokenizer


@torch.no_grad()
def capture_last_token_activations(
    model: Any, tokenizer: Any, prompts: list[str], cfg: AbliterateConfig
) -> dict[int, torch.Tensor]:
    layers = model.model.layers
    storage: dict[int, list[torch.Tensor]] = {i: [] for i in range(len(layers))}
    hooks = []
    batch_state: dict[str, torch.Tensor | None] = {"attention_mask": None}

    def make_hook(layer_idx: int):
        def hook(module, inp, out):
            hidden = out[0] if isinstance(out, tuple) else out
            mask = batch_state["attention_mask"]
            if mask is None:
                idx = hidden.new_full((hidden.shape[0],), hidden.shape[1] - 1, dtype=torch.long)
            else:
                lengths = mask.to(hidden.device).sum(dim=1).long() - 1
                idx = lengths.clamp(min=0)
            rows = torch.arange(hidden.shape[0], device=hidden.device)
            last = hidden[rows, idx, :].detach().float().cpu()
            storage[layer_idx].append(last)

        return hook

    try:
        for i, layer in enumerate(layers):
            hooks.append(layer.register_forward_hook(make_hook(i)))

        for start in range(0, len(prompts), cfg.batch_size):
            batch_prompts = prompts[start : start + cfg.batch_size]
            enc = tokenizer(
                batch_prompts,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=cfg.max_prompt_tokens,
            )
            batch_state["attention_mask"] = enc["attention_mask"].to(model.device)
            enc = {k: v.to(model.device) for k, v in enc.items()}
            model(**enc)
            batch_state["attention_mask"] = None
    finally:
        for h in hooks:
            h.remove()

    return {i: torch.cat(parts, dim=0) for i, parts in storage.items() if parts}
