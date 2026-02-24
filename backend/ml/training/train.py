"""
Training Script for CodeMix NLP - Multi-Task Sarcasm & Misinformation Detection
Trains XLM-RoBERTa-large with dual classification heads.
"""
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    EarlyStoppingCallback,
    set_seed,
)
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix,
    classification_report,
)
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from backend.ml.models.multitask_model import MultiTaskCodeMixModel

# =============================================================================
# Configuration
# =============================================================================
@dataclass
class TrainingConfig:
    model_name: str = "xlm-roberta-large"
    max_length: int = 128
    batch_size: int = 16
    eval_batch_size: int = 32
    num_epochs: int = 5
    learning_rate: float = 2e-5
    weight_decay: float = 0.01
    warmup_steps: int = 500
    gradient_accumulation_steps: int = 2
    max_grad_norm: float = 1.0
    seed: int = 42
    freeze_layers: int = 6
    early_stopping_patience: int = 2
    data_dir: str = "ml/data/processed"
    output_dir: str = "ml/models/checkpoints"
    logging_steps: int = 50
    eval_steps: int = 200
    save_total_limit: int = 3

    # Computed
    @property
    def device(self) -> torch.device:
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")


config = TrainingConfig()

# =============================================================================
# Dataset
# =============================================================================
class CodeMixDataset(Dataset):
    """PyTorch Dataset for code-mixed text classification."""

    def __init__(
        self,
        data: list[dict],
        tokenizer,
        max_length: int = 128,
    ) -> None:
        self.data = data
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> dict:
        item = self.data[idx]
        text = item["text"]

        encoding = self.tokenizer(
            text,
            max_length=self.max_length,
            truncation=True,
            padding="max_length",
            return_tensors="pt",
        )

        return {
            "input_ids": encoding["input_ids"].squeeze(),
            "attention_mask": encoding["attention_mask"].squeeze(),
            "sarcasm_labels": torch.tensor(item["sarcasm"], dtype=torch.long),
            "misinfo_labels": torch.tensor(item["misinformation"], dtype=torch.long),
        }


def load_data(data_dir: str) -> tuple[list, list, list]:
    """Load train/val/test data from CSV files."""
    data_path = Path(data_dir)

    def read_csv(path: Path) -> list[dict]:
        if path.exists():
            df = pd.read_csv(path)
            return df.to_dict(orient="records")
        return []

    train = read_csv(data_path / "train.csv")
    val = read_csv(data_path / "val.csv")
    test = read_csv(data_path / "test.csv")

    if not train:
        # Auto-generate dataset if not found
        print("No data found. Generating synthetic dataset...")
        import subprocess
        subprocess.run(
            ["python", "ml/data/preprocess.py"],
            check=True,
        )
        train = read_csv(data_path / "train.csv")
        val = read_csv(data_path / "val.csv")
        test = read_csv(data_path / "test.csv")

    print(f"Loaded: train={len(train)}, val={len(val)}, test={len(test)}")
    return train, val, test


# =============================================================================
# Metrics
# =============================================================================
def compute_metrics_multitask(eval_pred) -> dict:
    """Compute metrics for multi-task model during training."""
    logits, labels = eval_pred
    # logits shape: (2, N, 2) - [sarcasm_logits, misinfo_logits]
    # labels shape: (2, N)

    if isinstance(logits, (list, tuple)) and len(logits) == 2:
        sarcasm_logits, misinfo_logits = logits[0], logits[1]
        sarcasm_labels, misinfo_labels = labels[0], labels[1]
    else:
        # Fallback
        return {}

    sarcasm_preds = np.argmax(sarcasm_logits, axis=-1)
    misinfo_preds = np.argmax(misinfo_logits, axis=-1)

    # Sarcasm metrics
    s_prec, s_rec, s_f1, _ = precision_recall_fscore_support(
        sarcasm_labels, sarcasm_preds, average="binary"
    )
    s_acc = accuracy_score(sarcasm_labels, sarcasm_preds)

    # Misinformation metrics
    m_prec, m_rec, m_f1, _ = precision_recall_fscore_support(
        misinfo_labels, misinfo_preds, average="binary"
    )
    m_acc = accuracy_score(misinfo_labels, misinfo_preds)

    return {
        "sarcasm_accuracy": s_acc,
        "sarcasm_f1": s_f1,
        "sarcasm_precision": s_prec,
        "sarcasm_recall": s_rec,
        "misinfo_accuracy": m_acc,
        "misinfo_f1": m_f1,
        "misinfo_precision": m_prec,
        "misinfo_recall": m_rec,
        "overall_f1": (s_f1 + m_f1) / 2,
    }


# =============================================================================
# Custom Trainer for Multi-Task
# =============================================================================
class MultiTaskTrainer(Trainer):
    """Custom HuggingFace Trainer for multi-task learning."""

    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        """Compute multi-task loss."""
        sarcasm_labels = inputs.pop("sarcasm_labels", None)
        misinfo_labels = inputs.pop("misinfo_labels", None)

        outputs = model(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            sarcasm_labels=sarcasm_labels,
            misinfo_labels=misinfo_labels,
        )

        loss = outputs.loss
        return (loss, outputs) if return_outputs else loss

    def prediction_step(self, model, inputs, prediction_loss_only, ignore_keys=None):
        """Override prediction step for multi-task outputs."""
        with torch.no_grad():
            sarcasm_labels = inputs.get("sarcasm_labels")
            misinfo_labels = inputs.get("misinfo_labels")

            outputs = model(
                input_ids=inputs["input_ids"].to(model.device if hasattr(model, 'device') else self.args.device),
                attention_mask=inputs["attention_mask"].to(model.device if hasattr(model, 'device') else self.args.device),
                sarcasm_labels=sarcasm_labels.to(model.device if hasattr(model, 'device') else self.args.device) if sarcasm_labels is not None else None,
                misinfo_labels=misinfo_labels.to(model.device if hasattr(model, 'device') else self.args.device) if misinfo_labels is not None else None,
            )

        loss = outputs.loss
        logits = (
            outputs.sarcasm_logits.detach().cpu().numpy(),
            outputs.misinfo_logits.detach().cpu().numpy(),
        )
        labels = (
            sarcasm_labels.detach().cpu().numpy() if sarcasm_labels is not None else None,
            misinfo_labels.detach().cpu().numpy() if misinfo_labels is not None else None,
        )

        return loss, logits, labels


# =============================================================================
# Training Functions
# =============================================================================
def evaluate_model(
    model: MultiTaskCodeMixModel,
    tokenizer,
    test_data: list[dict],
    config: TrainingConfig,
    output_dir: str,
) -> dict:
    """Evaluate model on test set and generate confusion matrices."""
    model.eval()
    device = config.device
    model.to(device)

    dataset = CodeMixDataset(test_data, tokenizer, config.max_length)
    loader = DataLoader(dataset, batch_size=config.eval_batch_size, num_workers=0)

    all_sarcasm_preds, all_sarcasm_labels = [], []
    all_misinfo_preds, all_misinfo_labels = [], []

    with torch.no_grad():
        for batch in loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask)

            s_preds = torch.argmax(outputs.sarcasm_logits, dim=-1).cpu().numpy()
            m_preds = torch.argmax(outputs.misinfo_logits, dim=-1).cpu().numpy()

            all_sarcasm_preds.extend(s_preds.tolist())
            all_sarcasm_labels.extend(batch["sarcasm_labels"].numpy().tolist())
            all_misinfo_preds.extend(m_preds.tolist())
            all_misinfo_labels.extend(batch["misinfo_labels"].numpy().tolist())

    # Print reports
    print("\n=== Sarcasm Detection Results ===")
    print(classification_report(all_sarcasm_labels, all_sarcasm_preds, target_names=["Not Sarcastic", "Sarcastic"]))

    print("\n=== Misinformation Detection Results ===")
    print(classification_report(all_misinfo_labels, all_misinfo_preds, target_names=["Real", "Misinformation"]))

    # Save confusion matrices
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    for ax, labels, preds, title in [
        (axes[0], all_sarcasm_labels, all_sarcasm_preds, "Sarcasm Detection"),
        (axes[1], all_misinfo_labels, all_misinfo_preds, "Misinformation Detection"),
    ]:
        cm = confusion_matrix(labels, preds)
        im = ax.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
        ax.set_title(title)
        plt.colorbar(im, ax=ax)
        classes = ["Negative", "Positive"]
        tick_marks = range(len(classes))
        ax.set_xticks(tick_marks)
        ax.set_xticklabels(classes)
        ax.set_yticks(tick_marks)
        ax.set_yticklabels(classes)
        ax.set_ylabel("True Label")
        ax.set_xlabel("Predicted Label")
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                        color="white" if cm[i, j] > cm.max() / 2 else "black")

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "confusion_matrices.png"), dpi=150)
    plt.close()
    print(f"\nConfusion matrices saved to {output_dir}/confusion_matrices.png")

    # Compute final metrics
    s_prec, s_rec, s_f1, _ = precision_recall_fscore_support(
        all_sarcasm_labels, all_sarcasm_preds, average="binary"
    )
    m_prec, m_rec, m_f1, _ = precision_recall_fscore_support(
        all_misinfo_labels, all_misinfo_preds, average="binary"
    )

    return {
        "sarcasm": {"f1": s_f1, "precision": s_prec, "recall": s_rec},
        "misinformation": {"f1": m_f1, "precision": m_prec, "recall": m_rec},
        "overall_f1": (s_f1 + m_f1) / 2,
    }


def train(config: TrainingConfig) -> None:
    """Main training function."""
    set_seed(config.seed)
    device = config.device
    print(f"\nDevice: {device}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")

    # Create output directories
    os.makedirs(config.output_dir, exist_ok=True)
    os.makedirs(os.path.join(config.output_dir, "best_model"), exist_ok=True)

    # Load data
    train_data, val_data, test_data = load_data(config.data_dir)

    # Initialize tokenizer
    print(f"\nLoading tokenizer: {config.model_name}")
    tokenizer = AutoTokenizer.from_pretrained(config.model_name)

    # Create datasets
    train_dataset = CodeMixDataset(train_data, tokenizer, config.max_length)
    val_dataset = CodeMixDataset(val_data, tokenizer, config.max_length)

    # Initialize model
    print(f"Loading model: {config.model_name}")
    model = MultiTaskCodeMixModel(
        model_name=config.model_name,
        freeze_layers=config.freeze_layers,
    )
    model.to(device)

    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Total parameters: {total_params:,}")
    print(f"Trainable parameters: {trainable_params:,} ({trainable_params/total_params*100:.1f}%)")

    # Training arguments
    training_args = TrainingArguments(
        output_dir=config.output_dir,
        num_train_epochs=config.num_epochs,
        per_device_train_batch_size=config.batch_size,
        per_device_eval_batch_size=config.eval_batch_size,
        learning_rate=config.learning_rate,
        weight_decay=config.weight_decay,
        warmup_steps=config.warmup_steps,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        max_grad_norm=config.max_grad_norm,
        evaluation_strategy="steps",
        eval_steps=config.eval_steps,
        save_strategy="steps",
        save_steps=config.eval_steps,
        logging_steps=config.logging_steps,
        load_best_model_at_end=True,
        metric_for_best_model="overall_f1",
        greater_is_better=True,
        save_total_limit=config.save_total_limit,
        seed=config.seed,
        dataloader_num_workers=0,
        report_to="none",  # Disable wandb by default
        fp16=torch.cuda.is_available(),
    )

    # Trainer
    trainer = MultiTaskTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics_multitask,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=config.early_stopping_patience)],
    )

    # Train
    print("\n" + "="*60)
    print("  Starting Training")
    print("="*60)
    train_result = trainer.train()

    print("\nTraining completed!")
    print(f"  Total steps: {train_result.global_step}")
    print(f"  Train loss: {train_result.training_loss:.4f}")

    # Save best model
    best_model_path = os.path.join(config.output_dir, "best_model")
    model.save_pretrained(best_model_path)
    tokenizer.save_pretrained(best_model_path)
    print(f"\nBest model saved to: {best_model_path}")

    # Evaluate on test set
    print("\n" + "="*60)
    print("  Evaluating on Test Set")
    print("="*60)
    test_metrics = evaluate_model(model, tokenizer, test_data, config, config.output_dir)

    # Save metrics
    metrics_path = os.path.join(config.output_dir, "test_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(test_metrics, f, indent=2)
    print(f"\nTest metrics saved to: {metrics_path}")
    print(f"\nFinal Results:")
    print(f"  Sarcasm F1:         {test_metrics['sarcasm']['f1']:.4f}")
    print(f"  Misinformation F1:  {test_metrics['misinformation']['f1']:.4f}")
    print(f"  Overall F1:         {test_metrics['overall_f1']:.4f}")


if __name__ == "__main__":
    train(config)
