from annotator import MandarinAnnotator

annotator = MandarinAnnotator()

# Test text about the Forbidden City
text = "北京故宫是中国明清两代的皇家宫殿，旧称为紫禁城，是中国古代宫廷建筑的精华。北京故宫以三大殿为中心，占地面积72万平方米，建筑面积约15万平方米，有大小宫殿七十多座，房屋九千余间。是世界上现存规模最大、保存最为完整的木质结构古建筑之一。\n故宫博物院是一座特殊的博物馆，成立于1925年，建立在紫禁城的基础上。近几年，在人们头脑中陈旧甚至略微显得古板的故宫开始活跃起来。一部《我在故宫修文物》让普通人了解到故宫背后的工匠精神，《 国家宝藏》恢弘的气势与现代科技结合，让人们见识到大国风范\n故宫文创，依托悠久的故宫历史，发掘新的产品形态，将古老与现代结合，将历史与商业叠加。故宫口红，故宫项链，故宫台历等等，被人们广为使用。"

# Test 1: Character-level annotations
print("=" * 70)
print("TEST 1: CHARACTER-LEVEL ANNOTATIONS")
print("=" * 70)
char_annotations = annotator.annotate(text, as_words=False)
print(f"Total characters: {len(char_annotations)}\n")
# Show first 10
for ann in char_annotations:
    print(
        f"  {ann['character']}: {ann['pinyin']} → {ann['definitions'][0] if ann['definitions'] else 'N/A'}"
    )
print(f"  ... and {len(char_annotations) - 10} more characters\n")

# Test 2: Word-level annotations with segmentation
print("=" * 70)
print("TEST 2: WORD-LEVEL ANNOTATIONS (with proper segmentation)")
print("=" * 70)
word_annotations = annotator.annotate(text, as_words=True)
print(f"Total words: {len(word_annotations)}\n")
# Show first 15 words
for ann in word_annotations:
    definition = ann["definitions"] if ann["definitions"] else "N/A"
    print(f"  '{ann['word']:6s}' → {ann['pinyin']:20s} | {definition}")
print(f"  ... and {len(word_annotations) - 15} more words\n")

# Test 3: Detailed word information
print("=" * 70)
print("TEST 3: DETAILED WORD INFORMATION")
print("=" * 70)
sample_words = word_annotations
for i, ann in enumerate(sample_words, 1):
    print(f"{i}. Word: '{ann['word']}'")
    print(f"   Pinyin: {ann['pinyin']}")
    print(f"   Characters: {ann['characters']}")
    print(f"   Character count: {ann['character_count']}")
    if ann["definitions"]:
        print(f"   Definition: {ann['definitions'][0]}")
    print()
