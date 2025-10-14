"""Neo4j Graph RAG Database for ContextVault.

This module provides a graph-based knowledge storage and retrieval system that combines:
- Entity extraction (companies, people, projects, amounts, dates)
- Relationship graphs (WORKS_WITH, REFERENCES, MENTIONS, etc.)
- Vector embeddings for semantic search
- Graph traversal for complex queries
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

# Optional imports - Graph RAG dependencies
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    logger.warning("spaCy not available. Install with: pip install spacy && python -m spacy download en_core_web_sm")
    SPACY_AVAILABLE = False
    spacy = None

try:
    from neo4j import GraphDatabase, Driver, Session
    NEO4J_AVAILABLE = True
except ImportError:
    logger.warning("Neo4j driver not available. Install with: pip install neo4j")
    NEO4J_AVAILABLE = False
    GraphDatabase = None
    Driver = None
    Session = None

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    logger.warning("Sentence transformers not available. Install with: pip install sentence-transformers")
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None


class EntityExtractor:
    """Extract entities from text using spaCy NER."""

    def __init__(self, model_name: str = "en_core_web_sm"):
        """Initialize the entity extractor.

        Args:
            model_name: spaCy model to use for NER
        """
        if not SPACY_AVAILABLE:
            logger.error("spaCy is not available. Cannot initialize EntityExtractor.")
            self.nlp = None
            return

        try:
            self.nlp = spacy.load(model_name)
            logger.info(f"Loaded spaCy model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load spaCy model: {e}")
            logger.info("Install the model with: python -m spacy download en_core_web_sm")
            self.nlp = None

    def extract_entities(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """Extract entities from text.

        Args:
            text: Text to extract entities from

        Returns:
            Dictionary mapping entity types to lists of entities:
            {
                'PERSON': [{'text': 'John Smith', 'start': 0, 'end': 10}],
                'ORG': [{'text': 'Acme Corp', 'start': 20, 'end': 29}],
                'DATE': [...],
                'MONEY': [...],
                'GPE': [...] (Geo-political entities)
            }
        """
        if not self.nlp:
            logger.warning("spaCy model not loaded. Returning empty entities.")
            return {}

        doc = self.nlp(text)

        entities = {}
        for ent in doc.ents:
            entity_type = ent.label_
            if entity_type not in entities:
                entities[entity_type] = []

            entities[entity_type].append({
                'text': ent.text,
                'start': ent.start_char,
                'end': ent.end_char,
                'label': entity_type
            })

        return entities

    def extract_relationships(self, text: str, entities: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Extract relationships between entities using dependency parsing.

        Args:
            text: Original text
            entities: Extracted entities from extract_entities()

        Returns:
            List of relationships: [
                {'source': 'John Smith', 'source_type': 'PERSON',
                 'target': 'Acme Corp', 'target_type': 'ORG',
                 'relation': 'WORKS_WITH'}
            ]
        """
        if not self.nlp:
            logger.warning("spaCy model not loaded. Returning empty relationships.")
            return []

        doc = self.nlp(text)
        relationships = []

        # Create entity lookup by text
        entity_lookup = {}
        for ent_type, ent_list in entities.items():
            for ent in ent_list:
                entity_lookup[ent['text']] = ent_type

        # Extract relationships from dependency tree
        for token in doc:
            # Look for verbs connecting entities
            if token.pos_ == "VERB":
                # Find subject and object
                subjects = [child for child in token.children if child.dep_ in ("nsubj", "nsubjpass")]
                objects = [child for child in token.children if child.dep_ in ("dobj", "pobj", "obj")]

                for subj in subjects:
                    for obj in objects:
                        subj_text = subj.text
                        obj_text = obj.text

                        # Check if both are entities
                        if subj_text in entity_lookup and obj_text in entity_lookup:
                            relationships.append({
                                'source': subj_text,
                                'source_type': entity_lookup[subj_text],
                                'target': obj_text,
                                'target_type': entity_lookup[obj_text],
                                'relation': self._infer_relation_type(
                                    entity_lookup[subj_text],
                                    entity_lookup[obj_text],
                                    token.lemma_
                                )
                            })

        return relationships

    def _infer_relation_type(self, source_type: str, target_type: str, verb: str) -> str:
        """Infer relationship type from entity types and verb.

        Args:
            source_type: Source entity type (PERSON, ORG, etc.)
            target_type: Target entity type
            verb: Verb connecting them

        Returns:
            Relationship type (WORKS_WITH, REFERENCES, MENTIONS, etc.)
        """
        # Business relationship patterns
        if source_type == "PERSON" and target_type == "ORG":
            if verb in ("work", "employ", "hire", "join"):
                return "WORKS_AT"
            elif verb in ("found", "create", "establish"):
                return "FOUNDED"
            elif verb in ("lead", "manage", "direct"):
                return "MANAGES"

        if source_type == "ORG" and target_type == "ORG":
            if verb in ("acquire", "buy", "purchase"):
                return "ACQUIRED"
            elif verb in ("partner", "collaborate"):
                return "PARTNERS_WITH"
            elif verb in ("compete", "rival"):
                return "COMPETES_WITH"

        if target_type == "MONEY":
            if verb in ("pay", "receive", "earn"):
                return "TRANSACTED"
            elif verb in ("worth", "value"):
                return "VALUED_AT"

        if target_type == "DATE":
            if verb in ("occur", "happen", "schedule"):
                return "OCCURRED_ON"
            elif verb in ("deadline", "due"):
                return "DUE_ON"

        # Default relationship
        return "MENTIONS"


class GraphRAGDatabase:
    """Neo4j Graph RAG Database for knowledge storage and retrieval."""

    def __init__(
        self,
        uri: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        """Initialize the Graph RAG database.

        Args:
            uri: Neo4j connection URI (defaults to config)
            username: Neo4j username (defaults to config)
            password: Neo4j password (defaults to config)
            embedding_model: Sentence transformer model for embeddings
        """
        # Import config if not provided
        if uri is None or username is None or password is None:
            try:
                from ..config import settings
                self.uri = uri or settings.neo4j_uri
                self.username = username or settings.neo4j_user
                self.password = password or settings.neo4j_password
            except ImportError:
                # Fallback to defaults if config not available
                self.uri = uri or "bolt://localhost:7687"
                self.username = username or "neo4j"
                self.password = password or "password"
        else:
            self.uri = uri
            self.username = username
            self.password = password

        # Initialize components
        self.driver: Optional[Driver] = None

        # Initialize entity extractor if spaCy is available
        if SPACY_AVAILABLE:
            self.entity_extractor = EntityExtractor()
        else:
            logger.warning("Entity extraction unavailable - spaCy not installed")
            self.entity_extractor = None

        # Initialize embedding model if sentence-transformers available
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer(embedding_model)
                logger.info(f"Loaded embedding model: {embedding_model}")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                self.embedding_model = None
        else:
            logger.warning("Embeddings unavailable - sentence-transformers not installed")
            self.embedding_model = None

        # Connect to Neo4j if driver available
        if NEO4J_AVAILABLE:
            self._connect()
            # Initialize schema
            self._initialize_schema()
        else:
            logger.error("Neo4j driver not available. Graph RAG functionality disabled.")
            logger.info("Install with: pip install neo4j")

    def _connect(self):
        """Establish connection to Neo4j."""
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password)
            )
            # Test connection
            self.driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {self.uri}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            logger.warning("Neo4j Graph RAG is not available. Please ensure Neo4j is running.")
            self.driver = None

    def is_available(self) -> bool:
        """Check if Neo4j is available.

        Returns:
            True if Neo4j connection is active
        """
        return self.driver is not None

    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()
            logger.info("Closed Neo4j connection")

    def _initialize_schema(self):
        """Initialize Neo4j graph schema with indexes and constraints."""
        if not self.is_available():
            return

        schema_queries = [
            # Create constraints (unique IDs)
            "CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",

            # Create indexes for faster lookups
            "CREATE INDEX document_content IF NOT EXISTS FOR (d:Document) ON (d.content)",
            "CREATE INDEX entity_text IF NOT EXISTS FOR (e:Entity) ON (e.text)",
            "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)",

            # Vector index for semantic search (Neo4j 5.11+)
            """
            CREATE VECTOR INDEX document_embeddings IF NOT EXISTS
            FOR (d:Document) ON (d.embedding)
            OPTIONS {indexConfig: {
                `vector.dimensions`: 384,
                `vector.similarity_function`: 'cosine'
            }}
            """,
        ]

        with self.driver.session() as session:
            for query in schema_queries:
                try:
                    session.run(query)
                    logger.debug(f"Executed schema query: {query[:50]}...")
                except Exception as e:
                    # Some queries might fail if already exists or Neo4j version doesn't support
                    logger.debug(f"Schema query failed (may be expected): {e}")

        logger.info("Initialized Neo4j schema")

    def _generate_entity_id(self, text: str, entity_type: str) -> str:
        """Generate unique ID for entity.

        Args:
            text: Entity text
            entity_type: Entity type

        Returns:
            Unique entity ID
        """
        content = f"{entity_type}:{text.lower()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def add_document(
        self,
        content: str,
        document_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        extract_entities: bool = True
    ) -> Dict[str, Any]:
        """Add a document to the graph database with entity extraction.

        Args:
            content: Document content
            document_id: Unique document identifier
            metadata: Additional metadata
            extract_entities: Whether to extract and link entities

        Returns:
            Dictionary with statistics:
            {
                'document_id': '...',
                'entities_extracted': 15,
                'relationships_created': 8
            }
        """
        if not self.is_available():
            raise RuntimeError("Neo4j is not available")

        # Generate embedding
        embedding = None
        if self.embedding_model:
            embedding = self.embedding_model.encode(content).tolist()

        # Extract entities
        entities_data = {}
        relationships_data = []

        if extract_entities:
            entities_data = self.entity_extractor.extract_entities(content)
            relationships_data = self.entity_extractor.extract_relationships(content, entities_data)

        # Create document node
        with self.driver.session() as session:
            # Add document
            doc_query = """
            MERGE (d:Document {id: $doc_id})
            SET d.content = $content,
                d.created_at = datetime($created_at),
                d.updated_at = datetime($updated_at)
            """
            if embedding:
                doc_query += ", d.embedding = $embedding"

            if metadata:
                for key, value in metadata.items():
                    doc_query += f", d.{key} = ${key}"

            params = {
                'doc_id': document_id,
                'content': content,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            if embedding:
                params['embedding'] = embedding
            if metadata:
                params.update(metadata)

            session.run(doc_query, params)

            # Add entities
            entity_count = 0
            for entity_type, entity_list in entities_data.items():
                for entity in entity_list:
                    entity_id = self._generate_entity_id(entity['text'], entity_type)

                    entity_query = """
                    MERGE (e:Entity {id: $entity_id})
                    SET e.text = $text,
                        e.type = $type,
                        e.updated_at = datetime($updated_at)
                    WITH e
                    MATCH (d:Document {id: $doc_id})
                    MERGE (d)-[r:MENTIONS]->(e)
                    SET r.position = $position
                    """

                    session.run(entity_query, {
                        'entity_id': entity_id,
                        'text': entity['text'],
                        'type': entity_type,
                        'doc_id': document_id,
                        'position': entity['start'],
                        'updated_at': datetime.now().isoformat()
                    })
                    entity_count += 1

            # Add relationships between entities
            relationship_count = 0
            for rel in relationships_data:
                source_id = self._generate_entity_id(rel['source'], rel['source_type'])
                target_id = self._generate_entity_id(rel['target'], rel['target_type'])

                rel_query = f"""
                MATCH (s:Entity {{id: $source_id}})
                MATCH (t:Entity {{id: $target_id}})
                MERGE (s)-[r:{rel['relation']}]->(t)
                SET r.discovered_in = $doc_id,
                    r.updated_at = datetime($updated_at)
                """

                session.run(rel_query, {
                    'source_id': source_id,
                    'target_id': target_id,
                    'doc_id': document_id,
                    'updated_at': datetime.now().isoformat()
                })
                relationship_count += 1

        logger.info(f"Added document {document_id} with {entity_count} entities and {relationship_count} relationships")

        return {
            'document_id': document_id,
            'entities_extracted': entity_count,
            'relationships_created': relationship_count
        }

    def search(
        self,
        query: str,
        limit: int = 10,
        use_graph: bool = True,
        min_relevance: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Hybrid search combining vector similarity and graph traversal.

        Args:
            query: Search query
            limit: Maximum number of results
            use_graph: Whether to use graph traversal (True) or pure vector search (False)
            min_relevance: Minimum relevance score (0-1)

        Returns:
            List of search results with scores and relationships
        """
        if not self.is_available():
            raise RuntimeError("Neo4j is not available")

        # Generate query embedding
        query_embedding = None
        if self.embedding_model:
            query_embedding = self.embedding_model.encode(query).tolist()

        results = []

        with self.driver.session() as session:
            if use_graph:
                # Extract entities from query
                query_entities = self.entity_extractor.extract_entities(query)

                # Find documents connected to query entities
                for entity_type, entity_list in query_entities.items():
                    for entity in entity_list:
                        entity_id = self._generate_entity_id(entity['text'], entity_type)

                        # Graph traversal query
                        graph_query = """
                        MATCH (e:Entity {id: $entity_id})
                        MATCH (d:Document)-[r:MENTIONS]->(e)
                        OPTIONAL MATCH (d)-[:MENTIONS]->(other:Entity)
                        WITH d, e, collect(DISTINCT other) as related_entities
                        RETURN d.id as doc_id,
                               d.content as content,
                               e.text as matched_entity,
                               e.type as entity_type,
                               related_entities
                        LIMIT $limit
                        """

                        result = session.run(graph_query, {
                            'entity_id': entity_id,
                            'limit': limit
                        })

                        for record in result:
                            # Calculate relevance score
                            relevance = 0.8  # Base score for entity match

                            if query_embedding and record['content']:
                                doc_embedding = self.embedding_model.encode(record['content'])
                                from numpy import dot
                                from numpy.linalg import norm
                                semantic_similarity = dot(query_embedding, doc_embedding) / (
                                    norm(query_embedding) * norm(doc_embedding)
                                )
                                relevance = 0.5 * relevance + 0.5 * semantic_similarity

                            if relevance >= min_relevance:
                                results.append({
                                    'document_id': record['doc_id'],
                                    'content': record['content'],
                                    'matched_entity': record['matched_entity'],
                                    'entity_type': record['entity_type'],
                                    'related_entities': [
                                        {'text': e['text'], 'type': e['type']}
                                        for e in record['related_entities']
                                    ] if record['related_entities'] else [],
                                    'relevance_score': relevance,
                                    'search_type': 'graph'
                                })

            # Also do pure vector search if no graph results
            if not results and query_embedding:
                vector_query = """
                MATCH (d:Document)
                WHERE d.embedding IS NOT NULL
                WITH d,
                     gds.similarity.cosine(d.embedding, $query_embedding) as similarity
                WHERE similarity >= $min_relevance
                RETURN d.id as doc_id,
                       d.content as content,
                       similarity as relevance_score
                ORDER BY similarity DESC
                LIMIT $limit
                """

                try:
                    result = session.run(vector_query, {
                        'query_embedding': query_embedding,
                        'min_relevance': min_relevance,
                        'limit': limit
                    })

                    for record in result:
                        results.append({
                            'document_id': record['doc_id'],
                            'content': record['content'],
                            'relevance_score': record['relevance_score'],
                            'search_type': 'vector'
                        })
                except Exception as e:
                    logger.debug(f"Vector search failed: {e}")
                    # Fallback to simple text matching
                    pass

        # Sort by relevance and deduplicate
        seen_docs = set()
        unique_results = []
        for result in sorted(results, key=lambda x: x['relevance_score'], reverse=True):
            if result['document_id'] not in seen_docs:
                seen_docs.add(result['document_id'])
                unique_results.append(result)

        return unique_results[:limit]

    def get_entity_relationships(
        self,
        entity_text: str,
        entity_type: Optional[str] = None,
        depth: int = 1
    ) -> Dict[str, Any]:
        """Get all relationships for an entity.

        Args:
            entity_text: Entity text to search for
            entity_type: Entity type (optional)
            depth: Relationship depth (1 = direct connections, 2 = connections of connections)

        Returns:
            Dictionary with entity info and relationships:
            {
                'entity': {'text': '...', 'type': '...'},
                'relationships': [
                    {'target': '...', 'type': 'WORKS_AT', 'target_type': 'ORG'},
                    ...
                ]
            }
        """
        if not self.is_available():
            raise RuntimeError("Neo4j is not available")

        entity_id = self._generate_entity_id(entity_text, entity_type or "UNKNOWN")

        with self.driver.session() as session:
            query = f"""
            MATCH (e:Entity {{id: $entity_id}})
            OPTIONAL MATCH path = (e)-[r*1..{depth}]-(connected:Entity)
            RETURN e.text as entity_text,
                   e.type as entity_type,
                   collect(DISTINCT {{
                       target: connected.text,
                       target_type: connected.type,
                       relationship: type(last(relationships(path)))
                   }}) as relationships
            """

            result = session.run(query, {'entity_id': entity_id})
            record = result.single()

            if record:
                return {
                    'entity': {
                        'text': record['entity_text'],
                        'type': record['entity_type']
                    },
                    'relationships': [
                        r for r in record['relationships']
                        if r['target'] is not None
                    ]
                }

        return {'entity': None, 'relationships': []}

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics.

        Returns:
            Statistics dictionary with node/relationship counts
        """
        if not self.is_available():
            return {
                'available': False,
                'error': 'Neo4j is not connected'
            }

        with self.driver.session() as session:
            stats_query = """
            MATCH (d:Document) WITH count(d) as doc_count
            MATCH (e:Entity) WITH doc_count, count(e) as entity_count
            MATCH ()-[r]->() WITH doc_count, entity_count, count(r) as rel_count
            RETURN doc_count, entity_count, rel_count
            """

            result = session.run(stats_query)
            record = result.single()

            return {
                'available': True,
                'total_documents': record['doc_count'] if record else 0,
                'total_entities': record['entity_count'] if record else 0,
                'total_relationships': record['rel_count'] if record else 0,
                'database': 'Neo4j Graph RAG'
            }
