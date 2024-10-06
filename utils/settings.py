import json

def load_settings():
    try:
        with open('settings.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_settings(settings):
    with open('settings.json', 'w') as f:
        json.dump(settings, f)

def load_repos_cache():
    try:
        with open('repos_cache.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_repos_cache(repos):
    with open('repos_cache.json', 'w') as f:
        json.dump(repos, f)