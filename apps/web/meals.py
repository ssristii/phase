"""Daily meal prep ideas (local fallback for Gemini G3).

Curated, phase-aware ideas. No calories, macros, or dietary preferences.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MealIdea:
    title: str
    why: str
    prep_minutes: int
    ingredients: tuple[str, ...]
    steps: tuple[str, ...]
    source_domain: str
    source_url: str


MEALS: tuple[MealIdea, ...] = (
    MealIdea(
        title="Warm lentil and spinach bowl",
        why="Gentle, iron-rich, and easy to digest on lower-energy days.",
        prep_minutes=25,
        ingredients=("lentils", "spinach", "garlic", "olive oil", "lemon"),
        steps=(
            "Rinse and simmer lentils until tender.",
            "Saute garlic in olive oil, then wilt spinach.",
            "Combine, season, and finish with lemon.",
        ),
        source_domain="eatright.org",
        source_url="https://www.eatright.org/",
    ),
    MealIdea(
        title="Egg and vegetable scramble",
        why="Quick protein with vegetables for a steady start.",
        prep_minutes=15,
        ingredients=("eggs", "bell pepper", "spinach", "feta", "toast"),
        steps=(
            "Whisk eggs and season lightly.",
            "Cook vegetables until soft.",
            "Add eggs, scramble, and top with feta.",
        ),
        source_domain="eatright.org",
        source_url="https://www.eatright.org/",
    ),
    MealIdea(
        title="Chickpea and sweet potato tray bake",
        why="Filling and warm, suited to luteal-phase comfort.",
        prep_minutes=35,
        ingredients=("chickpeas", "sweet potato", "red onion", "tahini", "parsley"),
        steps=(
            "Toss chickpeas and sweet potato with oil and spices.",
            "Roast until golden.",
            "Drizzle with tahini and add parsley.",
        ),
        source_domain="eatright.org",
        source_url="https://www.eatright.org/",
    ),
    MealIdea(
        title="Quinoa salad with cucumber and herbs",
        why="Light and refreshing when energy is returning.",
        prep_minutes=20,
        ingredients=("quinoa", "cucumber", "mint", "lemon", "olive oil"),
        steps=(
            "Cook and cool quinoa.",
            "Chop cucumber and herbs.",
            "Toss with lemon and olive oil.",
        ),
        source_domain="eatright.org",
        source_url="https://www.eatright.org/",
    ),
)


def pick_meal(day_index: int, phase: str | None = None) -> MealIdea:
    return MEALS[day_index % len(MEALS)]
