import os
import json
import torch
import torch.nn as nn
from transformers import (AutoTokenizer,DistilBertModel,AutoModelForCausalLM,pipeline)
from peft import PeftModel

MODEL_1_PATH = "./models/mira-distilbert-lora"

class MIRAClassifier(nn.Module):
    def __init__(
        self,
        num_issue,
        num_category,
        num_severity,
        num_recurring
    ):
        super().__init__()
        self.distilbert = DistilBertModel.from_pretrained(
            "distilbert-base-uncased"
        )
        hidden_size = self.distilbert.config.hidden_size
        self.issue_classifier = nn.Linear(
            hidden_size,
            num_issue
        )
        self.category_classifier = nn.Linear(
            hidden_size,
            num_category
        )
        self.severity_classifier = nn.Linear(
            hidden_size,
            num_severity
        )
        self.recurring_classifier = nn.Linear(
            hidden_size,
            num_recurring
        )
    def forward(
        self,
        input_ids,
        attention_mask
    ):
        outputs = self.distilbert(
            input_ids=input_ids,
            attention_mask=attention_mask
        )
        pooled_output = outputs.last_hidden_state[:, 0]
        return {
            "issue": self.issue_classifier(
                pooled_output
            ),
            "category": self.category_classifier(
                pooled_output
            ),
            "severity": self.severity_classifier(
                pooled_output
            ),
            "recurring": self.recurring_classifier(
                pooled_output
            )
        }

with open(
    os.path.join(
        MODEL_1_PATH,
        "label_mappings.json"
    ),
    "r"
) as f:
    label_mappings = json.load(f)

tokenizer_1 = AutoTokenizer.from_pretrained(
    "distilbert-base-uncased"
)

model_1 = MIRAClassifier(
    num_issue=len(
        label_mappings["issue"]
    ),
    num_category=len(
        label_mappings["category"]
    ),
    num_severity=len(
        label_mappings["severity"]
    ),
    num_recurring=len(
        label_mappings["recurring"]
    )
)

model_1.distilbert = PeftModel.from_pretrained(
    model_1.distilbert,
    MODEL_1_PATH
)

heads = torch.load(
    os.path.join(
        MODEL_1_PATH,
        "classification_heads.pth"
    ),
    map_location="cpu"
)
model_1.issue_classifier.load_state_dict(
    heads["issue_classifier"]
)
model_1.category_classifier.load_state_dict(
    heads["category_classifier"]
)
model_1.severity_classifier.load_state_dict(
    heads["severity_classifier"]
)
model_1.recurring_classifier.load_state_dict(
    heads["recurring_classifier"]
)

device_1 = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)

model_1.to(device_1)
model_1.eval()

OFFLOAD_DIR = "./offload"
os.makedirs(
    OFFLOAD_DIR,
    exist_ok=True
)

BASE_MODEL_2 = "Qwen/Qwen2.5-3B-Instruct"
LORA_PATH_2 = "./models/MIRA2_qwen2.5-3b-lora"

tokenizer_2 = AutoTokenizer.from_pretrained(
    LORA_PATH_2
)

if torch.cuda.is_available():
    device_2 = "cuda"
    model_2_dtype = torch.float16
else:
    device_2 = "cpu"
    model_2_dtype = torch.float32

if device_2 == "cuda":
    base_model_2 = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_2,
        torch_dtype=model_2_dtype,
        device_map="auto",
        offload_folder=OFFLOAD_DIR
    )
else:
    base_model_2 = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_2,
        torch_dtype=model_2_dtype
    )

model_2 = PeftModel.from_pretrained(
    base_model_2,
    LORA_PATH_2
)

model_2.eval()

gen_pipeline = pipeline(
    "text-generation",
    model=model_2,
    tokenizer=tokenizer_2,
    batch_size=1,
    truncation=True,
    padding=False,
    return_full_text=False
)

print("==============================================")
print("MIRA AI MODELS LOADED")
print("==============================================")
print(
    "Model 1 : MIRA DistilBERT Classifier"
)
print(
    "Model 1 device:",
    device_1
)
print(
    "Model 2 : Qwen2.5-3B-Instruct + MIRA LoRA"
)
print(
    "Model 2 device:",
    device_2
)
print("==============================================")