from datetime import datetime
from typing import Optional, Dict, Any, List
from peewee import *
from playhouse.shortcuts import model_to_dict

db = SqliteDatabase('stories.db')

class BaseModel(Model):
    class Meta:
        database = db

class Country(BaseModel):
    code = CharField(primary_key=True)
    display_name = CharField()
    emoji = CharField()

    class Meta:
        table_name = 'countries'

class Organization(BaseModel):
    id = CharField(primary_key=True)
    orgname = CharField(unique=True)
    image_url = CharField(null=True)
    display_name = CharField()
    org_type = CharField()
    city_id = CharField(null=True)
    city_name = CharField(null=True)
    city_state = CharField(null=True)
    country_code = ForeignKeyField(Country, backref='organizations')
    
    class Meta:
        table_name = 'organizations'

class StoryScore(BaseModel):
    orgname = ForeignKeyField(Organization, field='orgname')
    slug = CharField()
    gpa = FloatField(null=True)
    scale = FloatField(null=True)
    sat = IntegerField(null=True)
    ielts = FloatField(null=True)
    toefl = IntegerField(null=True)
    created_at = DateTimeField(default=datetime.now)

    class Meta:
        primary_key = CompositeKey('orgname', 'slug')
        table_name = 'story_scores'
        
class Database:
    def __init__(self, db_path: str = "stories.db"):
        self.db = db
        self.init_db()

    def init_db(self):
        """Initialize the database with required tables."""
        self.db.connect()
        self.db.create_tables([Country, Organization, StoryScore])
        self.db.close()

    def upsert_story_scores(self, orgname: str, slug: str, scores: Dict[str, Any]):
        """Insert or update story scores in the database."""
        story_score, created = StoryScore.get_or_create(
            orgname=orgname,
            slug=slug,
            defaults={
                'gpa': scores.get('gpa'),
                'scale': scores.get('scale'),
                'sat': scores.get('sat'),
                'ielts': scores.get('ielts'),
                'toefl': scores.get('toefl')
            }
        )
        
        if not created:
            story_score.gpa = scores.get('gpa')
            story_score.scale = scores.get('scale')
            story_score.sat = scores.get('sat')
            story_score.ielts = scores.get('ielts')
            story_score.toefl = scores.get('toefl')
            story_score.save()

    def get_story_scores(self, orgname: str, slug: str) -> Optional[Dict[str, Any]]:
        """Retrieve story scores from the database."""
        try:
            story_score = StoryScore.get(
                StoryScore.orgname == orgname,
                StoryScore.slug == slug
            )
            return {
                'gpa': story_score.gpa,
                'scale': story_score.scale,
                'sat': story_score.sat,
                'ielts': story_score.ielts,
                'toefl': story_score.toefl
            }
        except StoryScore.DoesNotExist:
            return None

    def _convert_to_four_scale(self, gpa: float, scale: float) -> float:
        """Convert any GPA to 4.0 scale."""
        if scale == 4.0 or gpa is None or scale is None:
            return gpa
        return (gpa / scale) * 4.0

    def _calculate_stats(self, scores) -> Dict[str, float]:
        """Calculate statistics with GPA conversion to 4.0 scale."""
        stats = {
            'avg_gpa': 0.0,
            'avg_scale': 4.0,  # Always use 4.0 scale for output
            'avg_sat': 0.0,
            'avg_ielts': 0.0,
            'avg_toefl': 0.0,
            'count': scores.count()
        }
        
        if stats['count'] == 0:
            return stats

        # Convert GPAs to 4.0 scale before averaging
        gpa_scores = [
            self._convert_to_four_scale(s.gpa, s.scale)
            for s in scores 
            if s.gpa is not None and s.scale is not None
        ]
        sat_scores = [s.sat for s in scores if s.sat is not None]
        ielts_scores = [s.ielts for s in scores if s.ielts is not None]
        toefl_scores = [s.toefl for s in scores if s.toefl is not None]

        stats['avg_gpa'] = sum(gpa_scores) / len(gpa_scores) if gpa_scores else 0
        stats['avg_sat'] = sum(sat_scores) / len(sat_scores) if sat_scores else 0
        stats['avg_ielts'] = sum(ielts_scores) / len(ielts_scores) if ielts_scores else 0
        stats['avg_toefl'] = sum(toefl_scores) / len(toefl_scores) if toefl_scores else 0

        return stats

    def analyze_by_orgname(self, orgname: str) -> Dict[str, float]:
        """Calculate average stats for a given organization."""
        try:
            scores = StoryScore.select().where(StoryScore.orgname == orgname)
            return self._calculate_stats(scores)
        except Exception as e:
            print(f"Error analyzing org {orgname}: {str(e)}")
            return {
                'avg_gpa': 0.0,
                'avg_scale': 4.0,
                'avg_sat': 0.0,
                'avg_ielts': 0.0,
                'avg_toefl': 0.0,
                'count': 0
            }

    def analyze_by_author_country(self, country_code: str) -> Dict[str, float]:
        """Calculate average stats for authors from a specific country."""
        try:
            scores = (StoryScore
                     .select()
                     .join(Organization)
                     .join(Country)
                     .where(Country.code == country_code))
            return self._calculate_stats(scores)
        except Exception as e:
            print(f"Error analyzing country {country_code}: {str(e)}")
            return {
                'avg_gpa': 0.0,
                'avg_scale': 4.0,
                'avg_sat': 0.0,
                'avg_ielts': 0.0,
                'avg_toefl': 0.0,
                'count': 0
            }

    def analyze_by_org_country(self, country_code: str) -> Dict[str, float]:
        """Calculate average stats for organizations from a specific country."""
        try:
            scores = (StoryScore
                     .select()
                     .join(Organization)
                     .where(Organization.country_code == country_code))
            return self._calculate_stats(scores)
        except Exception as e:
            print(f"Error analyzing org country {country_code}: {str(e)}")
            return {
                'avg_gpa': 0.0,
                'avg_scale': 4.0,
                'avg_sat': 0.0,
                'avg_ielts': 0.0,
                'avg_toefl': 0.0,
                'count': 0
            }

    def get_all_organizations(self) -> List[str]:
        """Get list of all organization names."""
        return [org.orgname for org in Organization.select(Organization.orgname)]

    def get_all_countries(self) -> List[str]:
        """Get list of all country codes."""
        return [country.code for country in Country.select(Country.code)]