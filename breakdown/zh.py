import re


# Function to get the tone based on the diacritic
def get_tone(pinyin):
    # Define a mapping for the diacritics (tones)
    tone_map = {
        'ā': 1, 'á': 2, 'ǎ': 3, 'à': 4,
        'ē': 1, 'é': 2, 'ě': 3, 'è': 4,
        'ī': 1, 'í': 2, 'ǐ': 3, 'ì': 4,
        'ō': 1, 'ó': 2, 'ǒ': 3, 'ò': 4,
        'ū': 1, 'ú': 2, 'ǔ': 3, 'ù': 4,
        'ǖ': 1, 'ǘ': 2, 'ǚ': 3, 'ǜ': 4
    }

    # Find the vowel with diacritic in the pinyin string and map it to the tone
    for char in pinyin:
        if char in tone_map:
            return tone_map[char]
    return None  # If no diacritic is found, return None (unlikely in standard pinyin)


# Function to process a phrase into words, letters, and their tones
def process_pinyin_phrase(phrase):
    # Split the phrase into words
    words = phrase.split()

    # List to hold the breakdown of the phrase
    breakdown = []

    for word in words:
        word_data = {'letters': ', '.join(list(word)), 'tone': get_tone(word)}
        breakdown.append(word_data)

    return breakdown
