def get_instagram_images(shortcode: str):
    """دریافت با RapidAPI"""
    rapidapi_key = os.environ.get("RAPIDAPI_KEY")
    
    if rapidapi_key:
        try:
            url = "https://instagram-scraper-api2.p.rapidapi.com/v1/post_info"
            
            headers = {
                "X-RapidAPI-Key": rapidapi_key,
                "X-RapidAPI-Host": "instagram-scraper-api2.p.rapidapi.com"
            }
            
            params = {"code_or_id_or_url": shortcode}
            
            response = requests.get(url, headers=headers, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                images = []
                
                if 'data' in data:
                    items = data['data'].get('items', [])
                    if items:
                        item = items[0]
                        
                        # کاروسل
                        if 'carousel_media' in item:
                            for media in item['carousel_media']:
                                if 'image_versions2' in media:
                                    images.append(media['image_versions2']['candidates'][0]['url'])
                        # تک عکس
                        elif 'image_versions2' in item:
                            images.append(item['image_versions2']['candidates'][0]['url'])
                
                if images:
                    return images
        except Exception as e:
            print(f"RapidAPI error: {e}")
    
    # fallback به روش قدیمی
    return []
