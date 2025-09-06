# get init data
wget https://github.com/spellcheck-ko/hunspell-dict-ko/releases/download/0.7.92/ko-aff-dic-0.7.92.zip -P ./data/
unzip data/ko-aff-dic-0.7.92.zip  -d ./data/

# generate embedding
docker-compose run --rm  word-embedder --init

# load emebdding
docker-compose run --rm  word-embedder --emb_path data/embedding/init-data
