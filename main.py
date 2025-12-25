def get_instagram_images(shortcode: str):
    """دریافت تصاویر با چند روش مختلف"""
    
    # روش 1: استفاده از API غیررسمی
    try:
        headers = {
            'User-Agent': 'Instagram 76.0.0.15.395 Android (24/7.0; 640dpi; 1440x2560; samsung)',
            'Accept': '*/*',
        }
        
        # تلاش با endpoint های مختلف
        endpoints = [
            f"https://www.instagram.com/p/{shortcode}/?__a=1&__d=dis",
            f"https://i.instagram.com/api/v1/media/{shortcode}/info/",
        ]
        
        for endpoint in endpoints:
            try:
                resp = requests.get(endpoint, headers=headers, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    
                    # استخراج عکس‌ها
                    if 'items' in data and data['items']:
                        item = data['items'][0]
                        images = []
                        
                        if 'carousel_media' in item:
                            for media in item['carousel_media']:
                                if 'image_versions2' in media:
                                    images.append(media['image_versions2']['candidates'][0]['url'])
                        elif 'image_versions2' in item:
                            images.append(item['image_versions2']['candidates'][0]['url'])
                        
                        if images:
                            return images
            except:
                continue
    except:
        pass
    
    # روش 2: استفاده از oEmbed
    try:
        oembed_url = f"https://www.instagram.com/p/{shortcode}/embed/captioned/"
        resp = requests.get(oembed_url, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        if resp.status_code == 200:
            # پیدا کردن URL های تصویر
            pattern = r'https://[^"\'>\s]*(?:cdninstagram|fbcdn)[^"\'>\s]*\.jpg'
            matches = re.findall(pattern, resp.text)
            
            if matches:
                # فیلتر کردن تصاویر با کیفیت بالا
                high_quality = [m for m in matches if 's640x640' in m or 's1080x1080' in m or 'e35' in m]
                if high_quality:
                    return list(set(high_quality))[:10]  # حداکثر 10 عکس
                return list(set(matches))[:10]
    except:
        pass
    
    # روش 3: دانلود مستقیم media
    try:
        media_url = f"https://www.instagram.com/p/{shortcode}/media/?size=l"
        resp = requests.head(media_url, allow_redirects=True, timeout=10)
        if resp.status_code == 200:
            return [resp.url]
    except:
        pass
    
    return []
