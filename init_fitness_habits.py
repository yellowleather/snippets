#!/usr/bin/env python3
"""
Script to initialize fitness habits
"""
from google.cloud import firestore

db = firestore.Client()

# Define your fitness habits
habits = [
    {
        'name': 'Protein intake in the morning',
        'frequency_per_week': 7,
        'category': 'nutrition',
        'order': 0
    },
    {
        'name': 'Walk in the evening',
        'frequency_per_week': 4,  # every alternate day, roughly 3-4x/week
        'category': 'cardio',
        'order': 1
    },
    {
        'name': 'Running/Sprinting',
        'frequency_per_week': 2,
        'category': 'cardio',
        'order': 2
    },
    {
        'name': 'Legs day',
        'frequency_per_week': 1,
        'category': 'strength',
        'order': 3
    },
    {
        'name': 'Push day',
        'frequency_per_week': 1,
        'category': 'strength',
        'order': 4
    },
    {
        'name': 'Pull day',
        'frequency_per_week': 1,
        'category': 'strength',
        'order': 5
    },
    {
        'name': 'No food after 6 pm',
        'frequency_per_week': 7,
        'category': 'nutrition',
        'order': 6
    }
]

def init_habits():
    """Initialize fitness habits in Firestore"""
    habits_ref = db.collection('fitness_habits')

    # Check if habits already exist
    existing = list(habits_ref.stream())
    if existing:
        print(f"Found {len(existing)} existing habits. Skipping initialization.")
        print("If you want to reset, delete the fitness_habits collection first.")
        return

    # Create habits
    for habit in habits:
        doc_ref = habits_ref.document()
        doc_ref.set({
            **habit,
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP
        })
        print(f"Created habit: {habit['name']} ({habit['frequency_per_week']}x/week)")

    print(f"\n✓ Successfully initialized {len(habits)} fitness habits!")

if __name__ == '__main__':
    init_habits()
