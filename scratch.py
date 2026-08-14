import sys
import re
try:
    with open('e.sql', 'r', encoding='utf-8', errors='ignore') as f, open('out2.txt', 'w', encoding='utf-8') as out:
        in_news = False
        for line in f:
            if 'INSERT INTO `news_news`' in line:
                matches = re.findall(r'\((\d+),\'(.*?)\',', line)
                for m in matches:
                    if m[0] in ('29', '30'):
                        out.write(f"NEWS {m[0]}: {m[1]}\n")
except Exception as e:
    print(e)
