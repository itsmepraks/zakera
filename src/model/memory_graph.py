import logging
import re
from typing import List, Dict, Set, Optional, Any
from dataclasses import dataclass, field
from .memory import Message

logger = logging.getLogger(__name__)

@dataclass
class Entity:
    name: str
    label: str = "Entity"
    properties: Dict[str, Any] = field(default_factory=dict)

class GraphMemory:
    """
    Experimental Knowledge Graph-based memory system.
    Extracts entities and simple relationships from conversation history.
    """
    
    def __init__(self):
        self.nodes: Dict[str, Entity] = {}
        self.edges: List[Dict[str, str]] = [] # list of (source, target, relation)
        self.history: List[Message] = []

    def _simple_entity_extraction(self, text: str) -> List[str]:
        # Basic heuristic: extract capitalized words as potential entities
        return list(set(re.findall(r'\b[A-Z][a-z]+\b', text)))

    def add_message(self, message: Message):
        """Adds a message to memory and updates the internal graph."""
        self.history.append(message)
        entities = self._simple_entity_extraction(message.content)
        
        for e in entities:
            if e not in self.nodes:
                self.nodes[e] = Entity(name=e)
            
            # Create co-occurrence edges between entities in the same message
            for other in entities:
                if e != other:
                    edge = {"source": e, "target": other, "relation": "mentioned_with"}
                    if edge not in self.edges:
                        self.edges.append(edge)

    def query_graph(self, topic: str) -> Dict[str, Any]:
        """Returns the neighborhood of a topic in the graph."""
        if topic not in self.nodes:
            return {"entity": topic, "status": "not_found"}
            
        related = [edge for edge in self.edges if edge["source"] == topic or edge["target"] == topic]
        return {
            "entity": self.nodes[topic],
            "connections": related
        }

    def get_knowledge_context(self, query: str) -> str:
        """Generates a text context based on graph knowledge for a given query."""
        query_entities = self._simple_entity_extraction(query)
        context_snippets = []
        
        for entity in query_entities:
            result = self.query_graph(entity)
            if "connections" in result:
                connections = [e["target"] if e["source"] == entity else e["source"] for e in result["connections"]]
                if connections:
                    context_snippets.append(f"Knowledge about {entity}: commonly associated with {', '.join(connections[:5])}.")
        
        return " ".join(context_snippets)
