from typing import List, Dict, Tuple
from difflib import SequenceMatcher

class DuplicationDetector:
    """Detect code duplication."""
    
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
    
    def detect(self, code: str, min_lines: int = 4) -> List[Dict]:
        """Detect duplicated code blocks using character shingles and similarity."""
        lines = code.split('\n')
        if len(lines) < min_lines:
            return []
            
        duplicates = []
        # Create shingles for each block of min_lines
        blocks = []
        for i in range(len(lines) - min_lines + 1):
            block_text = "\n".join(lines[i:i+min_lines]).strip()
            if len(block_text) > 20: # Ignore very short blocks
                blocks.append((i, block_text))
        
        # Compare blocks
        for i in range(len(blocks)):
            idx1, text1 = blocks[i]
            for j in range(i + 1, len(blocks)):
                idx2, text2 = blocks[j]
                
                # Simple shingle similarity (jaccard-ish)
                similarity = self._calculate_similarity(text1, text2)
                
                if similarity >= self.similarity_threshold:
                    duplicates.append({
                        "block1_start": idx1 + 1,
                        "block1_end": idx1 + min_lines,
                        "block2_start": idx2 + 1,
                        "block2_end": idx2 + min_lines,
                        "similarity": round(similarity, 2),
                        "message": f"Similar code found (similarity: {round(similarity*100)}%)"
                    })
        
        return self._merge_overlapping(duplicates)
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text blocks."""
        if not text1 or not text2: return 0.0
        # Character-level 3-gram shingles
        def get_shingles(text):
            return set(text[i:i+3] for i in range(len(text)-2))
        
        s1, s2 = get_shingles(text1), get_shingles(text2)
        if not s1 or not s2: return 0.0
        intersection = s1.intersection(s2)
        union = s1.union(s2)
        return len(intersection) / len(union)

    def _merge_overlapping(self, duplicates: List[Dict]) -> List[Dict]:
        """Merge overlapping duplicate blocks."""
        if not duplicates:
            return []
        
        # Sort by start line
        sorted_dups = sorted(duplicates, key=lambda x: x['block1_start'])
        merged = [sorted_dups[0]]
        
        for current in sorted_dups[1:]:
            last = merged[-1]
            
            # Check if overlapping
            if current['block1_start'] <= last['block1_end']:
                # Merge
                last['block1_end'] = max(last['block1_end'], current['block1_end'])
                last['similarity'] = max(last['similarity'], current['similarity'])
            else:
                merged.append(current)
        
        return merged
