#!/bin/bash

find . -maxdepth 1 -type f \( -name '*.c' -o -name '*.js' -o -name '*.py' \) -print0 |
while IFS= read -r -d '' file; do
    first_line=$(head -n 1 "$file")

     extension="${file##*.}"

     if [[ "$extension" == "py" && "$first_line" =~ ^[[:space:]]*# ]] ||
         [[ "$extension" != "py" && "$first_line" =~ ^[[:space:]]*(//|/\*) ]]; then
        echo "$file: первая строка содержит комментарий"
    else
        echo "$file: первая строка не содержит комментарий"
    fi
done
