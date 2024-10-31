import json
from typing import Dict, Set, Optional, Tuple
from database import Database, Country, Organization
from story_types import StoryItem, City

def extract_unique_countries(stories: list[StoryItem]) -> Set[Tuple[str, str, str]]:
    """Extract unique countries from stories."""
    countries = set()
    
    for story in stories:
        # Add author's country
        country_data = story['author']['fromCountry']
        countries.add((
            country_data['code'],
            country_data['displayName'],
            country_data['emoji']
        ))
        
        # Add organization's country
        org_country = story['org']['country']
        countries.add((
            org_country['code'],
            org_country['displayName'],
            org_country['emoji']
        ))
    
    return countries

def extract_city_data(city: Optional[City]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Extract city data with null handling."""
    if not city:
        return None, None, None
    return (
        city.get('id'),
        city.get('displayName'),
        city.get('state')
    )

def extract_organizations(stories: list[StoryItem]) -> Set[Tuple]:
    """Extract unique organizations from stories."""
    organizations = set()
    
    for story in stories:
        org = story['org']
        city_id, city_name, city_state = extract_city_data(org.get('city'))
        
        organizations.add((
            org['id'],
            org['orgname'],
            org['imageUrl'],
            org['displayName'],
            org['orgType'],
            city_id,
            city_name,
            city_state,
            org['country']['code']
        ))
    
    return organizations

def populate_database(stories_file: str):
    """Populate the database with countries and organizations from stories."""
    # Read stories from JSON file
    with open(stories_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        stories = data['stories']

    # Extract unique entities
    countries = extract_unique_countries(stories)
    organizations = extract_organizations(stories)

    # Connect to database
    db = Database()

    try:
        # Populate countries
        print("Populating countries...")
        for code, display_name, emoji in countries:
            Country.get_or_create(
                code=code,
                defaults={
                    'display_name': display_name,
                    'emoji': emoji
                }
            )

        # Populate organizations
        print("Populating organizations...")
        for org_data in organizations:
            Organization.get_or_create(
                id=org_data[0],
                defaults={
                    'orgname': org_data[1],
                    'image_url': org_data[2],
                    'display_name': org_data[3],
                    'org_type': org_data[4],
                    'city_id': org_data[5],
                    'city_name': org_data[6],
                    'city_state': org_data[7],
                    'country_code': org_data[8]
                }
            )

        print("Database population completed successfully!")

    except Exception as e:
        print(f"Error populating database: {str(e)}")
        raise e

def main():
    stories_file = "data/stories.json"
    populate_database(stories_file)

if __name__ == "__main__":
    main() 