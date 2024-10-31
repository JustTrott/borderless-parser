import json
import os
from typing import Dict, Any, List
from openai import OpenAI
from database import Database
from story_types import StoryItem, ScoreData
from dotenv import load_dotenv

class StoryAnalyzer:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)
        self.db = Database()

    def extract_scores(self, story: StoryItem) -> ScoreData:
        """Extract academic scores from a story using GPT-4."""
        # Combine all section contents for analysis
        full_content = "\n".join(
            f"{section['title']}\n{section['content']}"
            for section in story['sections']
        )

        prompt = """
        Extract academic scores exactly as mentioned in the text:

        1. For grades:
           - If GPA is mentioned, extract both GPA and its scale (e.g., 3.7 out of 4.0)
           - If other grading system is mentioned, extract grade and its scale (e.g., 17.28 out of 20)
           - For multiple grades, extract the highest one
        2. Extract SAT score if mentioned (just the number)
        3. Extract IELTS score if mentioned (as decimal)
        4. Extract TOEFL score if mentioned (as integer)

        Return only a JSON object with these keys:
        {
            "gpa": float or null,
            "scale": float or null,
            "sat": integer or null,
            "ielts": float or null,
            "toefl": integer or null
        }

        Examples:
        - "17.28 out of 20" → {"gpa": 17.28, "scale": 20.0, "sat": null, "ielts": null, "toefl": null}
        - "GPA of 3.7/4.0 and TOEFL 100" → {"gpa": 3.7, "scale": 4.0, "sat": null, "ielts": null, "toefl": 100}
        - No grades mentioned → {"gpa": null, "scale": null, "sat": null, "ielts": null, "toefl": null}

        If a score is not mentioned, use null. Be precise and only include explicitly mentioned scores.
        For multiple grades, note which one you selected as a reasoning field in the JSON. The reasoning field should come before the gpa field.
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": full_content}
                ],
                temperature=0
            )

            # Parse the response
            print(response.choices[0].message.content)
            scores = json.loads(response.choices[0].message.content)
            return scores

        except Exception as e:
            print(f"Error analyzing story {story['slug']}: {str(e)}")
            return {
                "gpa": None,
                "scale": None,
                "sat": None,
                "ielts": None,
                "toefl": None
            }

    def analyze_stories(self, stories_file: str):
        """Analyze all stories from a JSON file and store results in database."""
        # Load stories from JSON file
        with open(stories_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            stories: List[StoryItem] = data['stories']

        # Process each story
        for story in stories:
            print(f"Analyzing story: {story['slug']}")
            
            scores = self.extract_scores(story)
            
            # Store results in database
            self.db.upsert_story_scores(
                orgname=story['org']['orgname'],
                slug=story['slug'],
                scores=scores
            )
            
            print(f"Stored scores for {story['slug']}: {scores}")

def analyze_all_stats(db: Database):
    """Analyze stats for all organizations and countries."""
    
    def _are_stats_empty(stats: Dict[str, float]) -> bool:
        """Check if all statistical values are 0."""
        return all(
            stats[key] == 0 
            for key in ['avg_gpa', 'avg_sat', 'avg_ielts', 'avg_toefl']
        )

    def _print_stats(prefix: str, name: str, stats: Dict[str, float]):
        """Print stats if they're not all zeros."""
        if not _are_stats_empty(stats):
            print(f"\n{prefix}: {name}")
            print(f"Number of stories: {stats['count']}")
            print(f"Average GPA: {stats['avg_gpa']:.2f}/{stats['avg_scale']:.2f}")
            print(f"Average SAT: {stats['avg_sat']:.0f}")
            print(f"Average IELTS: {stats['avg_ielts']:.1f}")
            print(f"Average TOEFL: {stats['avg_toefl']:.0f}")
    
    # Analyze organizations
    print("\nAnalyzing organizations...")
    orgs = db.get_all_organizations()
    for org in orgs:
        stats = db.analyze_by_orgname(org)
        _print_stats("Organization", org, stats)

    # Analyze countries of authors
    # print("\nAnalyzing countries of authors...")
    countries = db.get_all_countries()
    # for country in countries:
    #     stats = db.analyze_by_author_country(country)
    #     _print_stats("Author Country", country, stats)

    # Analyze countries of organizations
    print("\nAnalyzing countries of organizations...")
    for country in countries:
        stats = db.analyze_by_org_country(country)
        _print_stats("Organization Country", country, stats)

def main():
    # Load environment variables
    load_dotenv()

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")

    analyzer = StoryAnalyzer(api_key)
    
    # Analyze stories from the JSON file
    stories_file = "data/stories.json"
    analyzer.analyze_stories(stories_file)

    # Analyze aggregate statistics
    print("\nAnalyzing aggregate statistics...")
    analyze_all_stats(analyzer.db)

if __name__ == "__main__":
    main()
