from typing import TypedDict, List, Optional, Dict, Any
from datetime import datetime

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

class StorySection(TypedDict):
    title: str
    content: str
    images: List[str]

class StoryItem(TypedDict):
    slug: str
    createdAt: str
    author: Author
    org: Organization
    squareImageUrl: str
    previewImageUrl: str
    type: str
    title: str
    sections: List[StorySection]
    mainImage: Optional[str]

class ScoreData(TypedDict):
    gpa: Optional[float]
    scale: Optional[float]
    sat: Optional[int]
    ielts: Optional[float]
    toefl: Optional[int] 