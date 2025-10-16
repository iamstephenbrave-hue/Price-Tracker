import requests
from bs4 import BeautifulSoup
import json
import csv
from datetime import datetime
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# load config
with open('config.json', 'r') as f:
    config = json.load(f)

def scrape_price(url):
    """scrapes product price from url"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # trying common price selectors (works for many sites)
        price_selectors = [
            'span.a-price-whole',  # amazon
            'span.price',
            'div.price',
            'span[itemprop="price"]',
            'meta[property="product:price:amount"]'
        ]
        
        price = None
        title = soup.find('title').text.strip() if soup.find('title') else 'Unknown Product'
        
        for selector in price_selectors:
            element = soup.select_one(selector)
            if element:
                price_text = element.text.strip()
                # clean up price text
                price_text = price_text.replace('₹', '').replace(',', '').replace('$', '').strip()
                try:
                    price = float(price_text)
                    break
                except:
                    continue
        
        # fallback - search for price patterns
        if price is None:
            import re
            text = soup.get_text()
            # look for patterns like ₹1,234 or $123.45
            matches = re.findall(r'[₹$]\s*[\d,]+\.?\d*', text)
            if matches:
                price_text = matches[0].replace('₹', '').replace('$', '').replace(',', '').strip()
                try:
                    price = float(price_text)
                except:
                    pass
        
        return {
            'title': title[:100],  # limit length
            'price': price,
            'url': url,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

def save_to_csv(data, filename='price_history.csv'):
    """saves price data to csv"""
    
    file_exists = False
    try:
        with open(filename, 'r'):
            file_exists = True
    except:
        pass
    
    with open(filename, 'a', newline='', encoding='utf-8') as f:
        fieldnames = ['timestamp', 'title', 'price', 'url']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerow(data)

def send_alert(product_data):
    """sends email alert when price drops"""
    
    email_config = config['email']
    
    try:
        msg = MIMEMultipart()
        msg['From'] = email_config['sender']
        msg['To'] = email_config['receiver']
        msg['Subject'] = f"Price Alert! {product_data['title']}"
        
        body = f"""
        Good news! The price has dropped below your threshold.
        
        Product: {product_data['title']}
        Current Price: ₹{product_data['price']}
        Your Threshold: ₹{config['threshold']}
        
        Check it out: {product_data['url']}
        
        Time: {product_data['timestamp']}
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # using gmail smtp
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_config['sender'], email_config['password'])
        
        server.send_message(msg)
        server.quit()
        
        print("✓ Alert email sent!")
        
    except Exception as e:
        print(f"Failed to send email: {e}")

def check_products():
    """main function to check all products"""
    
    print(f"\nChecking prices... {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    
    for product in config['products']:
        url = product['url']
        print(f"\nChecking: {product['name']}")
        
        data = scrape_price(url)
        
        if data and data['price']:
            print(f"  Current price: ₹{data['price']}")
            
            save_to_csv(data)
            
            # check if below threshold
            if data['price'] <= config['threshold']:
                print(f"  🔔 ALERT! Price below threshold (₹{config['threshold']})")
                send_alert(data)
            else:
                print(f"  Price still above threshold (₹{config['threshold']})")
        else:
            print("  ✗ Could not fetch price")
        
        time.sleep(2)  # be nice to servers
    
    print("\n" + "="*60)
    print("Check complete!")

if __name__ == "__main__":
    print("="*60)
    print("Price Tracker Started")
    print("="*60)
    
    # run once for testing
    check_products()
    
    # uncomment below for continuous monitoring
    """
    import schedule
    
    schedule.every(6).hours.do(check_products)  # check every 6 hours
    
    print("\nScheduled to run every 6 hours. Press Ctrl+C to stop.")
    
    while True:
        schedule.run_pending()
        time.sleep(60)
    """
