from torch.utils.data import Dataset

from utils import filter_special_token_word


class WordDataset(Dataset):
    def __init__(self, words):
        self.words = words

    def __len__(self):
        return len(self.words)

    def __getitem__(self, idx):
        return self.words[idx]

def preprocessing(words, tokenizer):
    filtered_words = filter_special_token_word(tokenizer, words)
    # logger.info(f"embedding fail words: {' '.join(set(words) - set(filtered_words))}")
    print(
        "[Data]" 
        f"\n- Origin : {len(words)}"
        f"\n- After : {len(filtered_words)}"
        f"\n- Filtered : {len(words) - len(filtered_words)}"
    )    
    return WordDataset(filtered_words)
