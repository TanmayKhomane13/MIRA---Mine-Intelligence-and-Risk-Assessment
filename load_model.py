import os
import json
import pickle
import joblib
import shutil
import torch
import torch.nn as nn
from transformers import (
    AutoTokenizer,
    DistilBertModel,
    AutoModelForCausalLM,
    pipeline,
    DPRQuestionEncoderTokenizer,
    DPRQuestionEncoder
)
from peft import PeftModel

try:
    import faiss
except ImportError:
    faiss = None

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
    else "mps"
    if torch.backends.mps.is_available()
    else "cpu"
)

model_1.to(device_1)
model_1.eval()

OFFLOAD_DIR = "./offload"

# Wipe any stale offload index from a previous run. accelerate keys its
# offload index (index.json) by the parameter names of whatever model was
# dispatched into this folder. If a prior run left an index built from a
# different model/wrapping (e.g. a non-PEFT-wrapped base model), reusing
# this folder can serve up stale/mismatched keys and crash generation
# with a KeyError deep inside the offload hooks. Since this is a build
# artifact (not a cache we want to keep across model/code changes),
# recreate it fresh every startup.
if os.path.isdir(OFFLOAD_DIR):
    shutil.rmtree(OFFLOAD_DIR)
os.makedirs(
    OFFLOAD_DIR,
    exist_ok=True
)

BASE_MODEL_2 = "Qwen/Qwen2.5-3B-Instruct"
LORA_PATH_2 = "./models/MIRA2_qwen2.5-3b-lora"

tokenizer_2 = AutoTokenizer.from_pretrained(
    LORA_PATH_2
)

# --------------------------------------------
# Device
# --------------------------------------------

if torch.cuda.is_available():

    device_2 = torch.device("cuda")
    model_2_dtype = torch.float16

elif torch.backends.mps.is_available():

    device_2 = torch.device("mps")
    model_2_dtype = torch.float16

else:

    device_2 = torch.device("cpu")
    model_2_dtype = torch.float32


print("Model 2 device:", device_2)
print("Model 2 dtype:", model_2_dtype)


# --------------------------------------------
# Load base model on CPU
# --------------------------------------------

base_model_2 = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL_2,
    torch_dtype=model_2_dtype
)
if device_2 == "cuda":
    # Dispatch (and offload, if VRAM is insufficient) happens exactly
    # once, here, on the base model.
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


# --------------------------------------------
# Load LoRA adapter
# --------------------------------------------

# IMPORTANT: do NOT pass device_map/offload_folder again here.
#
# base_model_2 has already been dispatched (and possibly offloaded) above.
# LoRA only adds small adapter modules alongside the existing base layers
# and does not need its own placement/offload pass. Passing device_map
# again forces a second dispatch that reuses the same offload_folder, but
# every parameter now has a "base_model.model." prefix added by PEFT - so
# accelerate's offload index (built from the first, un-prefixed dispatch)
# no longer matches the parameter names being looked up, and generation
# crashes with:
#   KeyError: 'base_model.model.model.layers.N.input_layernorm.weight'
#
# PeftModel automatically respects base_model_2's existing hf_device_map,
# so no additional device_map/offload arguments are needed here.
model_2 = PeftModel.from_pretrained(
    base_model_2,
    LORA_PATH_2
)


# --------------------------------------------
# Move COMPLETE model to device
# --------------------------------------------

model_2 = model_2.to(device_2)

model_2.eval()

print("Model device:", next(model_2.parameters()).device)
print("Model dtype:", next(model_2.parameters()).dtype)

gen_pipeline = pipeline(
    "text-generation",
    model=model_2,
    tokenizer=tokenizer_2,
    batch_size=1,
    truncation=True,
    padding=False,
    return_full_text=False,
    device = "mps"
)
# ============================================================
# RISK ENGINE
# ============================================================

RISK_MODEL_PATH = "./models/mira_risk_engine/mira-risk-classifier.pkl"
RISK_ENCODER_PATH = "./models/mira_risk_engine/mira-risk-encoder.pkl"

risk_model = joblib.load(RISK_MODEL_PATH)
risk_encoder = joblib.load(RISK_ENCODER_PATH)

# ============================================================
# RAG — REGULATORY GUIDANCE RETRIEVAL
#
# Loads a pre-built FAISS index of regulatory text chunks plus a DPR
# question encoder, used at query time to retrieve the passages that get
# inserted into the GenLLM prompt as "Retrieved Guidance". Loading is
# defensive: if the index/chunks haven't been built yet, the app should
# still start up and simply retrieve no guidance rather than crash.
# ============================================================

RAG_CHUNKS_PATH = os.getenv(
    "RAG_CHUNKS_PATH",
    "./data/Encodings/regulatory_chunks.pkl"
)
RAG_INDEX_PATH = os.getenv(
    "RAG_INDEX_PATH",
    "./data/Encodings/regulatory.index"
)
QUESTION_ENCODER_MODEL = "facebook/dpr-question_encoder-single-nq-base"

regulatory_chunks = []
faiss_index = None
question_tokenizer = None
question_encoder = None

try:
    with open(RAG_CHUNKS_PATH, "rb") as f:
        regulatory_chunks = pickle.load(f)

    if faiss is None:
        raise RuntimeError("faiss is not installed")

    faiss_index = faiss.read_index(RAG_INDEX_PATH)

    question_tokenizer = DPRQuestionEncoderTokenizer.from_pretrained(
        QUESTION_ENCODER_MODEL
    )

    question_encoder = DPRQuestionEncoder.from_pretrained(
        QUESTION_ENCODER_MODEL
    )

    question_encoder.to("cpu")
    question_encoder.eval()

    rag_ready = True

except Exception as e:
    print(f"[MIRA] RAG index unavailable, continuing without it: {e}")
    regulatory_chunks = []
    faiss_index = None
    rag_ready = False

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
print(
    "Risk Engine : MIRA Risk Classifier + Encoder"
)
print(
    "RAG : Regulatory Guidance Retrieval —",
    "READY" if rag_ready else "UNAVAILABLE (no guidance will be retrieved)"
)
if rag_ready:
    print(
        "RAG chunks / vectors:",
        len(regulatory_chunks),
        "/",
        faiss_index.ntotal
    )
print("==============================================")