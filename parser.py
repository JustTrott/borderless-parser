from typing import TypedDict, List, Optional, Dict, Any
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import json
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from pathlib import Path

class Country(TypedDict):
    code: str
    displayName: str
    emoji: str

class City(TypedDict):
    id: str
    displayName: str
    state: Optional[str]

class Organization(TypedDict):
    id: str
    orgname: str
    imageUrl: str
    displayName: str
    orgType: str
    city: City
    country: Country

class Author(TypedDict):
    username: str
    firstName: str
    emoji: Optional[str]
    imageUrl: str
    fromCountry: Country

class Cursor(TypedDict):
    score: int
    createdAt: str

class StoryItem(TypedDict):
    slug: str
    createdAt: str
    author: Author
    org: Organization
    squareImageUrl: str
    previewImageUrl: str
    type: str
    title: str
    localeContents: List[Any]

class ApiResponse(TypedDict):
    items: List[StoryItem]
    nextCursor: Cursor

class StoryContent(TypedDict):
    title: str
    content: str
    imageUrl: Optional[str]

class StorySection(TypedDict):
    title: str
    content: str
    images: List[str]

class ParsedStory(TypedDict):
    title: str
    sections: List[StorySection]
    mainImage: Optional[str]
    author: Author
    org: Organization
    createdAt: str

def create_request_payload(
    lang: str = "en",
    limit: int = 1,
    types: List[str] = ["Bachelor"],
    cursor: Optional[Cursor] = None
) -> Dict[str, Any]:
    """Create the request payload for the API."""
    payload = {
        "0": {
            "json": {
                "lang": lang,
                "limit": limit,
                "types": types,
            },
            "meta": {
                "values": {
                    "cursor.createdAt": ["Date"]
                }
            }
        }
    }
    
    if cursor:
        payload["0"]["json"]["cursor"] = cursor
    
    return payload

def get_headers() -> Dict[str, str]:
    """Get the headers for the API request."""
    return {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://borderless.so/stories',
        'content-type': 'application/json',
        'trpc-batch-mode': 'stream',
        'Connection': 'keep-alive',
    }

def fetch_stories(
    url: str = 'https://borderless.so/api/trpc/post.findRelevant',
    lang: str = "en",
    limit: int = 1,
    types: List[str] = ["Bachelor"],
    cursor: Optional[Cursor] = None
) -> ApiResponse:
    """Fetch stories from the API and return typed response."""
    payload = create_request_payload(lang, limit, types, cursor)
    
    params = {
        'batch': '1',
        'input': json.dumps(payload)
    }
    
    response = requests.get(url, params=params, headers=get_headers())
    response.raise_for_status()  # Raise exception for bad status codes
    
    data = response.json()
    return data['0']['result']['data']['json']

def parse_story(slug: str) -> ParsedStory:
    """
    Fetch and parse a story from borderless.so using its slug.
    
    Args:
        slug: The story's unique identifier/slug
        
    Returns:
        ParsedStory object containing the structured story content
    """
    url = f'https://borderless.so/stories/{slug}'
    
    # Fetch the page
    response = requests.get(url, headers=get_headers())
    response.raise_for_status()
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')
    article = soup.find('article')
    
    if not article:
        raise ValueError(f"Could not find article content for slug: {slug}")
    
    # Initialize sections list
    sections: List[StorySection] = []
    current_section: Optional[StorySection] = None
    main_image: Optional[str] = None
    
    # Process each element in the article
    for element in article.children:
        # Skip advertisement elements
        if element.name == 'a':
            continue
            
        if element.name == 'div':
            # Process elements within each div
            for content in element.children:
                if content.name == 'h1':
                    # If we have a previous section, add it to sections list
                    if current_section:
                        sections.append(current_section)
                    
                    # Start new section
                    current_section = {
                        'title': content.get_text(strip=True),
                        'content': '',
                        'images': []
                    }
                
                elif content.name == 'p':
                    if current_section:
                        current_section['content'] += content.get_text(strip=True) + '\n'
                
                elif content.name == 'figure':
                    img = content.find('img')
                    if img and img.get('src'):
                        img_url = img['src']
                        if not main_image:
                            main_image = img_url
                        if current_section:
                            current_section['images'].append(img_url)
    
    # Add the last section if exists
    if current_section:
        sections.append(current_section)
    
    # Fetch story metadata using the existing API
    # story_data = fetch_stories(limit=1, types=["Bachelor"])
    # story_item = next((item for item in story_data['items'] if item['slug'] == slug), None)
    
    # if not story_item:
    #     raise ValueError(f"Could not find story metadata for slug: {slug}")
    
    return {
        # 'title': story_item['title'],
        'sections': sections,
        'mainImage': main_image,
        # 'author': story_item['author'],
        # 'org': story_item['org'],
        # 'createdAt': story_item['createdAt']
    }

def fetch_full_stories(count: int = -1, parallel: bool = False, max_workers: int = 5) -> List[Dict[str, Any]]:
    """
    Fetch stories with their full content.
    
    Args:
        count: Number of stories to fetch. If -1, fetches all available stories.
        parallel: If True, fetches stories within each batch in parallel.
        max_workers: Maximum number of parallel workers when parallel=True.
    
    Returns:
        List of stories with both API metadata and parsed content
    """
    all_stories = []
    cursor: Optional[Cursor] = None
    batch_size = 10

    def process_story(story: StoryItem) -> Dict[str, Any]:
        """Process a single story by fetching its content and combining with metadata."""
        parsed_content = parse_story(story['slug'])
        return {
            **story,  # All API metadata
            'sections': parsed_content['sections'],
            'mainImage': parsed_content['mainImage']
        }
    
    while True:
        # Fetch batch of stories from API
        stories_response = fetch_stories(
            limit=batch_size,
            cursor=cursor
        )
        
        batch_stories = []
        
        if parallel:
            # Process stories in parallel
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all stories in batch for processing
                future_to_story = {
                    executor.submit(process_story, story): story 
                    for story in stories_response['items']
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_story):
                    try:
                        full_story = future.result()
                        batch_stories.append(full_story)
                    except Exception as e:
                        print(f"Error processing story: {e}")
        else:
            # Process stories sequentially
            for story in stories_response['items']:
                try:
                    full_story = process_story(story)
                    batch_stories.append(full_story)
                except Exception as e:
                    print(f"Error processing story: {e}")
        
        # Add processed stories to result list
        all_stories.extend(batch_stories)
        
        # Check if we've reached the requested count
        if count != -1 and len(all_stories) >= count:
            return all_stories[:count]
        
        # Update cursor for next batch
        cursor = stories_response.get('nextCursor')
        
        # If no more stories, break
        if not cursor:
            break
            
        # Random delay between batches
        # time.sleep(random.uniform(1, 5))
    
    return all_stories

def save_stories_to_json(
    stories: List[Dict[str, Any]], 
    output_dir: str = "data",
    filename: Optional[str] = None
) -> str:
    """
    Save fetched stories to a JSON file.
    
    Args:
        stories: List of story dictionaries to save
        output_dir: Directory to save the JSON file (default: "data")
        filename: Optional custom filename. If None, generates timestamp-based name
        
    Returns:
        str: Path to the saved JSON file
    """
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Generate filename with timestamp if not provided
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"stories_{timestamp}.json"
    
    # Ensure filename has .json extension
    if not filename.endswith('.json'):
        filename += '.json'
    
    filepath = os.path.join(output_dir, filename)
    
    # Save stories to JSON file
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'story_count': len(stories)
            },
            'stories': stories
        }, f, ensure_ascii=False, indent=2)
    
    return filepath

def main():
    """Main function to demonstrate usage."""
    try:
        # Example: Fetch 5 stories with full content in parallel
        stories = fetch_full_stories(count=20, parallel=True, max_workers=3)
        
        print(f"Fetched {len(stories)} stories:")
        # for story in stories:
        #     print(f"\nTitle: {story['title']}")
        #     print(f"Author: {story['author']['firstName']}")
        #     print(f"Organization: {story['org']['displayName']}")
        #     print(f"Number of sections: {len(story['sections'])}")
            
        #     # Print first section preview
        #     if story['sections']:
        #         first_section = story['sections'][0]
        #         print(f"First section: {first_section['title']}")
        #         print(f"Content preview: {first_section['content'][:100]}...")
        
        # Save stories to JSON
        saved_path = save_stories_to_json(stories)
        print(f"\nStories saved to: {saved_path}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
