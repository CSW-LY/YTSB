# Test keyword matching logic
text = "查找零件"
keyword = "查找零件"

text_normalized = text.strip().lower()
keyword_normalized = keyword.strip().lower()

print(f"Text: {text}")
print(f"Keyword: {keyword}")
print(f"Text normalized: {text_normalized}")
print(f"Keyword normalized: {keyword_normalized}")
print(f"Match result: {keyword_normalized in text_normalized}")

# Test with strip
text_with_spaces = " 查找零件 "
print(f"\nText with spaces: '{text_with_spaces}'")
print(f"Stripped: '{text_with_spaces.strip()}'")
print(f"Match: {keyword_normalized in text_with_spaces.strip().lower()}")
