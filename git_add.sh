#!/bin/bash

# Adiciona todos os diretórios (e seu conteúdo) ao stage do Git, exceto o diretório raiz.
find . -mindepth 1 -type d -print0 | xargs -0 git add

# Adiciona todos os arquivos localizados no diretório raiz ao stage do Git.
find . -maxdepth 1 -type f -print0 | xargs -0 git add

echo "Todos os diretórios e arquivos da raiz foram adicionados ao git."
