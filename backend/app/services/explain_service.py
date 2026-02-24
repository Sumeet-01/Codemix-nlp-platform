"""
Explainability Service - SHAP and Attention Visualization
Returns data matching ExplanationResponse / ShapValue frontend interfaces.
"""
import random
from typing import Optional

import structlog
import numpy as np

from app.core.config import settings

logger = structlog.get_logger(__name__)


def _build_shap_values(tokens, sarcasm_vals, misinfo_vals):
    return [
        {"token": t, "sarcasm_score": round(s, 4), "misinfo_score": round(m, 4)}
        for t, s, m in zip(tokens, sarcasm_vals, misinfo_vals)
    ]


class ExplainabilityService:
    """Works in DEMO_MODE without torch."""

    async def get_full_explanation(self, text, analysis_id, ml_service_instance) -> dict:
        if not ml_service_instance.is_loaded:
            raise RuntimeError("ML model not loaded")

        base = await ml_service_instance.predict(text)
        tokens = [t for t in base.get("tokens", text.split()[:18])
                  if t not in {"<s>", "</s>", "<pad>", "<unk>"}] or text.split()[:15]

        if settings.DEMO_MODE or ml_service_instance.model is None:
            return self._demo_explanation(text, str(analysis_id), tokens, base)
        return await self._real_explanation(text, str(analysis_id), tokens, base, ml_service_instance)

    def _demo_explanation(self, text, analysis_id, tokens, base):
        """
        Intelligent SHAP-like explanation using the same linguistic rules
        as the predictor. Tokens that match sarcasm/misinfo patterns get
        high positive scores; neutral/opposing tokens get negative scores.
        """
        from app.services.ml_service import (
            _SARCASM_WORDS, _SARCASM_EMOJIS, _SARCASM_EMOJI_TOKENS,
            _POSITIVE_WORDS, _NEGATIVE_WORDS,
            _MISINFO_WORDS, _CREDIBILITY_WORDS, _POLITICAL_REFS,
        )

        rng = random.Random(hash(text) % (2 ** 32))
        sarcasm_vals = []
        misinfo_vals = []

        all_lower = [tt.lower() for tt in tokens]
        any_neg = any(nt in all_lower for nt in _NEGATIVE_WORDS)
        any_pos = any(pt in all_lower for pt in _POSITIVE_WORDS)
        any_political = any(pt in all_lower for pt in _POLITICAL_REFS)

        for tok in tokens:
            t = tok.lower().strip("[]")
            # --- Sarcasm SHAP score ---
            s_val = 0.0
            if t in _SARCASM_WORDS:
                s_val = rng.uniform(0.55, 0.95)
            elif tok in _SARCASM_EMOJIS or tok.upper() in _SARCASM_EMOJI_TOKENS:
                s_val = rng.uniform(0.65, 0.95)
            elif t in _POLITICAL_REFS:
                # Political refs are sarcasm signals when paired with positive words
                s_val = rng.uniform(0.45, 0.80) if any_pos else rng.uniform(-0.05, 0.20)
            elif t in _POSITIVE_WORDS:
                # Positive words in sarcastic context push toward sarcasm
                s_val = rng.uniform(0.50, 0.85) if (any_neg or any_political) else rng.uniform(-0.15, 0.15)
            elif t in _NEGATIVE_WORDS:
                s_val = rng.uniform(0.35, 0.70) if any_pos else rng.uniform(-0.10, 0.10)
            else:
                s_val = rng.uniform(-0.25, 0.15)

            # --- Misinfo SHAP score ---
            m_val = 0.0
            if t in _MISINFO_WORDS:
                m_val = rng.uniform(0.50, 0.90)
            elif t in {"share", "forward", "send", "deleted", "removed", "banned", "censored"}:
                m_val = rng.uniform(0.45, 0.85)
            elif t in {"scientists", "scientist", "doctors", "doctor", "discovered", "confirmed", "proved"}:
                m_val = rng.uniform(0.40, 0.80)
            elif t in _CREDIBILITY_WORDS:
                m_val = rng.uniform(-0.60, -0.30)
            else:
                m_val = rng.uniform(-0.20, 0.10)

            sarcasm_vals.append(s_val)
            misinfo_vals.append(m_val)

        # Normalize to [-0.95, 0.95]
        def _norm(vals):
            mx = max(abs(v) for v in vals) if vals else 1.0
            if mx == 0:
                return vals
            return [v / mx * 0.95 for v in vals]

        sarcasm_vals = _norm(sarcasm_vals)
        misinfo_vals = _norm(misinfo_vals)
        shap_values = _build_shap_values(tokens, sarcasm_vals, misinfo_vals)
        top_sarcasm = sorted(shap_values, key=lambda x: abs(x["sarcasm_score"]), reverse=True)[:5]
        top_misinfo = sorted(shap_values, key=lambda x: abs(x["misinfo_score"]), reverse=True)[:5]

        n = min(len(tokens), 8)
        attn = []
        for _ in range(n):
            row = [rng.uniform(0.01, 0.3) for _ in range(n)]
            s = sum(row)
            attn.append([v / s for v in row])

        return {
            "analysis_id": analysis_id, "tokens": tokens,
            "shap_values": shap_values, "attention_weights": attn,
            "top_sarcasm_tokens": top_sarcasm, "top_misinfo_tokens": top_misinfo,
            "confidence": {"sarcasm": round(base["sarcasm_score"], 4),
                           "misinformation": round(base["misinformation_score"], 4)},
            "method": "demo-occlusion",
        }

    async def _real_explanation(self, text, analysis_id, tokens, base, ml_service_instance):
        try:
            import torch
            import torch.nn.functional as F
            base_s, base_m = base["sarcasm_score"], base["misinformation_score"]
            inputs = ml_service_instance.tokenizer(
                ml_service_instance.preprocess_text(text),
                return_tensors="pt", max_length=128, truncation=True, padding=True)
            input_ids = inputs["input_ids"][0].clone()
            mask_id = ml_service_instance.tokenizer.mask_token_id or 0
            device = getattr(ml_service_instance, "_device", torch.device("cpu"))
            sarcasm_vals, misinfo_vals = [], []
            with torch.no_grad():
                for idx in range(len(input_ids)):
                    masked = input_ids.clone(); masked[idx] = mask_id
                    out = ml_service_instance.model(
                        input_ids=masked.unsqueeze(0).to(device),
                        attention_mask=inputs["attention_mask"].to(device))
                    sarcasm_vals.append(base_s - F.softmax(out["sarcasm_logits"], dim=-1)[0][1].item())
                    misinfo_vals.append(base_m - F.softmax(out["misinfo_logits"], dim=-1)[0][1].item())

            def _norm(vals):
                arr = np.array(vals); mx = np.abs(arr).max()
                return (arr / mx * 0.95).tolist() if mx > 0 else list(vals)

            sarcasm_vals = _norm(sarcasm_vals); misinfo_vals = _norm(misinfo_vals)
            shap_values = _build_shap_values(tokens, sarcasm_vals[:len(tokens)], misinfo_vals[:len(tokens)])
        except Exception as exc:
            logger.warning("Real SHAP failed, using demo fallback", error=str(exc))
            return self._demo_explanation(text, analysis_id, tokens, base)

        top_sarcasm = sorted(shap_values, key=lambda x: abs(x["sarcasm_score"]), reverse=True)[:5]
        top_misinfo = sorted(shap_values, key=lambda x: abs(x["misinfo_score"]), reverse=True)[:5]
        return {
            "analysis_id": analysis_id, "tokens": tokens,
            "shap_values": shap_values, "attention_weights": [],
            "top_sarcasm_tokens": top_sarcasm, "top_misinfo_tokens": top_misinfo,
            "confidence": {"sarcasm": round(base["sarcasm_score"], 4),
                           "misinformation": round(base["misinformation_score"], 4)},
            "method": "occlusion",
        }


explain_service = ExplainabilityService()
