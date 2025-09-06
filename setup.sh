# get init data
wget https://github.com/spellcheck-ko/hunspell-dict-ko/releases/download/0.7.92/ko-aff-dic-0.7.92.zip -P ./data/
unzip data/ko-aff-dic-0.7.92.zip  -d ./data/

# generate embedding
docker-compose run --rm  word-embedder --init

# load emebdding
docker-compose run --rm  data-loader --setup --emb_path data/embedding/init-data

# delete init data
rm -rf ./data/ko-aff-dic-0.7.92
rm -rf ./data/ko-aff-dic-0.7.92.zip
# rm -rf ./data/embedding/init-data