"""
Context Assembler Service

Deduplicates child chunks and assembles parent chunks for better context continuity.
Handles chunk grouping and parent document reconstruction.
"""

import logging
import time
from typing import List, Dict, Any, Set, Tuple
from app.core.retrieval_config import RETRIEVAL_CONFIG

logger = logging.getLogger("legalgpt.retrieval.assembly")


class ContextAssembler:
    """Assembles and deduplicates context chunks."""

    def __init__(self):
        """Initialize context assembler."""
        self.dedupe_threshold = RETRIEVAL_CONFIG["dedupe_threshold"]

    def deduplicate_by_parent(
        self,
        chunks: List[Dict[str, Any]],
        min_similarity: float = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, List[int]]]:
        """
        Deduplicate child chunks by grouping into parent chunks.
        
        Returns one assembled parent chunk per unique parent instead of
        multiple duplicate child chunks.
        
        Args:
            chunks: List of ranked chunks (may have duplicates from same parent)
            min_similarity: Minimum similarity for grouping (default: config threshold)
            
        Returns:
            Tuple of (deduplicated_chunks, mapping of parent_id -> child_indices)
        """
        start_time = time.time()
        
        if min_similarity is None:
            min_similarity = self.dedupe_threshold
        
        if not chunks:
            return [], {}
        
        # Group chunks by parent
        parent_groups = {}  # parent_id -> list of (chunk_idx, chunk)
        child_chunk_ids = set()  # Track which chunks are children
        
        for idx, chunk in enumerate(chunks):
            # Check if chunk has parent info
            parent_id = chunk.get("parent_id")
            
            if parent_id:
                child_chunk_ids.add(chunk.get("id"))
                if parent_id not in parent_groups:
                    parent_groups[parent_id] = []
                parent_groups[parent_id].append((idx, chunk))
            else:
                # Orphan chunk (no parent) - treat as its own parent
                if idx not in parent_groups:
                    parent_groups[idx] = []
                parent_groups[idx].append((idx, chunk))
        
        # Assemble deduplicated chunks
        deduplicated = []
        parent_mapping = {}  # parent_id -> list of original child indices
        
        for parent_id, group in parent_groups.items():
            # Sort by position/order
            group.sort(key=lambda x: x[1].get("chunk_number", x[0]))
            
            # Create assembled parent chunk
            assembled = self._assemble_parent_chunk(group, parent_id)
            deduplicated.append(assembled)
            
            # Track mapping
            parent_mapping[str(parent_id)] = [idx for idx, _ in group]
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.debug(
            f"Deduplication | input_chunks={len(chunks)} | "
            f"parent_groups={len(parent_groups)} | "
            f"output_chunks={len(deduplicated)} | latency_ms={elapsed_ms}"
        )
        
        return deduplicated, parent_mapping

    def _assemble_parent_chunk(
        self,
        child_group: List[Tuple[int, Dict[str, Any]]],
        parent_id: Any
    ) -> Dict[str, Any]:
        """
        Assemble multiple child chunks into single parent chunk.
        
        Args:
            child_group: List of (index, chunk) tuples
            parent_id: Parent identifier
            
        Returns:
            Assembled parent chunk dictionary
        """
        if not child_group:
            return {}
        
        # Use first chunk as base
        first_idx, first_chunk = child_group[0]
        
        # Check if parent content already exists
        if "parent_content" in first_chunk:
            # Parent already assembled - use as is
            assembled = first_chunk.copy()
        else:
            # Assemble from children
            assembled = first_chunk.copy()
            
            # Combine content from all children
            if len(child_group) > 1:
                child_contents = []
                for idx, chunk in child_group:
                    if "content" in chunk:
                        child_contents.append(chunk["content"])
                
                # Join with separator
                if child_contents:
                    combined_content = "\n\n".join(child_contents)
                    assembled["content"] = combined_content
                    assembled["combined_from_children"] = len(child_group)
        
        # Update metadata
        # Prefer the complete persisted parent text over partial child text.
        parent_text = first_chunk.get('parent_text') or first_chunk.get('metadata', {}).get('parent_text')
        if parent_text:
            assembled['content'] = parent_text
            assembled['parent_text'] = parent_text
        assembled['child_ids'] = [chunk.get('child_id') or chunk.get('id') for _, chunk in child_group]
        assembled["parent_id"] = parent_id
        assembled["child_count"] = len(child_group)
        assembled["child_indices"] = [idx for idx, _ in child_group]
        
        # Use highest score from children
        if "_scoring" in first_chunk:
            assembled["_scoring"] = first_chunk["_scoring"]
        
        return assembled

    def group_chunks_by_proximity(
        self,
        chunks: List[Dict[str, Any]],
        max_distance: int = 2
    ) -> List[List[Dict[str, Any]]]:
        """
        Group chunks that are near each other in document.
        
        Args:
            chunks: List of chunks
            max_distance: Maximum chunk number distance for grouping
            
        Returns:
            List of grouped chunk lists
        """
        if not chunks:
            return []
        
        groups = []
        current_group = []
        last_chunk_number = None
        
        for chunk in chunks:
            chunk_number = chunk.get("chunk_number", 0)
            
            # Start new group if far from last
            if last_chunk_number is not None:
                distance = abs(chunk_number - last_chunk_number)
                if distance > max_distance:
                    if current_group:
                        groups.append(current_group)
                    current_group = []
            
            current_group.append(chunk)
            last_chunk_number = chunk_number
        
        # Add final group
        if current_group:
            groups.append(current_group)
        
        return groups

    def merge_with_context(
        self,
        primary_chunks: List[Dict[str, Any]],
        context_chunks: List[Dict[str, Any]],
        context_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Merge primary chunks with surrounding context.
        
        Enriches primary chunks with preceding/following context chunks
        without duplicating primary content.
        
        Args:
            primary_chunks: Main chunks to keep
            context_chunks: Additional context chunks
            context_weight: Weight for context chunk relevance
            
        Returns:
            Merged chunks with enriched context
        """
        merged = []
        primary_ids = {c.get("id") for c in primary_chunks}
        
        for primary in primary_chunks:
            enriched = primary.copy()
            
            # Find related context chunks
            related_context = []
            for context in context_chunks:
                if context.get("id") not in primary_ids:
                    # Check if related (same parent, nearby position)
                    if self._is_related_context(primary, context):
                        related_context.append(context)
            
            # Add context to chunk metadata
            if related_context:
                enriched["related_context"] = related_context[:3]  # Top 3 context chunks
                enriched["has_context"] = True
            
            merged.append(enriched)
        
        return merged

    def _is_related_context(
        self,
        primary: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """Check if context chunk is related to primary chunk."""
        # Same parent
        if primary.get("parent_id") == context.get("parent_id"):
            return True
        
        # Same document
        if primary.get("document_id") == context.get("document_id"):
            # Nearby chunks
            p_num = primary.get("chunk_number", 0)
            c_num = context.get("chunk_number", 0)
            if abs(p_num - c_num) <= 2:
                return True
        
        return False


class DeduplicationMetrics:
    """Tracks deduplication statistics."""

    def __init__(self):
        """Initialize metrics tracker."""
        self.total_input_chunks = 0
        self.total_output_chunks = 0
        self.total_parents = 0
        self.average_children_per_parent = 0.0
        self.deduplication_ratio = 0.0

    def update(
        self,
        input_count: int,
        output_count: int,
        parent_count: int
    ) -> None:
        """
        Update deduplication metrics.
        
        Args:
            input_count: Number of input chunks
            output_count: Number of output chunks
            parent_count: Number of unique parents
        """
        self.total_input_chunks = input_count
        self.total_output_chunks = output_count
        self.total_parents = parent_count
        
        if parent_count > 0:
            self.average_children_per_parent = input_count / parent_count
        
        if input_count > 0:
            self.deduplication_ratio = 1.0 - (output_count / input_count)

    def log(self) -> None:
        """Log deduplication statistics."""
        logger.info(
            f"Deduplication metrics | "
            f"input={self.total_input_chunks} | "
            f"output={self.total_output_chunks} | "
            f"parents={self.total_parents} | "
            f"avg_children={self.average_children_per_parent:.2f} | "
            f"reduction={self.deduplication_ratio:.1%}"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "input_chunks": self.total_input_chunks,
            "output_chunks": self.total_output_chunks,
            "parent_chunks": self.total_parents,
            "avg_children_per_parent": self.average_children_per_parent,
            "deduplication_ratio": self.deduplication_ratio,
        }


def get_context_assembler() -> ContextAssembler:
    """
    Get or create context assembler singleton.
    
    Returns:
        ContextAssembler instance
    """
    if not hasattr(get_context_assembler, "_instance"):
        get_context_assembler._instance = ContextAssembler()
    return get_context_assembler._instance
