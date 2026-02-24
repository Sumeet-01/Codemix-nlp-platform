"""
Multi-Task Transformer Model Architecture
XLM-RoBERTa with dual classification heads for sarcasm + misinformation.
"""
from dataclasses import dataclass
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import (
    AutoModel,
    AutoConfig,
    PreTrainedModel,
    XLMRobertaConfig,
)
from transformers.modeling_outputs import ModelOutput


@dataclass
class MultiTaskOutput(ModelOutput):
    """Output class for multi-task model."""
    loss: Optional[torch.FloatTensor] = None
    sarcasm_logits: torch.FloatTensor = None
    misinfo_logits: torch.FloatTensor = None
    hidden_states: Optional[tuple] = None
    attentions: Optional[tuple] = None


class ClassificationHead(nn.Module):
    """
    Classification head with dropout and LayerNorm for stability.
    Uses two-layer MLP with GELU activation.
    """

    def __init__(self, hidden_size: int, num_labels: int = 2, dropout: float = 0.1) -> None:
        super().__init__()
        self.dense = nn.Linear(hidden_size, hidden_size // 2)
        self.norm = nn.LayerNorm(hidden_size // 2)
        self.dropout = nn.Dropout(dropout)
        self.out_proj = nn.Linear(hidden_size // 2, num_labels)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.dropout(x)
        x = self.dense(x)
        x = F.gelu(x)
        x = self.norm(x)
        x = self.dropout(x)
        x = self.out_proj(x)
        return x


class MultiTaskCodeMixModel(nn.Module):
    """
    Multi-task model for sarcasm and misinformation detection.
    
    Architecture:
    - Shared XLM-RoBERTa-large encoder (frozen lower layers)
    - Independent classification heads for each task
    - [CLS] token representation used for classification
    
    Multi-task Loss:
    loss = sarcasm_weight * sarcasm_loss + misinfo_weight * misinfo_loss
    """

    def __init__(
        self,
        model_name: str = "xlm-roberta-large",
        num_labels: int = 2,
        dropout: float = 0.1,
        sarcasm_weight: float = 0.5,
        misinfo_weight: float = 0.5,
        freeze_layers: int = 6,  # Freeze first N transformer layers
    ) -> None:
        super().__init__()
        self.model_name = model_name
        self.sarcasm_weight = sarcasm_weight
        self.misinfo_weight = misinfo_weight

        # Load pre-trained encoder
        self.encoder = AutoModel.from_pretrained(model_name)
        config = self.encoder.config
        hidden_size = config.hidden_size

        # Freeze embedding and lower transformer layers for efficiency
        self._freeze_layers(freeze_layers)

        # Task-specific classification heads
        self.sarcasm_head = ClassificationHead(hidden_size, num_labels, dropout)
        self.misinfo_head = ClassificationHead(hidden_size, num_labels, dropout)

        # Initialize heads with small weights
        self._init_weights(self.sarcasm_head)
        self._init_weights(self.misinfo_head)

    def _freeze_layers(self, num_layers: int) -> None:
        """Freeze embedding and first N transformer layers."""
        # Freeze embeddings
        for param in self.encoder.embeddings.parameters():
            param.requires_grad = False

        # Freeze first N encoder layers
        if hasattr(self.encoder, "encoder"):
            layers = self.encoder.encoder.layer
            for i, layer in enumerate(layers):
                if i < num_layers:
                    for param in layer.parameters():
                        param.requires_grad = False

    def _init_weights(self, module: nn.Module) -> None:
        """Initialize classification head weights."""
        for m in module.modules():
            if isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, mean=0.0, std=0.02)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        token_type_ids: Optional[torch.Tensor] = None,
        sarcasm_labels: Optional[torch.Tensor] = None,
        misinfo_labels: Optional[torch.Tensor] = None,
        output_attentions: bool = False,
        output_hidden_states: bool = False,
    ) -> MultiTaskOutput:
        """Forward pass."""
        # Encode
        outputs = self.encoder(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
        )

        # Use [CLS] token (first token)
        cls_repr = outputs.last_hidden_state[:, 0, :]

        # Task predictions
        sarcasm_logits = self.sarcasm_head(cls_repr)
        misinfo_logits = self.misinfo_head(cls_repr)

        # Compute multi-task loss
        loss = None
        if sarcasm_labels is not None and misinfo_labels is not None:
            loss_fn = nn.CrossEntropyLoss()
            sarcasm_loss = loss_fn(sarcasm_logits, sarcasm_labels)
            misinfo_loss = loss_fn(misinfo_logits, misinfo_labels)
            loss = (self.sarcasm_weight * sarcasm_loss) + (self.misinfo_weight * misinfo_loss)

        return MultiTaskOutput(
            loss=loss,
            sarcasm_logits=sarcasm_logits,
            misinfo_logits=misinfo_logits,
            hidden_states=outputs.hidden_states if output_hidden_states else None,
            attentions=outputs.attentions if output_attentions else None,
        )

    def predict(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
    ) -> dict:
        """Run inference and return probabilities."""
        with torch.no_grad():
            outputs = self.forward(input_ids, attention_mask)

        sarcasm_probs = F.softmax(outputs.sarcasm_logits, dim=-1)
        misinfo_probs = F.softmax(outputs.misinfo_logits, dim=-1)

        return {
            "sarcasm_probs": sarcasm_probs.cpu().numpy().tolist(),
            "misinfo_probs": misinfo_probs.cpu().numpy().tolist(),
            "sarcasm_label": sarcasm_probs[:, 1].argmax().item() >= 0.5,
            "misinfo_label": misinfo_probs[:, 1].argmax().item() >= 0.5,
        }

    def save_pretrained(self, save_path: str) -> None:
        """Save model and heads to directory."""
        import os
        os.makedirs(save_path, exist_ok=True)

        # Save encoder
        self.encoder.save_pretrained(save_path)

        # Save task heads separately
        heads_state = {
            "sarcasm_head": self.sarcasm_head.state_dict(),
            "misinfo_head": self.misinfo_head.state_dict(),
            "config": {
                "model_name": self.model_name,
                "sarcasm_weight": self.sarcasm_weight,
                "misinfo_weight": self.misinfo_weight,
            },
        }
        torch.save(heads_state, os.path.join(save_path, "task_heads.pt"))
        print(f"Model saved to {save_path}")
