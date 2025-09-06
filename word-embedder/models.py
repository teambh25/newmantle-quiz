import os

from loguru import logger
import torch
from torch.utils.data import DataLoader
from tqdm import tqdm

from transformers import AutoModel, AutoTokenizer

from utils import save_embedding
from dataset import WordDataset


def load_model_and_tokenizer(model_name: str):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = AutoModel.from_pretrained(model_name).to(device)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    return model, tokenizer


def inference(dataset: WordDataset, model, tokenizer, batch_size:int, save_path: str, save_iter: int):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    word_embeddings = {}
    file_num = 0
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
            word_embeddings[word] = emb.detach().cpu().numpy()
            if len(word_embeddings) % save_iter == 0:
                file_name = os.path.join(save_path,f"{file_num}.pkl")
                save_embedding(file_name, word_embeddings)
                word_embeddings = {}
                file_num += 1
    if word_embeddings:
        file_name = os.path.join(save_path,f"{file_num}.pkl")
        save_embedding(file_name, word_embeddings)
    logger.success("Generate embedding succeeded!")


def masked_mean_pooling(input:torch.tensor, mask: torch.tensor):
    input_mask_expanded = mask.unsqueeze(-1).expand(input.size()).float()
    sum_embeddings = torch.sum(input * input_mask_expanded, 1)
    sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    return sum_embeddings / sum_mask