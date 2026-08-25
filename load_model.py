import os
import json

import torch
import torch.nn as nn

from transformers import AutoTokenizer, DistilBertModel
from peft import PeftModel

MODEL_PATH = './models/mira-distilbert-lora'


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
            'distilbert-base-uncased'
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

    def forward(self, input_ids, attention_mask):

        outputs = self.distilbert(
            input_ids=input_ids,
            attention_mask=attention_mask
        )

        pooled_output = outputs.last_hidden_state[:, 0]

        return {
            'issue': self.issue_classifier(pooled_output),
            'category': self.category_classifier(pooled_output),
            'severity': self.severity_classifier(pooled_output),
            'recurring': self.recurring_classifier(pooled_output)
        }


# ------------------------------------------------------------
# Load label mappings
# ------------------------------------------------------------

with open(
    os.path.join(
        MODEL_PATH,
        'label_mappings.json'
    ),
    'r'
) as f:

    label_mappings = json.load(f)


# ------------------------------------------------------------
# Tokenizer
# ------------------------------------------------------------

tokenizer = AutoTokenizer.from_pretrained(
    'distilbert-base-uncased'
)


# ------------------------------------------------------------
# Model
# ------------------------------------------------------------

model = MIRAClassifier(
    num_issue=len(label_mappings['issue']),
    num_category=len(label_mappings['category']),
    num_severity=len(label_mappings['severity']),
    num_recurring=len(label_mappings['recurring'])
)


# ------------------------------------------------------------
# Load LoRA
# ------------------------------------------------------------

model.distilbert = PeftModel.from_pretrained(
    model.distilbert,
    MODEL_PATH
)


# ------------------------------------------------------------
# Load classification heads
# ------------------------------------------------------------

heads = torch.load(
    os.path.join(
        MODEL_PATH,
        'classification_heads.pth'
    ),
    map_location='cpu'
)


model.issue_classifier.load_state_dict(
    heads['issue_classifier']
)

model.category_classifier.load_state_dict(
    heads['category_classifier']
)

model.severity_classifier.load_state_dict(
    heads['severity_classifier']
)

model.recurring_classifier.load_state_dict(
    heads['recurring_classifier']
)


# ------------------------------------------------------------
# Device
# ------------------------------------------------------------

device = torch.device(
    'cuda'
    if torch.cuda.is_available()
    else 'cpu'
)

model.to(device)
model.eval()

print("MIRA model loaded on:", device)