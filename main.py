def get_instagram_images(shortcode: str):
    """دریافت تصاویر با RapidAPI"""
    rapidapi_key = os.environ.get("RAPIDAPI_KEY")
    
    if rapidapi_key:
        try:
            url = "https://instagram-scraper-api2.p.rapidapi.com/v1/post_info"
            
            headers = {
                "X-RapidAPI-Key": rapidapi_key,
                "X-RapidAPI-Host": "instagram-scraper-api2.p.rapidapi.com"
            }
            
            querystring = {"code_or_id_or_url": shortcode}
            
            response = requests.get(url, headers=headers, params=querystring, timeout=20)
            
            print(f"RapidAPI response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                images = []
                
                # استخراج عکس‌ها
                if 'data' in data and 'items' in data['data']:
                    items = data['data']['items']
                    if items and len(items) > 0:
                        item = items[0]
                        
                        # چک carousel (چند عکس)
                        if 'carousel_media' in item:
                            for media in item['carousel_media']:
                                if 'image_versions2' in media:
                                    candidates = media['image_versions2']['candidates']
                                    if candidates:
                                        images.append(candidates[0]['url'])
                        # یک عکس
                        elif 'image_versions2' in item:
                            candidates = item['image_versions2']['candidates']
                            if candidates:
                                images.append(candidates[0]['url'])
                
                if images:
                    print(f"Found {len(images)} images via RapidAPI")
                    return images
                else:
                    print("No images found in API response")
            else:
                print(f"RapidAPI error: {response.text[:200]}")
                
        except Exception as e:
            print(f"RapidAPI exception: {e}")
    else:
        print("RAPIDAPI_KEY not set")
    
    # Fallback به روش قدیمی
    print("Trying fallback method...")
    try:
        url = f"https://www.instagram.com/p/{shortcode}/embed/captioned/"
        resp = requests.get(url, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        if resp.status_code == 200:
            pattern = r'https://[^"\'>\s]*(?:cdninstagram|fbcdn)[^"\'>\s]*\.jpg'
            matches = re.findall(pattern, resp.text)
            
            if matches:
                high_quality = [m for m in matches if 's640x640' in m or 's1080x1080' in m or 'e35' in m]
                if high_quality:
                    return list(set(high_quality))[:10]
                return list(set(matches))[:10]
    except Exception as e:
        print(f"Fallback error: {e}")
    
    return []
