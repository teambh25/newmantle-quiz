from loguru import logger
from tqdm import tqdm
import torch
from torch.utils.data import DataLoader

from transformers import AutoModel, AutoTokenizer

from dataset import WordDataset


def load_model_and_tokenizer(model_name: str):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = AutoModel.from_pretrained(model_name).to(device)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    return model, tokenizer


def inference(dataset: WordDataset, model, tokenizer, batch_size:int) -> dict:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    embeddings = {}
    dataloader = DataLoader(dataset, batch_size=batch_size)
    for batch_words in tqdm(dataloader):
        inputs = tokenizer(
            batch_words,
            return_tensors="pt",
            padding=True,  # 가장 긴 단어를 기준으로 패딩
        ).to(device)
    
        with torch.inference_mode():
            model_output = model(**inputs)
            batch_embeddings = masked_mean_pooling(model_output.last_hidden_state, inputs['attention_mask'])
    
        for word, emb in zip(batch_words, batch_embeddings):
            embeddings[word] = emb.detach().cpu().numpy()
        
    logger.success("Generate embedding succeeded!")
    return embeddings


def masked_mean_pooling(input:torch.tensor, mask: torch.tensor):
    input_mask_expanded = mask.unsqueeze(-1).expand(input.size()).float()
    sum_embeddings = torch.sum(input * input_mask_expanded, 1)
    sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    return sum_embeddings / sum_mask