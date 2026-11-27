import copy
import logging
import re
from typing import Dict, Tuple, Optional, Iterable

import torch

import folder_paths
import comfy.utils
import comfy.sd


# =========================================================
# Layer mapping: legacy Anima 28L -> Anima 2.9B 40L ONLY
# (All 52L / Anima 3.8B code removed for a clean 28L/40L setup)
# =========================================================
MAP_28_TO_40 = {
     0:  0,
     1:  1,
     2:  3,
     3:  4,
     4:  6,
     5:  7,
     6:  9,
     7: 10,
     8: 12,
     9: 13,
    10: 15,
    11: 16,
    12: 18,
    13: 19,
    14: 14 + 6,
    15: 22,
    16: 23,
    17: 25,
    18: 26,
    19: 28,
    20: 29,
    21: 31,
    22: 32,
    23: 34,
    24: 35,
    25: 37,
    26: 38,
    27: 39,
}

INSERTED_40 = [2, 5, 8, 11, 14, 17, 21, 24, 27, 30, 33, 36]

DOT_PATTERN = re.compile(r"(blocks\.)(\d+)(\.)")
US_PATTERN = re.compile(r"(blocks_)(\d+)(_)")
UP_PATTERNS = (".lora_up.weight", "_lora_up.weight", "lora_up.weight")


def is_llm_adapter_key(key: str) -> bool:
    return "llm_adapter" in key.lower()


def replace_block_index(key: str, new_idx) -> Tuple[str, Optional[int]]:
    if is_llm_adapter_key(key):
        return key, None

    m = DOT_PATTERN.search(key)
    if m:
        old_idx = int(m.group(2))
        return key[:m.start(2)] + str(new_idx) + key[m.end(2):], old_idx

    m = US_PATTERN.search(key)
    if m:
        old_idx = int(m.group(2))
        return key[:m.start(2)] + str(new_idx) + key[m.end(2):], old_idx

    return key, None


def get_block_index(key: str) -> Optional[int]:
    if is_llm_adapter_key(key):
        return None

    m = DOT_PATTERN.search(key)
    if m:
        return int(m.group(2))

    m = US_PATTERN.search(key)
    if m:
        return int(m.group(2))

    return None


def normalize_signature(key: str) -> str:
    out, _ = replace_block_index(key, "{BLOCK}")
    return out


def clone_tensor(x):
    if torch.is_tensor(x):
        return x.clone()
    return copy.deepcopy(x)


def blend_tensors(a, b, ratio_prev=0.5, ratio_next=0.5):
    if a is None and b is None:
        return None
    if a is None:
        return clone_tensor(b)
    if b is None:
        return clone_tensor(a)
    if not torch.is_tensor(a) or not torch.is_tensor(b):
        return clone_tensor(a)
    if a.shape != b.shape:
        return clone_tensor(a)
    return (a.float() * ratio_prev + b.float() * ratio_next).to(a.dtype)


def is_attention_related_key(key: str) -> bool:
    k = key.lower()
    return ("self_attn" in k) or ("cross_attn" in k) or ("attn" in k and "mlp" not in k)


def is_mlp_related_key(key: str) -> bool:
    return "mlp" in key.lower()


def should_include_inserted_key(key: str, inserted_scope: str) -> bool:
    scope = inserted_scope.lower()
    if scope == "all":
        return True
    if scope == "attn_only":
        return is_attention_related_key(key)
    if scope == "attn_and_mlp":
        return is_attention_related_key(key) or is_mlp_related_key(key)
    return True


def scaled_for_inserted(key: str, value, inserted_strength: float):
    if not torch.is_tensor(value):
        return value
    lk = key.lower()
    if any(p in lk for p in UP_PATTERNS):
        return (value.float() * inserted_strength).to(value.dtype)
    return value.clone()


def select_source_tensor(
    sig: str,
    prev_map: Dict[str, Tuple[str, object]],
    next_map: Dict[str, Tuple[str, object]],
    mode: str,
):
    prev_item = prev_map.get(sig)
    next_item = next_map.get(sig)

    prev_key = prev_item[0] if prev_item else None
    prev_val = prev_item[1] if prev_item else None
    next_key = next_item[0] if next_item else None
    next_val = next_item[1] if next_item else None

    mode = mode.lower()
    if mode == "copy_prev":
        if prev_item is not None:
            return prev_key, clone_tensor(prev_val)
        if next_item is not None:
            return next_key, clone_tensor(next_val)
        return None, None

    if mode == "copy_next":
        if next_item is not None:
            return next_key, clone_tensor(next_val)
        if prev_item is not None:
            return prev_key, clone_tensor(prev_val)
        return None, None

    if mode == "blend":
        if prev_item is None and next_item is None:
            return None, None
        source_key = prev_key if prev_key is not None else next_key
        return source_key, blend_tensors(prev_val, next_val, 0.5, 0.5)

    if mode == "sharp_blend":
        if prev_item is None and next_item is None:
            return None, None
        source_key = prev_key if prev_key is not None else next_key
        return source_key, blend_tensors(prev_val, next_val, 0.7, 0.3)

    if prev_item is not None:
        return prev_key, clone_tensor(prev_val)
    if next_item is not None:
        return next_key, clone_tensor(next_val)
    return None, None


def build_inserted_neighbors(anchor_map: Dict[int, int], inserted_blocks: Iterable[int]):
    sorted_pairs = sorted(anchor_map.items(), key=lambda x: x[1])
    result = {}
    for inserted in inserted_blocks:
        prev_pair = None
        next_pair = None
        for old_idx, new_idx in sorted_pairs:
            if new_idx < inserted:
                prev_pair = (old_idx, new_idx)
            elif new_idx > inserted and next_pair is None:
                next_pair = (old_idx, new_idx)
                break
        if prev_pair is None or next_pair is None:
            raise RuntimeError(f"Could not determine neighbors for inserted block {inserted}")
        result[inserted] = (prev_pair[0], next_pair[0])
    return result


NEIGHBORS_40 = build_inserted_neighbors(MAP_28_TO_40, INSERTED_40)


def remap_28_to_40(
    lora_sd: Dict[str, object],
    inserted_mode: str = "copy_prev",
    inserted_strength: float = 0.18,
    inserted_scope: str = "attn_only",
):
    out = {}
    collisions = []
    remapped_count = 0
    inserted_count = 0
    examples = []

    source_entries = {i: {} for i in range(28)}

    for key, value in lora_sd.items():
        old_idx = get_block_index(key)
        if old_idx is None or old_idx not in MAP_28_TO_40:
            if key in out:
                collisions.append((key, key))
            out[key] = clone_tensor(value)
            continue

        new_idx = MAP_28_TO_40[old_idx]
        new_key, _ = replace_block_index(key, new_idx)

        if new_key in out and new_key != key:
            collisions.append((key, new_key))
        else:
            out[new_key] = clone_tensor(value)
            remapped_count += 1
            if len(examples) < 10:
                examples.append(f"anchor {old_idx:02d}->{new_idx:02d}: {key} -> {new_key}")

        sig = normalize_signature(key)
        source_entries[old_idx][sig] = (key, value)

    effective_mode = "copy_prev" if inserted_mode == "disabled" else inserted_mode
    effective_strength = 0.0 if inserted_mode == "disabled" else inserted_strength

    for inserted_new in INSERTED_40:
        prev_old, next_old = NEIGHBORS_40[inserted_new]
        prev_map = source_entries.get(prev_old, {})
        next_map = source_entries.get(next_old, {})
        signatures = sorted(set(prev_map.keys()) | set(next_map.keys()))

        for sig in signatures:
            any_source_key = prev_map[sig][0] if sig in prev_map else (next_map[sig][0] if sig in next_map else None)
            if any_source_key is None or not should_include_inserted_key(any_source_key, inserted_scope):
                continue

            source_key, tensor_val = select_source_tensor(sig, prev_map, next_map, effective_mode)
            if source_key is None or tensor_val is None:
                continue

            inserted_key, _ = replace_block_index(source_key, inserted_new)
            if inserted_key in out:
                collisions.append((source_key, inserted_key))
                continue

            out[inserted_key] = scaled_for_inserted(inserted_key, tensor_val, effective_strength)
            inserted_count += 1

    if collisions:
        preview = "\n".join(f"{a} -> {b}" for a, b in collisions[:12])
        raise RuntimeError(f"Legacy Anima LoRA remap produced collisions:\n{preview}")

    return out, remapped_count, inserted_count, examples


class Anima29LegacyLoRALoaderSharp:
    """
    Smart Anima 2.9B (40L) LoRA Loader:
    - Standard 28L Anima LoRA -> remaps 28L -> 40L on the fly.
    - Native/Remapped 40L Anima-2.9B LoRA (max_block >= 28 or '29b' in name) -> loads directly without double remapping.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "lora_name": (folder_paths.get_filename_list("loras"),),
                "strength_model": ("FLOAT", {"default": 0.75, "min": -5.0, "max": 5.0, "step": 0.01}),
                "inserted_strength": ("FLOAT", {"default": 0.18, "min": 0.0, "max": 1.0, "step": 0.01}),
                "inserted_mode": (["copy_prev", "sharp_blend", "blend", "copy_next", "disabled"],),
                "inserted_scope": (["attn_only", "attn_and_mlp", "all"],),
            }
        }

    RETURN_TYPES = ("MODEL", "STRING")
    RETURN_NAMES = ("model", "report")
    FUNCTION = "load_legacy_lora"
    CATEGORY = "Anima/2.9B LoRA"

    def load_legacy_lora(
        self,
        model,
        lora_name,
        strength_model,
        inserted_strength,
        inserted_mode,
        inserted_scope,
    ):
        lora_path = folder_paths.get_full_path_or_raise("loras", lora_name)
        lora_sd = comfy.utils.load_torch_file(lora_path, safe_load=True)
        original_count = len(lora_sd)

        indices = [idx for k in lora_sd.keys() if (idx := get_block_index(k)) is not None]
        max_idx = max(indices) if indices else -1
        is_already_40l = (max_idx >= 28) or bool(re.search(r"2\.?9b", str(lora_name), re.I))

        if not indices or is_already_40l:
            model_out, _ = comfy.sd.load_lora_for_models(model, None, lora_sd, strength_model, 0.0)
            report = (
                f"Anima 2.9B Direct Pass-Through (max_block={max_idx})\n"
                f"LoRA: {lora_name} | strength={strength_model} | entries={original_count}"
            )
            logging.info(report)
            return (model_out, report)

        remapped_sd, remapped_count, inserted_count, examples = remap_28_to_40(
            lora_sd,
            inserted_mode=inserted_mode,
            inserted_strength=inserted_strength,
            inserted_scope=inserted_scope,
        )

        model_out, _ = comfy.sd.load_lora_for_models(model, None, remapped_sd, strength_model, 0.0)
        report = (
            f"Anima 2.9B Bridge: 28L -> 40L\n"
            f"LoRA: {lora_name} | strength={strength_model}\n"
            f"40L inserted: {inserted_mode} / {inserted_strength} / {inserted_scope}\n"
            f"Entries: {original_count} -> anchor={remapped_count}, synthetic={inserted_count}"
        )
        logging.info(report)
        return (model_out, report)


NODE_CLASS_MAPPINGS = {
    "Anima29LegacyLoRALoader": Anima29LegacyLoRALoaderSharp,
    "Anima29LegacyLoRALoaderSharp": Anima29LegacyLoRALoaderSharp,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Anima29LegacyLoRALoader": "Anima 2.9B Smart LoRA Loader (28L -> 40L)",
    "Anima29LegacyLoRALoaderSharp": "Anima 2.9B Smart LoRA Loader (28L -> 40L)",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
