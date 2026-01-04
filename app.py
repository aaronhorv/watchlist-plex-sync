from flask import Flask, render_template, request, jsonify
import requests
import feedparser
import json
import os
import time
from datetime import datetime
import schedule
import threading

app = Flask(__name__)

CONFIG_FILE = '/config/config.json'
LOGS_FILE = '/config/logs.json'

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        'imdbListUrl': '',
        'plexToken': '',
        'tmdbApiKey': '',
        'region': 'US',
        'streamingServices': []
    }

def save_config(config):
    os.makedirs('/config', exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def add_log(message, log_type='info'):
    logs = []
    if os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, 'r') as f:
            logs = json.load(f)
    
    logs.insert(0, {
        'timestamp': datetime.now().isoformat(),
        'message': message,
        'type': log_type
    })
    
    logs = logs[:100]
    
    with open(LOGS_FILE, 'w') as f:
        json.dump(logs, f, indent=2)

def get_imdb_watchlist(list_url):
    try:
        list_id = list_url.split('/')[-1].split('?')[0]
        rss_url = f"https://rss.imdb.com/list/{list_id}"
        
        feed = feedparser.parse(rss_url)
        items = []
        
        for entry in feed.entries:
            imdb_id = entry.link.split('/title/')[-1].strip('/')
            items.append({
                'title': entry.title,
                'imdb_id': imdb_id,
                'link': entry.link
            })
        
        return items
    except Exception as e:
        add_log(f"Error fetching IMDB watchlist: {str(e)}", 'error')
        return []

def get_tmdb_id(imdb_id, api_key):
    try:
        url = f"https://api.themoviedb.org/3/find/{imdb_id}"
        params = {
            'api_key': api_key,
            'external_source': 'imdb_id'
        }
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get('movie_results'):
            return data['movie_results'][0]['id'], 'movie'
        elif data.get('tv_results'):
            return data['tv_results'][0]['id'], 'tv'
        
        return None, None
    except Exception as e:
        add_log(f"Error converting IMDB to TMDB ID: {str(e)}", 'error')
        return None, None

def check_streaming_availability(tmdb_id, media_type, api_key, region, provider_ids):
    try:
        url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/watch/providers"
        params = {'api_key': api_key}
        response = requests.get(url, params=params)
        data = response.json()
        
        if 'results' not in data or region not in data['results']:
            return False, []
        
        region_data = data['results'][region]
        available_providers = []
        
        if 'flatrate' in region_data:
            for provider in region_data['flatrate']:
                if provider['provider_id'] in provider_ids:
                    available_providers.append(provider['provider_name'])
        
        return len(available_providers) > 0, available_providers
    except Exception as e:
        add_log(f"Error checking streaming availability: {str(e)}", 'error')
        return False, []

def add_to_plex_watchlist(imdb_id, plex_token):
    try:
        headers = {
            'X-Plex-Token': plex_token,
            'Accept': 'application/json'
        }
        
        search_url = f"https://metadata.provider.plex.tv/library/metadata/matches"
        params = {
            'type': '1',
            'guid': f'imdb://{imdb_id}'
        }
        
        response = requests.get(search_url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('MediaContainer', {}).get('Metadata'):
                rating_key = data['MediaContainer']['Metadata'][0]['ratingKey']
                
                watchlist_url = f"https://metadata.provider.plex.tv/actions/addToWatchlist"
                params = {'ratingKey': rating_key}
                
                response = requests.put(watchlist_url, headers=headers, params=params)
                return response.status_code == 200
        
        return False
    except Exception as e:
        add_log(f"Error adding to Plex watchlist: {str(e)}", 'error')
        return False

def sync_watchlist():
    config = load_config()
    
    if not all([config.get('imdbListUrl'), config.get('plexToken'), config.get('tmdbApiKey')]):
        add_log("Configuration incomplete. Please configure all settings.", 'error')
        return
    
    add_log("Starting sync process", 'info')
    
    items = get_imdb_watchlist(config['imdbListUrl'])
    add_log(f"Found {len(items)} items in IMDB watchlist", 'info')
    
    processed = 0
    added = 0
    skipped = 0
    
    for item in items:
        processed += 1
        
        tmdb_id, media_type = get_tmdb_id(item['imdb_id'], config['tmdbApiKey'])
        
        if not tmdb_id:
            add_log(f"Could not find TMDB ID for {item['title']}", 'warning')
            continue
        
        is_available, providers = check_streaming_availability(
            tmdb_id,
            media_type,
            config['tmdbApiKey'],
            config['region'],
            config['streamingServices']
        )
        
        if is_available:
            skipped += 1
            add_log(f"Skipped '{item['title']}' - available on {', '.join(providers)}", 'warning')
            continue
        
        if add_to_plex_watchlist(item['imdb_id'], config['plexToken']):
            added += 1
            add_log(f"Added '{item['title']}' to Plex watchlist", 'success')
        else:
            add_log(f"Failed to add '{item['title']}' to Plex watchlist", 'error')
        
        time.sleep(0.5)
    
    add_log(f"Sync complete: {processed} processed, {added} added, {skipped} skipped", 'success')

def schedule_sync():
    schedule.every(6).hours.do(sync_watchlist)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify(load_config())

@app.route('/api/config', methods=['POST'])
def update_config():
    config = request.json
    save_config(config)
    add_log("Configuration updated", 'success')
    return jsonify({'success': True})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    if os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, 'r') as f:
            return jsonify(json.load(f))
    return jsonify([])

@app.route('/api/sync', methods=['POST'])
def trigger_sync():
    threading.Thread(target=sync_watchlist, daemon=True).start()
    return jsonify({'success': True, 'message': 'Sync started'})

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        'lastSync': None,
        'status': 'idle',
        'processed': 0,
        'added': 0,
        'skipped': 0
    })

if __name__ == '__main__':
    threading.Thread(target=schedule_sync, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=False)