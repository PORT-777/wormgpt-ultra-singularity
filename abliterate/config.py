from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class AbliterateConfig:
    model_id: str
    device: str = "cuda"
    dtype: str = "float16"  # "float16" | "bfloat16" | "float32"
    harmful_dataset: str = "mlabonne/harmful_behaviors"
    harmless_dataset: str = "mlabonne/harmless_alpaca"
    n_samples: int = 128
    batch_size: int = 8
    max_prompt_tokens: int = 256
    target_modules: tuple[str, ...] = ("o_proj", "down_proj")
    strength: float = 1.0
    output_dir: str = "./abliterated"
    save_steering: bool = False

    @classmethod
    def from_args(cls, args: Any) -> "AbliterateConfig":
        fields = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        data: dict[str, Any] = {}
        for name in fields:
            if hasattr(args, name):
                val = getattr(args, name)
                if name == "target_modules" and isinstance(val, str):
                    val = tuple(s.strip() for s in val.split(",") if s.strip())
                if val is not None:
                    data[name] = val
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["target_modules"] = list(self.target_modules)
        return d
