from __future__ import annotations

import json
from pathlib import Path

import click

from abliterate.capture import capture_last_token_activations, dtype_from_str, load_model
from abliterate.config import AbliterateConfig
from abliterate.direction import compute_refusal_directions
from abliterate.evaluate import run_eval, score_refusals
from abliterate.project import apply_abliteration_, _resolve_module
from abliterate.prompts import load_prompt_pairs
from abliterate.steering import apply_steering_from_file, load_steering, save_steering


def _cfg_from_opts(**opts) -> AbliterateConfig:
    target_modules = opts.get("target_modules")
    if isinstance(target_modules, str):
        target_modules = tuple(s.strip() for s in target_modules.split(",") if s.strip())
    layers = opts.get("layers")
    if isinstance(layers, str) and layers.strip():
        opts["_layers"] = {int(s.strip()) for s in layers.split(",") if s.strip()}
    data = {
        "model_id": opts["model"],
        "device": opts.get("device", "cuda"),
        "dtype": opts.get("dtype", "float16"),
        "harmful_dataset": opts.get("harmful_dataset", "mlabonne/harmful_behaviors"),
        "harmless_dataset": opts.get("harmless_dataset", "mlabonne/harmless_alpaca"),
        "n_samples": int(opts.get("n_samples", 128)),
        "batch_size": int(opts.get("batch_size", 8)),
        "max_prompt_tokens": int(opts.get("max_prompt_tokens", 256)),
        "target_modules": target_modules or ("o_proj", "down_proj"),
        "strength": float(opts.get("strength", 1.0)),
        "output_dir": opts.get("output_dir", "./abliterated"),
        "save_steering": bool(opts.get("save_steering", False)),
    }
    return AbliterateConfig(**data)


_COMMON = [
    click.option("--model", "model", required=True, help="HF model id or local path"),
    click.option("--device", default="cuda", show_default=True),
    click.option("--dtype", default="float16", show_default=True),
    click.option("--n-samples", default=128, show_default=True, type=int),
    click.option("--batch-size", default=8, show_default=True, type=int),
    click.option("--max-prompt-tokens", default=256, show_default=True, type=int),
    click.option("--harmful-dataset", default="mlabonne/harmful_behaviors", show_default=True),
    click.option("--harmless-dataset", default="mlabonne/harmless_alpaca", show_default=True),
    click.option("--target-modules", default="o_proj,down_proj", show_default=True),
    click.option("--strength", default=1.0, show_default=True, type=float),
]


def add_common(func):
    for opt in reversed(_COMMON):
        func = opt(func)
    return func


@click.group()
def abliterate():
    """Orthogonalize refusal behavior from open-weights causal LMs."""


@abliterate.command("run")
@add_common
@click.option("--output-dir", default="./abliterated", show_default=True)
@click.option("--save-steering", is_flag=True, default=False)
def run_cmd(**opts):
    cfg = _cfg_from_opts(**opts)
    click.echo(f"[run] model={cfg.model_id} device={cfg.device} dtype={cfg.dtype} n={cfg.n_samples}")

    click.echo("[run] loading prompts")
    harmful, harmless = load_prompt_pairs(cfg)
    held_out = harmful[min(8, len(harmful)) : min(16, len(harmful))] or harmful[: min(8, len(harmful))]

    click.echo("[run] loading model")
    model, tokenizer = load_model(cfg)

    click.echo("[run] baseline eval")
    before = score_refusals(model, tokenizer, held_out, cfg)
    click.echo(f"[run] before refusal_rate={before['refusal_rate']:.3f} ({before['refused']}/{before['n']})")

    click.echo("[run] capturing harmful activations")
    h_act = capture_last_token_activations(model, tokenizer, harmful, cfg)
    click.echo("[run] capturing harmless activations")
    b_act = capture_last_token_activations(model, tokenizer, harmless, cfg)

    click.echo("[run] computing directions")
    dirs = compute_refusal_directions(h_act, b_act)
    click.echo(f"[run] directions={len(dirs)} layers")

    if cfg.save_steering:
        steering_path = Path(cfg.output_dir) / "steering.pt"
        steering_path.parent.mkdir(parents=True, exist_ok=True)
        save_steering(str(steering_path), dirs)
        click.echo(f"[run] saved steering -> {steering_path}")

    click.echo("[run] applying abliteration")
    modified = apply_abliteration_(model, dirs, cfg)
    click.echo(f"[run] modified_weights={modified}")

    out = Path(cfg.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    click.echo(f"[run] saving model -> {out}")
    model.save_pretrained(out)
    tokenizer.save_pretrained(out)
    cfg_path = out / "config.json"
    data = {}
    if cfg_path.exists():
        try:
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data.update(
        {
            "abliterated": True,
            "abliterated_model_id": cfg.model_id,
            "abliteration_strength": cfg.strength,
        }
    )
    cfg_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    click.echo("[run] after eval")
    after = score_refusals(model, tokenizer, held_out, cfg)
    click.echo(f"[run] after refusal_rate={after['refusal_rate']:.3f} ({after['refused']}/{after['n']})")
    click.echo(
        json.dumps(
            {"before_refusal_rate": before["refusal_rate"], "after_refusal_rate": after["refusal_rate"]},
            indent=2,
        )
    )


@abliterate.command("steering")
@click.option("--model", required=True)
@click.option("--vector", required=True, help="Path to steering .pt")
@click.option("--strength", default=1.0, show_default=True, type=float)
@click.option("--layers", default="", show_default=True, help="Comma-separated layer indices")
@click.option("--device", default="cuda", show_default=True)
@click.option("--dtype", default="float16", show_default=True)
@click.option("--n-samples", default=8, show_default=True, type=int)
@click.option("--harmful-dataset", default="mlabonne/harmful_behaviors", show_default=True)
def steering_cmd(model, vector, strength, layers, device, dtype, n_samples, harmful_dataset):
    cfg = AbliterateConfig(
        model_id=model,
        device=device,
        dtype=dtype,
        n_samples=n_samples,
        harmful_dataset=harmful_dataset,
    )
    click.echo(f"[steering] loading model={model}")
    m, tok = load_model(cfg)
    layer_set = {int(s.strip()) for s in layers.split(",") if s.strip()} if layers else None
    dirs = load_steering(vector)
    if layer_set is None:
        layer_set = set(dirs.keys())
    rs = apply_steering_from_file(m, vector, strength=strength, layers=layer_set)
    click.echo(f"[steering] attached layers={sorted(rs.layers or [])} strength={strength}")
    harmful, _ = load_prompt_pairs(cfg)
    prompts = harmful[: min(8, len(harmful))]
    res = score_refusals(m, tok, prompts, cfg)
    rs.detach()
    click.echo(f"[steering] refusal_rate={res['refusal_rate']:.3f} ({res['refused']}/{res['n']})")


@abliterate.command("eval")
@click.option("--model", required=True)
@click.option("--device", default="cuda", show_default=True)
@click.option("--dtype", default="float16", show_default=True)
@click.option("--n-samples", default=8, show_default=True, type=int)
@click.option("--harmful-dataset", default="mlabonne/harmful_behaviors", show_default=True)
@click.option("--prompts-file", default=None, help="Text file with one prompt per line")
def eval_cmd(model, device, dtype, n_samples, harmful_dataset, prompts_file):
    cfg = AbliterateConfig(
        model_id=model,
        device=device,
        dtype=dtype,
        n_samples=n_samples,
        harmful_dataset=harmful_dataset,
    )
    if prompts_file:
        prompts = [
            line.strip()
            for line in Path(prompts_file).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ][:n_samples]
        click.echo(f"[eval] loaded prompts={len(prompts)} from {prompts_file}")
    else:
        click.echo(f"[eval] loading prompts n={n_samples}")
        harmful, _ = load_prompt_pairs(cfg)
        prompts = harmful[:n_samples]
    click.echo(f"[eval] loading model={model}")
    m, tok = load_model(cfg)
    res = score_refusals(m, tok, prompts, cfg)
    click.echo(f"[eval] refusal_rate={res['refusal_rate']:.3f} ({res['refused']}/{res['n']})")


@abliterate.command("info")
@click.option("--model", required=True)
@click.option("--device", default="cpu", show_default=True)
@click.option("--dtype", default="float32", show_default=True)
@click.option("--target-modules", default="o_proj,down_proj", show_default=True)
def info_cmd(model, device, dtype, target_modules):
    cfg = AbliterateConfig(
        model_id=model,
        device=device,
        dtype=dtype,
        target_modules=tuple(s.strip() for s in target_modules.split(",") if s.strip()),
    )
    click.echo(f"[info] loading model={model}")
    m, _ = load_model(cfg)
    layers = m.model.layers
    hidden = getattr(getattr(m, "config", None), "hidden_size", None)
    click.echo(f"[info] layers={len(layers)} hidden_size={hidden} dtype={dtype_from_str(dtype)}")
    if layers:
        layer0 = layers[0]
        resolved = {}
        for target in cfg.target_modules:
            try:
                mod = _resolve_module(layer0, target)
                resolved[target] = tuple(mod.weight.shape)
            except Exception as e:
                resolved[target] = f"error: {e}"
        click.echo(f"[info] target_modules(layer0)={json.dumps(resolved)}")


def main():
    abliterate()


if __name__ == "__main__":
    main()
