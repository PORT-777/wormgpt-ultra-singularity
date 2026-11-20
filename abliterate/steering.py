from __future__ import annotations

from typing import Any

import torch


class RefusalSteering:
    def __init__(
        self,
        direction: torch.Tensor,
        strength: float = 1.0,
        layers: set[int] | None = None,
    ):
        self.direction = direction.reshape(-1).float()
        self.strength = float(strength)
        self.layers = set(layers) if layers is not None else None
        self._handles: list[Any] = []

    def attach(self, model: Any) -> None:
        self.detach()
        decoder_layers = model.model.layers
        for i, layer in enumerate(decoder_layers):
            if self.layers is not None and i not in self.layers:
                continue
            self._handles.append(layer.register_forward_hook(self._make_hook()))

    def detach(self) -> None:
        for h in self._handles:
            h.remove()
        self._handles.clear()

    def _make_hook(self):
        def _hook(module, inp, out):
            hidden = out[0] if isinstance(out, tuple) else out
            r = self.direction.to(device=hidden.device, dtype=hidden.dtype)
            coeff = torch.matmul(hidden, r)
            steered = hidden - self.strength * coeff.unsqueeze(-1) * r
            if isinstance(out, tuple):
                return (steered,) + out[1:]
            return steered

        return _hook


def save_steering(path: str, directions: dict[int, torch.Tensor]) -> None:
    payload = {int(k): v.detach().cpu().float() for k, v in directions.items()}
    torch.save(payload, path)


def load_steering(path: str) -> dict[int, torch.Tensor]:
    data = torch.load(path, map_location="cpu", weights_only=True)
    return {int(k): v.float() for k, v in data.items()}


def apply_steering_from_file(
    model: Any, path: str, strength: float, layers: set[int] | None = None
) -> RefusalSteering:
    directions = load_steering(path)
    if layers is None:
        layers = set(directions.keys())
    selected = {i for i in layers if i in directions}
    if not selected:
        raise ValueError(f"No matching layers between file and requested layers={layers}")
    # Use a single averaged direction when multiple layers selected for simplicity and stability.
    vecs = torch.stack([directions[i] for i in sorted(selected)], dim=0)
    direction = vecs.mean(0)
    direction = direction / direction.norm().clamp(min=1e-12)
    steering = RefusalSteering(direction=direction, strength=strength, layers=selected)
    steering.attach(model)
    return steering
