"""
Arquitetura escalável para classificação hierárquica de notícias.

Este arquivo deve ser salvo como: app/services/ai/hierarchical/scalable_architecture.py
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Protocol, Union
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path

logger = logging.getLogger(__name__)

# Definições de tipos e enums
class ClassificationLevel(Enum):
    """Níveis de classificação hierárquica."""
    PRIMARY = "primary"      # Categoria principal (ex: discriminação)
    SECONDARY = "secondary"  # Subcategoria (ex: educacional)
    TERTIARY = "tertiary"    # Especificação (ex: negação de matrícula)

class Severity(Enum):
    """Níveis de severidade."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class ClassificationResult:
    """Resultado de classificação."""
    category: str
    confidence: float
    level: ClassificationLevel
    severity: Severity
    evidence: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class Article:
    """Representação de artigo."""
    id: str
    title: str
    content: str
    source: str
    publish_date: datetime
    url: str
    metadata: Dict[str, Any] = field(default_factory=dict)

# Protocolos para injeção de dependência
class ClassifierProtocol(Protocol):
    """Protocolo para classificadores."""
    
    async def classify(self, article: Article) -> List[ClassificationResult]:
        """Classifica um artigo."""
        ...

class RepositoryProtocol(Protocol):
    """Protocolo para repositórios de dados."""
    
    async def save_classification(self, article_id: str, results: List[ClassificationResult]) -> None:
        """Salva resultado de classificação."""
        ...
    
    async def get_classification_history(self, article_id: str) -> List[ClassificationResult]:
        """Obtém histórico de classificações."""
        ...

class EventPublisherProtocol(Protocol):
    """Protocolo para publicação de eventos."""
    
    async def publish(self, event_type: str, data: Dict[str, Any]) -> None:
        """Publica um evento."""
        ...

# Base abstratas
class BaseClassifier(ABC):
    """Classe base para classificadores."""
    
    def __init__(self, name: str, version: str = "1.0"):
        self.name = name
        self.version = version
        self.is_initialized = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """Inicializa o classificador."""
        pass
    
    @abstractmethod
    async def classify(self, article: Article) -> List[ClassificationResult]:
        """Classifica um artigo."""
        pass
    
    @abstractmethod
    async def get_supported_categories(self) -> List[str]:
        """Retorna categorias suportadas."""
        pass
    
    async def validate_input(self, article: Article) -> bool:
        """Valida entrada."""
        return bool(article.content and article.content.strip())

class BaseRepository(ABC):
    """Classe base para repositórios."""
    
    @abstractmethod
    async def save_classification(self, article_id: str, results: List[ClassificationResult]) -> None:
        """Salva resultado de classificação."""
        pass
    
    @abstractmethod
    async def get_classification_history(self, article_id: str) -> List[ClassificationResult]:
        """Obtém histórico de classificações."""
        pass

# Implementações específicas
class DiscriminationClassifier(BaseClassifier):
    """Classificador específico para discriminação."""
    
    def __init__(self):
        super().__init__("discrimination_classifier", "2.0")
        self.categories = {
            "discrimination.educational": {
                "name": "Discriminação Educacional",
                "subcategories": [
                    "enrollment_denial",
                    "inadequate_support", 
                    "social_exclusion",
                    "institutional_barriers"
                ]
            },
            "discrimination.employment": {
                "name": "Discriminação no Trabalho", 
                "subcategories": [
                    "hiring_bias",
                    "workplace_harassment",
                    "accommodation_denial",
                    "promotion_barriers"
                ]
            },
            "discrimination.healthcare": {
                "name": "Discriminação na Saúde",
                "subcategories": [
                    "service_denial",
                    "inadequate_care",
                    "communication_barriers",
                    "diagnostic_bias"
                ]
            }
        }
        
    async def initialize(self) -> None:
        """Inicializa modelos de ML."""
        try:
            # Carregar modelos específicos para cada categoria
            logger.info(f"Inicializando {self.name} v{self.version}")
            # Implementação de carregamento de modelos
            self.is_initialized = True
        except Exception as e:
            logger.error(f"Erro na inicialização: {str(e)}")
            raise
    
    async def classify(self, article: Article) -> List[ClassificationResult]:
        """Classifica artigo para discriminação."""
        if not self.is_initialized:
            await self.initialize()
        
        if not await self.validate_input(article):
            return []
        
        results = []
        content_lower = article.content.lower()
        
        # Classificação hierárquica
        for category, config in self.categories.items():
            # Análise de categoria principal
            primary_result = await self._classify_primary_category(
                article, category, config
            )
            
            if primary_result.confidence > 0.3:  # Threshold mínimo
                results.append(primary_result)
                
                # Análise de subcategorias
                subcategory_results = await self._classify_subcategories(
                    article, category, config["subcategories"]
                )
                results.extend(subcategory_results)
        
        return results
    
    async def _classify_primary_category(
        self, 
        article: Article, 
        category: str, 
        config: Dict[str, Any]
    ) -> ClassificationResult:
        """Classifica categoria principal."""
        # Simulação de classificação - em produção usaria ML
        confidence = 0.0
        evidence = []
        
        # Padrões específicos por categoria
        if "educational" in category:
            patterns = [
                "negação de matrícula", "escola recusa", "falta de estrutura",
                "não consegue atender", "sem condições", "inadequado"
            ]
            matches = [p for p in patterns if p in article.content.lower()]
            confidence = min(0.9, len(matches) * 0.3)
            evidence = matches
            
        elif "employment" in category:
            patterns = [
                "demitido por", "não contratado", "discriminação no trabalho",
                "incapaz de trabalhar", "não se adapta"
            ]
            matches = [p for p in patterns if p in article.content.lower()]
            confidence = min(0.9, len(matches) * 0.3)
            evidence = matches
        
        # Determinar severidade
        severity = self._determine_severity(confidence, evidence, article)
        
        return ClassificationResult(
            category=category,
            confidence=confidence,
            level=ClassificationLevel.PRIMARY,
            severity=severity,
            evidence=evidence,
            metadata={
                "classifier": self.name,
                "version": self.version,
                "article_source": article.source
            }
        )
    
    async def _classify_subcategories(
        self, 
        article: Article, 
        parent_category: str,
        subcategories: List[str]
    ) -> List[ClassificationResult]:
        """Classifica subcategorias."""
        results = []
        
        for subcategory in subcategories:
            confidence = await self._analyze_subcategory(article, subcategory)
            
            if confidence > 0.4:  # Threshold para subcategorias
                severity = self._determine_severity(confidence, [], article)
                
                result = ClassificationResult(
                    category=f"{parent_category}.{subcategory}",
                    confidence=confidence,
                    level=ClassificationLevel.SECONDARY,
                    severity=severity,
                    evidence=[],
                    metadata={
                        "parent_category": parent_category,
                        "classifier": self.name
                    }
                )
                results.append(result)
        
        return results
    
    async def _analyze_subcategory(self, article: Article, subcategory: str) -> float:
        """Analisa subcategoria específica."""
        content_lower = article.content.lower()
        
        # Padrões por subcategoria
        patterns_map = {
            "enrollment_denial": ["negação de matrícula", "recusa matrícula", "não aceita"],
            "inadequate_support": ["falta de apoio", "sem suporte", "despreparado"],
            "social_exclusion": ["isolamento", "exclusão", "discriminação social"],
            "hiring_bias": ["não contratou", "rejeitou candidatura", "preconceito na seleção"],
            "service_denial": ["negou atendimento", "recusou serviço", "não atende"]
        }
        
        patterns = patterns_map.get(subcategory, [])
        matches = sum(1 for pattern in patterns if pattern in content_lower)
        
        return min(0.9, matches * 0.4)
    
    def _determine_severity(
        self, 
        confidence: float, 
        evidence: List[str], 
        article: Article
    ) -> Severity:
        """Determina severidade baseada em múltiplos fatores."""
        # Palavras que indicam alta severidade
        high_severity_terms = [
            "violência", "agressão", "expulsão", "demissão", "processo judicial"
        ]
        
        # Palavras que indicam severidade crítica
        critical_terms = [
            "morte", "suicídio", "violência física", "crime", "denúncia formal"
        ]
        
        content_lower = article.content.lower()
        
        if any(term in content_lower for term in critical_terms):
            return Severity.CRITICAL
        elif any(term in content_lower for term in high_severity_terms) or confidence > 0.8:
            return Severity.HIGH
        elif confidence > 0.5:
            return Severity.MEDIUM
        else:
            return Severity.LOW
    
    async def get_supported_categories(self) -> List[str]:
        """Retorna categorias suportadas."""
        categories = list(self.categories.keys())
        
        # Adicionar subcategorias
        for category, config in self.categories.items():
            for subcategory in config["subcategories"]:
                categories.append(f"{category}.{subcategory}")
        
        return categories

class ViolenceClassifier(BaseClassifier):
    """Classificador específico para violência."""
    
    def __init__(self):
        super().__init__("violence_classifier", "1.5")
        
    async def initialize(self) -> None:
        """Inicializa classificador de violência."""
        self.is_initialized = True
        
    async def classify(self, article: Article) -> List[ClassificationResult]:
        """Classifica artigo para violência."""
        # Implementação similar ao DiscriminationClassifier
        # mas focada em padrões de violência
        return []
    
    async def get_supported_categories(self) -> List[str]:
        """Retorna categorias de violência."""
        return ["violence.physical", "violence.psychological", "violence.institutional"]

# Sistema de classificação hierárquica
class HierarchicalClassificationSystem:
    """Sistema principal de classificação hierárquica."""
    
    def __init__(
        self,
        repository: RepositoryProtocol,
        event_publisher: Optional[EventPublisherProtocol] = None
    ):
        self.repository = repository
        self.event_publisher = event_publisher
        self.classifiers: Dict[str, BaseClassifier] = {}
        self.classification_pipeline = []
        
    def register_classifier(self, classifier: BaseClassifier) -> None:
        """Registra um classificador."""
        self.classifiers[classifier.name] = classifier
        logger.info(f"Classificador registrado: {classifier.name}")
    
    def configure_pipeline(self, classifier_names: List[str]) -> None:
        """Configura pipeline de classificação."""
        self.classification_pipeline = [
            self.classifiers[name] for name in classifier_names 
            if name in self.classifiers
        ]
        logger.info(f"Pipeline configurado com {len(self.classification_pipeline)} classificadores")
    
    async def initialize_all(self) -> None:
        """Inicializa todos os classificadores."""
        for classifier in self.classifiers.values():
            if not classifier.is_initialized:
                await classifier.initialize()
    
    async def classify_article(self, article: Article) -> Dict[str, List[ClassificationResult]]:
        """Classifica artigo usando todos os classificadores."""
        if not self.classification_pipeline:
            raise ValueError("Pipeline não configurado")
        
        all_results = {}
        
        for classifier in self.classification_pipeline:
            try:
                results = await classifier.classify(article)
                all_results[classifier.name] = results
                
                # Publicar evento se necessário
                if self.event_publisher and results:
                    await self._publish_classification_event(article, classifier, results)
                    
            except Exception as e:
                logger.error(f"Erro no classificador {classifier.name}: {str(e)}")
                all_results[classifier.name] = []
        
        # Salvar resultados
        await self._save_classification_results(article.id, all_results)
        
        return all_results
    
    async def _publish_classification_event(
        self, 
        article: Article, 
        classifier: BaseClassifier,
        results: List[ClassificationResult]
    ) -> None:
        """Publica evento de classificação."""
        high_severity_results = [
            r for r in results 
            if r.severity in [Severity.HIGH, Severity.CRITICAL]
        ]
        
        if high_severity_results:
            event_data = {
                "article_id": article.id,
                "classifier": classifier.name,
                "high_severity_categories": [r.category for r in high_severity_results],
                "max_confidence": max(r.confidence for r in high_severity_results),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.event_publisher.publish("high_severity_classification", event_data)
    
    async def _save_classification_results(
        self, 
        article_id: str, 
        all_results: Dict[str, List[ClassificationResult]]
    ) -> None:
        """Salva todos os resultados de classificação."""
        for classifier_name, results in all_results.items():
            if results:
                await self.repository.save_classification(article_id, results)
    
    async def get_classification_summary(self, article_id: str) -> Dict[str, Any]:
        """Obtém resumo das classificações de um artigo."""
        history = await self.repository.get_classification_history(article_id)
        
        if not history:
            return {"article_id": article_id, "classifications": []}
        
        # Agrupar por nível e categoria
        summary = {
            "article_id": article_id,
            "classifications": [],
            "highest_severity": Severity.LOW,
            "total_categories": 0,
            "confidence_scores": []
        }
        
        category_groups = {}
        for result in history:
            category = result.category
            if category not in category_groups:
                category_groups[category] = []
            category_groups[category].append(result)
        
        for category, results in category_groups.items():
            # Pegar resultado com maior confiança
            best_result = max(results, key=lambda r: r.confidence)
            
            summary["classifications"].append({
                "category": category,
                "confidence": best_result.confidence,
                "severity": best_result.severity.name,
                "level": best_result.level.value,
                "evidence": best_result.evidence,
                "last_updated": best_result.timestamp.isoformat()
            })
            
            # Atualizar estatísticas
            if best_result.severity.value > summary["highest_severity"].value:
                summary["highest_severity"] = best_result.severity
            
            summary["confidence_scores"].append(best_result.confidence)
        
        summary["total_categories"] = len(category_groups)
        summary["avg_confidence"] = sum(summary["confidence_scores"]) / len(summary["confidence_scores"]) if summary["confidence_scores"] else 0
        summary["highest_severity"] = summary["highest_severity"].name
        
        return summary

# Implementações de infraestrutura
class MongoClassificationRepository(BaseRepository):
    """Repositório MongoDB para classificações."""
    
    def __init__(self, mongodb_manager):
        self.db_manager = mongodb_manager
    
    async def save_classification(self, article_id: str, results: List[ClassificationResult]) -> None:
        """Salva resultados no MongoDB."""
        try:
            async with self.db_manager.get_db() as db:
                documents = []
                for result in results:
                    doc = {
                        "article_id": article_id,
                        "category": result.category,
                        "confidence": result.confidence,
                        "level": result.level.value,
                        "severity": result.severity.value,
                        "evidence": result.evidence,
                        "metadata": result.metadata,
                        "timestamp": result.timestamp,
                        "classifier_version": result.metadata.get("version", "unknown")
                    }
                    documents.append(doc)
                
                if documents:
                    await db.classifications.insert_many(documents)
                    
        except Exception as e:
            logger.error(f"Erro ao salvar classificações: {str(e)}")
            raise
    
    async def get_classification_history(self, article_id: str) -> List[ClassificationResult]:
        """Obtém histórico de classificações."""
        try:
            async with self.db_manager.get_db() as db:
                docs = await db.classifications.find(
                    {"article_id": article_id}
                ).sort("timestamp", -1).to_list(length=None)
                
                results = []
                for doc in docs:
                    result = ClassificationResult(
                        category=doc["category"],
                        confidence=doc["confidence"],
                        level=ClassificationLevel(doc["level"]),
                        severity=Severity(doc["severity"]),
                        evidence=doc.get("evidence", []),
                        metadata=doc.get("metadata", {}),
                        timestamp=doc["timestamp"]
                    )
                    results.append(result)
                
                return results
                
        except Exception as e:
            logger.error(f"Erro ao obter histórico: {str(e)}")
            return []

class EventPublisher:
    """Publicador de eventos para integração."""
    
    def __init__(self):
        self.subscribers: Dict[str, List[callable]] = {}
    
    def subscribe(self, event_type: str, handler: callable) -> None:
        """Inscreve handler para tipo de evento."""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
    
    async def publish(self, event_type: str, data: Dict[str, Any]) -> None:
        """Publica evento."""
        handlers = self.subscribers.get(event_type, [])
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Erro no handler de evento: {str(e)}")

# Factory para configuração
class ClassificationSystemFactory:
    """Factory para criar sistema de classificação."""
    
    @staticmethod
    def create_default_system(mongodb_manager) -> HierarchicalClassificationSystem:
        """Cria sistema padrão."""
        # Repositório
        repository = MongoClassificationRepository(mongodb_manager)
        
        # Event publisher
        event_publisher = EventPublisher()
        
        # Sistema principal
        system = HierarchicalClassificationSystem(repository, event_publisher)
        
        # Registrar classificadores
        discrimination_classifier = DiscriminationClassifier()
        violence_classifier = ViolenceClassifier()
        
        system.register_classifier(discrimination_classifier)
        system.register_classifier(violence_classifier)
        
        # Configurar pipeline
        system.configure_pipeline([
            "discrimination_classifier",
            "violence_classifier"
        ])
        
        return system
    
    @staticmethod
    def create_custom_system(
        classifiers: List[BaseClassifier],
        repository: RepositoryProtocol,
        event_publisher: Optional[EventPublisherProtocol] = None
    ) -> HierarchicalClassificationSystem:
        """Cria sistema customizado."""
        system = HierarchicalClassificationSystem(repository, event_publisher)
        
        for classifier in classifiers:
            system.register_classifier(classifier)
        
        system.configure_pipeline([c.name for c in classifiers])
        
        return system

# Exemplo de uso
async def main():
    """Exemplo de uso do sistema escalável."""
    # Mock do MongoDB manager
    class MockMongoDB:
        async def get_db(self):
            return self
        
        async def insert_many(self, docs):
            print(f"Salvando {len(docs)} classificações")
            return None
        
        async def find(self, query):
            return self
        
        async def sort(self, field, direction):
            return self
        
        async def to_list(self, length):
            return []
    
    mock_db = MockMongoDB()
    
    # Criar sistema
    system = ClassificationSystemFactory.create_default_system(mock_db)
    await system.initialize_all()
    
    # Artigo exemplo
    article = Article(
        id="test_article_1",
        title="Escola nega matrícula para criança autista",
        content="A escola municipal recusou a matrícula alegando falta de estrutura adequada para atender crianças com autismo.",
        source="Jornal Local",
        publish_date=datetime.utcnow(),
        url="https://example.com/noticia"
    )
    
    # Classificar
    results = await system.classify_article(article)
    
    print("Resultados da classificação:")
    for classifier_name, classifications in results.items():
        print(f"\n{classifier_name}:")
        for result in classifications:
            print(f"  - {result.category}: {result.confidence:.2f} ({result.severity.name})")

if __name__ == "__main__":
    asyncio.run(main())