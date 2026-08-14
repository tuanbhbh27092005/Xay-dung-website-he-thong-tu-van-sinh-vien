import os
import requests
import re
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from accounts.models import CustomUser
from news.models import News
from django.core.files.base import ContentFile

class Command(BaseCommand):
    help = 'Update news from HCMUTE website'

    def handle(self, *args, **options):
        # Delete old news
        News.objects.all().delete()
        self.stdout.write("Deleted all old news.")

        user = CustomUser.objects.filter(is_superuser=True).first()
        if not user:
            user = CustomUser.objects.first()

        url = 'https://hcmute.edu.vn/'
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        response = requests.get(url, verify=False)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        added_titles = set()
        count = 0

        for a in soup.find_all('a', href=True):
            href = a['href']
            title = a.text.strip()
            
            # Look for valid news links
            if 'ArticleId' in href and len(title) > 30:
                if title in added_titles:
                    continue
                
                # Extract ArticleId
                article_id = None
                if '?' in href:
                    qs = parse_qs(urlparse(href).query)
                    if 'ArticleId' in qs:
                        article_id = qs['ArticleId'][0]
                elif '/ArticleId/' in href:
                    parts = href.split('/ArticleId/')
                    if len(parts) > 1:
                        sub_parts = parts[1].split('/')
                        if len(sub_parts) > 0:
                            article_id = sub_parts[0]

                if not article_id:
                    continue

                # Create News object
                content = f"{title}\n\nXem chi tiết tại: https://hcmute.edu.vn{href if href.startswith('/') else '/' + href}"
                news = News(
                    title=title,
                    content=content,
                    summary=title,
                    category='school',
                    author=user,
                    is_published=True
                )
                
                # Download image
                img_url = f"https://hcmute.edu.vn/Services/GetArticleImage.ashx?option=0&Id={article_id}"
                img_resp = requests.get(img_url, verify=False)
                
                if img_resp.status_code == 200 and len(img_resp.content) > 1000: # Ensure it's not a tiny broken image
                    file_name = f"news_{article_id}.jpg"
                    news.thumbnail_image.save(file_name, ContentFile(img_resp.content), save=False)
                
                news.save()
                added_titles.add(title)
                count += 1
                
                if count >= 10: # Limit to 10 news
                    break
        
        self.stdout.write(self.style.SUCCESS(f"Successfully added {count} news articles."))
