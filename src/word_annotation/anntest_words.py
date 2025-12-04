from annotator import MandarinAnnotator

annotator = MandarinAnnotator()

# Test text
text = "北京故宫是中国明清两代的皇家宫殿"

print("=" * 60)
print("CHARACTER-LEVEL ANNOTATIONS (as_words=False)")
print("=" * 60)
char_annotations = annotator.annotate(text, as_words=False)
for i, ann in enumerate(char_annotations[:10]):  # Show first 10
    print(f"{i+1}. {ann['character']}: {ann['pinyin']}")

print("\n" + "=" * 60)
print("WORD-LEVEL ANNOTATIONS (as_words=True)")
print("=" * 60)
word_annotations = annotator.annotate(text, as_words=True)
for i, word in enumerate(word_annotations[:10]):  # Show first 10
    print(f"{i+1}. Word: '{word['word']}'")
    print(f"   Characters: {word['characters']}")
    print(f"   Pinyin: {word['pinyin']}")
    print()
